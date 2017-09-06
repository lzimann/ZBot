from twisted.web import server, resource
from twisted.internet import reactor, endpoints
from hashlib import sha1
import hmac
import json

class WebHandler(resource.Resource):
	isLeaf = True
	def __init__(self, irc_clients, config):
		self.clients = irc_clients
		self.config = config #stores the webhook config
		self.port = self.config.get('port')
		self.secret = self.config['github'].get('secret')
		print("Now listening POST requests on port:", self.port)
	def _compare_secret(self, secret_to_compare, payload):
		if secret_to_compare == None:
			return False
		this_secret = hmac.new(self.secret.encode('utf-8'), payload, sha1)
		secret_to_compare = secret_to_compare.replace('sha1=', '')
		return hmac.compare_digest(secret_to_compare, this_secret.hexdigest())
	def render_POST(self, request):
		event_type = request.getHeader("X-GitHub-Event")
		payload = request.content.getvalue()
		if not self._compare_secret(request.getHeader("X-Hub-Signature"), payload):
			request.setResponseCode(500)
			return b"Secret did NOT match"
		json_payload = "".join(map(chr, payload))
		for client in self.clients:
			client.receive_event(event_type, json_payload)
		return b"POST sucessfully received."
	
	def render_GET(self, request):
		return b"GET events not supported"

if __name__ == '__main__':
	endpoints.serverFromString(reactor, "tcp:25568").listen(server.Site(Handler()))
	try:
		print("Server running.")
		reactor.run()
	except KeyboardInterrupt:
		pass