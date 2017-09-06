import os
import json

class Config(dict):
	def __init__(self, *args, **kwargs):
		self.filename = "config.json"
		self.path = os.path.abspath(self.filename)
		self.populate_config()
		super(Config, self).__init__(*args, **kwargs)
		
	def populate_config(self):
		if not os.path.exists(self.path):
			print("No config file found!")
			sys.exit(666)
		
		with open(self.path) as f:
			self.update(json.load(f))
		f.close()