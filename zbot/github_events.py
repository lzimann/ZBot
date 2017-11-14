import json

#bold = ""
class EventHandler:
    events_dict = {
        'pull_request' : '_pull_request_event',
        'push' : '_push_event',
        'issues' : '_issue_event'
    }
    def __init__(self, event_type, payload, event_dict):
        self.event_type = event_type
        self.payload = json.loads(payload)
        self.this_event_dict = event_dict
        self.event_msg = self._check_event()

    def get_message(self):
        return self.event_msg

    def _get_repo_name(self):
        return "6[{repo_name}] ".format(repo_name = self.payload.get('repository').get('name'))

    #Returns the action color for issues/prs.
    def _get_action_color(self, action, merging = False):
        if action == 'opened' or action == 'reopened':
            return '3' #Green
        elif action == 'closed':
            if merging:
                return '6' #Purple
            else:
                return '4' #Red

    def _check_event(self):
        try:
            if self.event_type not in self.events_dict:
                print("Error: {} is not a valid event".format(self.event_type))
                raise KeyError
            event = self.events_dict[self.event_type]
            message = None
            event_msg = getattr(self, event)()
            if event_msg:
                message = self._get_repo_name() + event_msg
            return {'channels' : self.this_event_dict.get('channels'), 'message' : message}
        except KeyError:
            print("Invalid or not supported hook event:", self.event_type)
            return {'message' : None}

    def _pull_request_event(self):
        pr_action = self.payload.get('action')
        if pr_action not in self.this_event_dict.get('actions'):
            return None
        pr_obj = self.payload.get('pull_request')
        merging = pr_obj.get('merged')
        pr_action_color = self._get_action_color(pr_action, merging)
        if pr_action == 'closed' and merging:
            pr_action = 'merged'
        pr_title = pr_obj.get('title')
        pr_number = pr_obj.get('number')
        pr_author = pr_obj.get('user').get('login')
        if pr_author == self.payload.get('sender').get('login'):
            pr_author = ""
        else:
            pr_author = " by {}".format(pr_author)

        to_branch = pr_obj.get('base').get('ref')
        from_branch = pr_obj.get('head').get('ref')

        #the message itself
        msg = "Pull Request "
        msg += "{action_color}{action} ".format(action_color = pr_action_color, action = pr_action)
        msg += "by {}: ".format(self.payload.get('sender').get('login'))
        msg += "{title} (#{number}){author} ".format(title = pr_title, number = pr_number, author = pr_author)
        msg += "({}...{}) ".format(to_branch, from_branch)
        msg += pr_obj.get('html_url')
        return msg

    def _push_event(self):
        sender = self.payload.get('sender').get('login')
        branch = self.payload.get('ref').replace('refs/heads/', '')
        
        diff = self.payload.get('compare')
        size = len(self.payload.get('commits'))

        if self.payload.get('deleted'):
            return "{} 4deleted {}.".format(sender, branch)
        elif self.payload.get('created'):
            return "{} 3created {}. {}".format(sender, branch, diff)
        if self.this_event_dict.get('ignore_non_master_pushes') and branch != 'master':
            return None
        if not size:
            return None

        #the message
        msg = "Push: "
        msg += "{} 6{}pushed {} commit{} ".format(sender, '4force-' if self.payload.get('forced') else '', size, '' if size == 1 else 's')
        msg += "to {}. ".format(branch)
        msg += diff
        return msg

    def _issue_event(self):
        issue_action = self.payload.get('action')
        if issue_action not in self.this_event_dict.get('actions'):
            return None
        issue_obj = self.payload.get('issue')
        issue_action_color = self._get_action_color(issue_action)
        issue_title = issue_obj.get('title')
        issue_number = issue_obj.get('number')

        #the message itself
        msg = "Issue "
        msg += "{action_color}{action} ".format(action_color = issue_action_color, action = issue_action)
        msg += "by {}: ".format(self.payload.get('sender').get('login'))
        msg += "{title} (#{number}). ".format(title = issue_title, number = issue_number)
        msg += issue_obj.get('html_url')
        return msg

class EventHandlerFactory:
    def __init__(self, config):
        self.events_dict = config.get('github').get('events')

    def new_event(self, event_type, payload):
        if event_type not in self.events_dict:
            return {'message' : None}
        return EventHandler(event_type, payload, self.events_dict[event_type]).get_message()
