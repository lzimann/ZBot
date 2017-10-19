import re
import requests
from twisted.words.protocols import irc
from twisted.internet import protocol
from zbot.github_events import EventHandler
from zbot.github_events import EventHandlerFactory

class ZBot(irc.IRCClient):
	#Dict of command -> function to call, ugly but effective, I guess
	commands = {
		'commit'      : '_search_for_commit',
		'kek'	      : '_kek',
		'pr' 	      : '_get_pr_info',
		'sdef'	      : '_get_proc',
		'sfile'	      : '_search_for_file',
		'shatree'     : '_sha_tree',
		'shelp'	      : '_help',
		'update_tree' : '_update_sha_tree'
	}
	#Regex to search the string for #numbers or [numbers]. At least 5 digits are necessary for # and at least 4 are necessary for []
	pr_regex = re.compile('#(\d{5,})|\[(\d{4,})\]')
	#Regex to search for a file between []
	file_regex = re.compile('\[(.*\.[^#\s]*)#?(\d+)?\]')
	#Regex to search for a commit prefixed with ^
	commit_regex = re.compile('\^([0-9a-fA-F~]{5,40})')
	def __init__(self, config, requests):
		self.config = config
		self.event_handler = EventHandlerFactory(config.get('webhook'))
		self.requests = requests
		self._setup()
		self.server_name = self.config.get('server').get('name').capitalize()
		self.connected_channels = []
		super(ZBot, self).__init__()
	
	def _setup(self):
		info = self.config.get('info')
		self.nickname = info.get('nickname', 'ZBot')
		self.alt_nickname = info.get('alt_nickname', 'ZBot_')
		self.realname = info.get('realname', 'ZBot')
		self.username = info.get('username', 'ZBot')
		self.channels = self.config.get('channels')
	
	def signedOn(self):
		print("Sucessfully connected to", self.server_name)
		nickserv = self.config.get('nickserv')
		if nickserv.get('enabled'):
			self.msg("NickServ", "IDENTIFY {}".format(nickserv.get('password')))
		print("Attempting to join channels: ")
		for channel in self.channels:
			self.join(channel)
	
	def alterCollidedNick(self, nickname):
		print("{}: {} is already in use. Changing to {}".format(self.server_name, self.nickname, self.alt_nickname))
		return self.alt_nickname
	
	def joined(self, channel):
		print("Sucessfully joined", channel)
		self.connected_channels += channel
	
	def privmsg(self, user, channel, message):
		print("{}: {}: {}".format(channel, user, message))
		if(message.startswith("!")):
			msg_split = message[1:].split()
			try:
				if msg_split[0] in self.commands:
					getattr(self, self.commands[msg_split[0]])(channel, user, msg_split)
			except IndexError:
				pass
		else:
			pr_match = re.search(self.pr_regex, message)
			if pr_match:
				group = pr_match.group(1) or pr_match.group(2)
				self._get_pr_info(channel, user, group, True)
			else:
				file_match = re.search(self.file_regex, message)
				if file_match:
					self._search_for_file(channel, user, file_match, True)
				else:
					commit_match = re.search(self.commit_regex, message)
					if commit_match:
						self._search_for_commit(channel, user, commit_match.group(1))
	def ctcpQuery(self, user, channel, messages):
		super(ZBot, self).ctcpQuery(user, channel, messages)
		print("CTCP: {}: {}: {}".format(channel, user, messages))
	
	def receive_event(self, event_type, json_payload):
		event_dict = self.event_handler.new_event(event_type, json_payload)
		msg = event_dict.get('message')
		if msg is not None:
			self.send_to_channels(event_dict.get('channels'), msg)
	
	#Send to a single channel
	def send_to_channel(self, channel, message):
		print("{s} - {c}: {m}".format(s = self.server_name, c = channel, m = message))
		self.msg(channel, message)
	
	#Sends to a list of channels
	def send_to_channels(self, channels, message):
		for channel in channels:
			self.send_to_channel(channel, message)

	#Sends to all connected channels.
	def send_to_all_channels(self, message):
		for channel in self.channels:
			self.send_to_channel(channel, message)
			
	## Bot commands

	#Searches the configured repo for a commit and sends the github link to it if it exists.
	def _search_for_commit(self, channel, user, commit_sha):
		"""Usage: !commit <commit hash>"""
		path = self.requests.get_commit_url(commit_sha)
		if path:
			self.send_to_channel(channel, path)
	
	#Searches the configured repo's tree for a file match, and sends the closest match.
	def _search_for_file(self, channel, user, msg_split, regex_used = False):
		"""Usage: !sfile <file name> <#L + line number(if any)>"""
		line = None
		if regex_used:
			file_string = msg_split.group(1)
			if msg_split.group(2):
				line = "#L" + msg_split.group(2)
		elif len(msg_split) >= 3 and msg_split[2].startswith('#L'):
			file_string = msg_split[1]
			line = msg_split[2]
		path = self.requests.get_file_url(file_string, line)
		if path:
			self.send_to_channel(channel, path)
	
	def _sha_tree(self, channel, user, msg_split):
		"""Returns the current tree's SHA."""
		self.send_to_channel(channel, "SHA: {}".format(self.requests.get_tree_sha()))
	
	def _update_sha_tree(self, channel, user, msg_split):
		"""Updates the current tree with configured repo's latest."""
		force = False
		if len(msg_split) >= 2 and msg_split[1] == 'force': #Forces the tree to reload regardless if it's the same sha
			force = True
		old = self.requests.get_tree_sha()
		self.requests.update_tree(force)
		self.send_to_channel(channel, "Tree updated.")
		self.send_to_channel(channel, "Old: {} New: {}".format(old, self.requests.get_tree_sha()))
	
	#Gets the info of a certain pull request/issue by the number from the configured repository
	def _get_pr_info(self, channel, user, msg_split, regex_used = False):
		"""Usage: !pr <number>"""
		if regex_used:
			number = msg_split
		else:
			number = msg_split[1]
		pr_info = self.requests.get_pr_info(number)
		if(pr_info):
			msg = "\"{t}\" (#{n}) by {u} - {l}".format(t = pr_info.get('title'), n = pr_info.get('number'), u = pr_info.get('user').get('login'), l = pr_info.get('html_url'))
			self.send_to_channel(channel, msg)
	
	def _get_proc(self, channel, user, msg_split):
		"""Usage: !sdef <proc/var> <name> <parent type(if any)>"""
		# If it is a var or proc
		search_type = msg_split[1]
		# What is the proc/var you are trying to find
		thing_to_search = msg_split[2]
		
		# If the proc/var has a parent type
		parent_type = None
		if len(msg_split) > 3:
			parent_type = msg_split[3]
		
		param = {
		"searchtype" : search_type,
		"q" : thing_to_search,
		"json" : "1",
		"search" : "go"
		}
		if parent_type:
			param["type"] = parent_type
			
		payload = requests.get("https://tgstation13.org/findshit.php", params = param).json()
		
		#Grab the first result
		try:
			info_found = payload[0]
			file = info_found.get('F')
			file_path = file[0]
			line = file[1]
			msg = "https://github.com/tgstation/tgstation/blob/master/{FILE}#L{LINE}".format(FILE = file_path, LINE = line)
			self.send_to_channel(channel, msg)
		except KeyError:
			pass
		
	def _kek(self, channel, user, msg_split):
		"""kek"""
		self.send_to_channel(channel, "kek")
	
	def _help(self, channel, user, msg_split):
		"""Usage: !help <command(or blank to display all available commands)>"""
		if len(msg_split) == 1:
			final_msg = "Available commands: "
			len_c = len(self.commands)
			count = 0
			for command in self.commands:
				if count == len_c - 1:
					final_msg += command
				else:
					final_msg += command + ", "
				count += 1
		else:
			final_msg = getattr(self, self.commands[msg_split[1]]).__doc__
		self.send_to_channel(channel, final_msg)
		
	
class ZBotFactory(protocol.ClientFactory):
	def __init__(self, config, requests):
		super(ZBotFactory, self).__init__()
		self.requests = requests
		self.config = config #Config containing this connection's info + webhook
		server_info = self.config.get('server')
		self.name = server_info.get('name').capitalize()#Server name
		
	def buildProtocol(self, addr):
		self.client = ZBot(self.config, self.requests)
		self.client.factory = self
		return self.client
	
	def startedConnecting(self, connector):
		print("Attempting to connect on", self.name)
	
	def clientConnectionLost(self, connector, reason):
		connector.connect()
	
	def clientConnectionFailed(self, connector, reason):
		print("Connection has failed:", reason)
	
	def receive_event(self, event_type, json_payload):
		self.client.receive_event(event_type, json_payload)
	
