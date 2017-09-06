from twisted.internet import reactor, endpoints
import twisted.web.server as twisted_server
from zbot.bot import ZBotFactory
from zbot.config import Config
from zbot.webhandler import handler
from zbot.requests import APIRequests

def main():
	config = Config() # Initializes the configuration
	connections = config.get('connections') #Gets all connections
	clients = [] # List of clients
	webhook_config = config.get('webhook')
	webrequests_config = config.get('webrequests')
	requests_api = APIRequests(webrequests_config)
	for server in connections:
		server_array = server.get('server')
		address = server_array.get('address')
		port = server_array.get('port')
		server['webhook'] = webhook_config #appends the webhook config to the bot, temporary until a better solution of properly sending the entire config obj appears
		irc_factory = ZBotFactory(server, requests_api)
		reactor.connectTCP(address, port, irc_factory)
		clients.append(irc_factory)
	if webhook_config.get('enabled'):
		webhook_port = webhook_config.get('port', 8080)	
		endpoints.serverFromString(reactor, "tcp:" + webhook_port).listen(twisted_server.Site(handler.WebHandler(clients, config.get('webhook'))))
	try:
		reactor.run()
	except KeyboardInterrupt:
		reactor.stop()
		pass

main()