#
#-
# Copyright (c) 2015  StorPool.
# All rights reserved.
#
import httplib as http
import json as js
import re as re
import sys as sys
import BaseHTTPServer as HTTP
from collections import defaultdict
from urlparse import urlparse


class Logger(object):
	def log(self, outp, fmt, **kwargs):
		print >> outp, fmt.format(**kwargs)
		outp.flush()
	
	debug = lambda self, fmt, **kwargs: self.log(sys.stdout, fmt, **kwargs)
	info  = lambda self, fmt, **kwargs: self.log(sys.stdout, fmt, **kwargs)
	warn  = lambda self, fmt, **kwargs: self.log(sys.stderr, fmt, **kwargs)
	error = lambda self, fmt, **kwargs: self.log(sys.stderr, fmt, **kwargs)

log = Logger()


class RequestException(Exception):
	def __init__(self, req):
		super(RequestException, self).__init__()
		self.req = req

class Request(object):
	def __init__(self, method, host, port, query, headers={}, data=None):
		try:
			log.info("""SENDING REQUEST:
REQUEST: {method} {host}:{port}{query}
HEADERS: {headers}
DATA:    {data}
""", method=method, host=host, port=port, query=query, headers=headers, data=data)
			
			conn = http.HTTPConnection(host, port)
			conn.request(method, query, data, headers)
			resp = conn.getresponse()
			
			self.status = resp.status
			self.headers = dict(resp.getheaders())
			self.data = resp.read()
			
			log.info("""RECEIVED RESPONSE:
STATUS:  {r.status} {r.reason}
HEADERS: {s.headers}
DATA:    {s.data}
""", s=self, r=resp)
			
			if self.status < 200 or self.status >= 300:
				raise RequestException(self)
		finally:
			conn.close()
	
	@property
	def ok(self):
		return self.status == http.OK
	
	@property
	def json(self):
		return js.loads(self.data)


class ProxyHandler(HTTP.BaseHTTPRequestHandler):
	wbufsize = 4096
	proxyHost = None
	proxyPort = None
	proxyQueryDefs = defaultdict(list)
	
	def getPath(self):
		return urlparse(self.path).path
	
	def getHeaders(self):
		return dict((name, self.headers.getheader(name)) for name in self.headers)
	
	def getContent(self):
		length = self.headers.getheader('content-length')
		if length is not None:
			try:
				length = int(length)
				err = length < 0
			except:
				err = True
			
			if err:
				raise Exception("Invalid Length: {length}".format(length=length))
		
		return self.rfile.read(length) if length else None
	
	def sendRequest(self, method, host, port, query, headers={}, data=None, json=None):
		if json is not None:
			assert data is None
			data = js.dumps(json)
		
		if 'content-length' in headers:
			del headers['content-length']
		
		return Request(method, host, port, query, headers, data)
	
	def proxyRequest(self):
		return self.sendRequest(self._method, self.proxyHost, self.proxyPort, self.path, self._headers, self._data)
	
	def sendResponse(self, status, headers={}, data=None, json=None):
		assert not (data is not None and json is not None)
		
		log.info("""SENDING RESPONSE:
STATUS:  {status}
HEADERS: {headers}
DATA:    {data}
JSON:    {json}
""", status=status, headers=headers, data=data, json=js.dumps(json, indent=4))
		
		self.send_response(status)
		for hname, hval in headers.iteritems():
			if hname != 'content-length':
				self.send_header(hname, hval)
		self.end_headers()
		
		if json is not None:
			js.dump(json, self.wfile)
		elif data is not None:
			self.wfile.write(data)
	
	def sendError(self, code, msg):
		log.error("ERROR: {code} {msg}", code=code, msg=msg)
		self.sendResponse(code, json={ 'error': { 'error': str(msg) } })
	
	@property
	def json(self):
		return js.loads(self._data)
	
	def handleRequest(self, method):
		try:
			self._method, self._headers, self._data = method, self.getHeaders(), self.getContent()
			log.info("""HANDLE REQUEST:
METHOD:  {s._method}
PATH:    {s.path}
HEADERS: {s._headers}
DATA:    {s._data}
""", s=self)
			
			path = self.getPath()
			for regex, handler in self.proxyQueryDefs[method]:
				m = regex.match(path)
				if m is not None:
					handler(self, m)
					break
			else:
				self.default()
		except KeyboardInterrupt:
			raise
		except RequestException as re:
			self.sendResponse(re.req.status, re.req.headers, re.req.data)
		except Exception as e:
			self.sendError(http.INTERNAL_SERVER_ERROR, e)
	
	def default(self):
		req = self.proxyRequest()
		self.sendResponse(req.status, req.headers, data=req.data)
	
	def unimplemented(self, _):
		self.sendError(http.NOT_IMPLEMENTED, "Request not implemented. Please contact Storpool support")
	
	do_GET    = lambda self: self.handleRequest('GET')
	do_POST   = lambda self: self.handleRequest('POST')
	do_PUT    = lambda self: self.handleRequest('PUT')
	do_DELETE = lambda self: self.handleRequest('DELETE')


class Proxy(object):
	def __init__(self, proxyHost, proxyPort):
		self.vars = {}
		ProxyHandler.proxyHost = proxyHost
		ProxyHandler.proxyPort = proxyPort
	
	def doBind(self, method, query, handler):
		regex = re.compile("^{q}$".format(q=query.format(**self.vars)))
		ProxyHandler.proxyQueryDefs[method].append((regex, handler))
	
	def bind(self, method, path):
		return lambda handler: self.doBind(method, path, handler)
	
	def unimplemented(self, method, query):
		self.bind(method, query)(ProxyHandler.unimplemented)
	
	def run(self, host, port):
		httpd = HTTP.HTTPServer((host, port), ProxyHandler)
		try:
			httpd.serve_forever()
		except:
			httpd.server_close()


