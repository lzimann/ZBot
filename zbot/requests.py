import requests
import json
import os
import re
from threading import Timer
from fuzzywuzzy import process, fuzz
"""
    This will make requests using the GitHub api.
"""

#How many seconds between requesting info on the same PR
PR_TIMING = 60.0

class APIRequests:
    github_api_url = 'https://api.github.com/repos'
    github_frontend_url = 'https://github.com'
    file_pattern = re.compile('.*\/(.*)')
    #Recent pull requests
    recent_prs = {}
    def __init__(self, config):
        self.config = config
        self.repo = self.config.get('name')
        self.owner = self.config.get('owner')
        self.master_tree_url = '{gau}/{o}/{r}/git/trees/master'.format(gau = self.github_api_url, o = self.owner, r = self.repo)
        self.update_tree()
    """
        Updates the current tree, used as a hook for the bot
    """
    def update_tree(self, force = False):
        self.current_tree = self.get_repo_tree()
        self.current_paths = []
        for file in self.current_tree.get('tree'):
            if file.get('type') == 'blob':
                self.current_paths.append(file['path'])

    """
        Returns a URL to a commit if it exists
    """
    def get_commit_url(self, sha):
        api_url = '{gau}/{o}/{r}/commits/{commit}'.format(gau = self.github_api_url, o = self.owner, r = self.repo, commit = sha)
        r = requests.get(api_url)
        if r.status_code == 200:	#will 404 if it doesn't exist
            frontend_url = '{feu}/{o}/{r}/commit/{commit}'.format(feu = self.github_frontend_url, o = self.owner, r = self.repo, commit = sha)
            return frontend_url

    """
        Returns a json tree of the default repo
    """
    def get_repo_tree(self, force = False):
        path = os.path.abspath('repository_tree.json')
        tree = {}
        try:
            f = open(path, "r+")
            tree = json.load(f)
        except:
            f = open(path, "w+")
        if tree.get('sha') != requests.get(self.master_tree_url).json().get('sha') or force:
            f.seek(0)
            f.truncate()
            tree = requests.get(self.master_tree_url, params = {'recursive' : '1'}).json()
            json.dump(tree, f)
        f.close()
        return tree

    """
        Returns the current tree SHA
    """
    def get_tree_sha(self):
        return self.current_tree.get('sha')

    """
        Searches the tree for a given path
    """
    def get_file_url(self, file_string, line):
        matching_paths = []
        file_to_search = file_string
        user_match = self.file_pattern.search(file_string)
        exact_match = None
        if user_match:
            file_to_search = user_match.group(1)
        for path in self.current_paths:
            current_path = path
            if current_path == file_string:
                print(current_path)
                exact_match = current_path
            path_match = self.file_pattern.search(path)
            if path_match:
                current_path = path_match.group(1)
            if fuzz.token_sort_ratio(file_to_search, current_path) >= 75:
                matching_paths.append(path)
        if exact_match is not None:
            result = [exact_match]
        else:
            result = process.extractOne(file_string, matching_paths, scorer = fuzz.token_set_ratio)
        if result:
            return "https://github.com/{own}/{repo}/blob/master/{p}{l}".format(own = self.owner, repo = self.repo, p = result[0], l = line if line else '')
        return None

    def get_pr_info(self, pr_number, channel):
        try:
            if pr_number in self.recent_prs[channel]:
                return None
        except KeyError:
            self.recent_prs[channel] = []
        req = requests.get("{g}/{o}/{r}/issues/{n}".format(g = self.github_api_url, o = self.owner, r = self.repo, n = pr_number))
        if req.status_code == 200:
            self.recent_prs[channel].append(pr_number)
            Timer(PR_TIMING, lambda n: self.recent_prs[channel].remove(n), [pr_number]).start()
            return req.json()
        return None