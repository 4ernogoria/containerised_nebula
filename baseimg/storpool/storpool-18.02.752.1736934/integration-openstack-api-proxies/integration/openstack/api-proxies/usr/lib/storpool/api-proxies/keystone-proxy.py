#
#-
# Copyright (c) 2015  StorPool.
# All rights reserved.
#
from urlparse import urlparse, urlunparse
from config import *
from proxy import Proxy, log


proxy = Proxy(TARGET_HOST, KEYSTONE_PORT_REAL)

@proxy.bind('POST', "/v2.0/tokens")
def listTokens(handler, _, pmap = KEYSTONE_REMAP):
	req = handler.proxyRequest()
	json = req.json
	
	for e in json['access']['serviceCatalog']:
		if e['name'] in pmap:
			portMappings = pmap[e['name']]
			
			for endpoint in e['endpoints']:
				for urlName in ['internalURL', 'adminURL', 'publicURL']:
					parsed = urlparse(endpoint[urlName])
					if parsed.port in portMappings:
						new = parsed._replace(netloc="{0}:{1}".format(parsed.hostname, portMappings[parsed.port]))
						endpoint[urlName] = urlunparse(new)
	
	handler.sendResponse(req.status, req.headers, json=json)

proxy.run(BIND_HOST, KEYSTONE_PORT_PROXY)

