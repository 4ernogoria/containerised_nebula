#
#-
# Copyright (c) 2015  StorPool.
# All rights reserved.
#
import re
from config import *
from proxy import Proxy

def isStorpoolImage(snap):
	return snap.get('metadata', {}).get('storpool.image', None) == STORPOOL_IMAGE_TRUE

def imageFromSnapshot(tenantId, snapshot):
	
	url = "http://{HOST}:{PORT}/v2/{tenantId}/images/{id}".format(HOST=BIND_HOST, PORT=NOVA_PORT_PROXY, tenantId=tenantId, id=snapshot['id'])
	
	return {
		"id": snapshot['id'],
		"name": snapshot['display_name'],
		
		"status": "ACTIVE", # XXX "ACTIVE" if snapshot['status'] == "available" else ???
		"OS-EXT-IMG-SIZE:size": snapshot['size'] * 1024 ** 3,
		
		"created": snapshot['created_at'],
		"updated": snapshot['created_at'],
		
		"minDisk": 0,
		"minRam": 0,
		"progress": snapshot['os-extended-snapshot-attributes:progress'],
		"metadata": {},
		"links": [
			{"href": url, "rel": "self"},
			{"href": url, "rel": "bookmark"},
			{"href": url, "type": "application/vnd.openstack.image", "rel": "alternate"}
		
		],
	}


proxy = Proxy(TARGET_HOST, NOVA_PORT_REAL)
proxy.vars['tenant_id'] = r"([0-9a-f]+)"
proxy.vars['image_id'] = r"([0-9a-f\-]+)"
proxy.vars['key'] = r".+"

# Images
@proxy.bind('GET', "/v2/{tenant_id}/images")
def images(handler, m):
	query = "/v1/{tenant_id}/snapshots/detail".format(tenant_id=m.groups()[0])
	req = handler.sendRequest('GET', TARGET_HOST, CINDER_PORT_REAL, query, handler._headers, handler._data)
	json = { 'images': [{ 'id': snap['id'], 'name': snap['display_name'], 'links': [] } for snap in req.json['snapshots'] if isStorpoolImage(snap)] }
	handler.sendResponse(req.status, req.headers, json=json)

@proxy.bind('GET', "/v2/{tenant_id}/images/detail")
def imagesDetails(handler, m):
	tenantId = m.groups()[0]
	
	query = "/v1/{tenant_id}/snapshots/detail".format(tenant_id=tenantId)
	req = handler.sendRequest('GET', TARGET_HOST, CINDER_PORT_REAL, query, handler._headers, handler._data)
	json = { 'images': [imageFromSnapshot(tenantId, snap) for snap in req.json['snapshots'] if isStorpoolImage(snap)] }
	handler.sendResponse(req.status, req.headers, json=json)

@proxy.bind('GET', "/v2/{tenant_id}/images/{image_id}")
def imageDetails(handler, m):
	tenantId = m.groups()[0]
	
	query = "/v1/{tenant_id}/snapshots/{image_id}".format(tenant_id=tenantId, image_id=m.groups()[1])
	req = handler.sendRequest('GET', TARGET_HOST, CINDER_PORT_REAL, query, handler._headers, handler._data)
	json = { 'image' : imageFromSnapshot(tenantId, req.json['snapshot']) }
	handler.sendResponse(req.status, req.headers, json=json)

proxy.unimplemented('DELETE', "/v2/{tenant_id}/images/{image_id}")

# Image metadata
proxy.unimplemented('GET',    "/v2/{tenant_id}/images/{image_id}/metadata")
proxy.unimplemented('PUT',    "/v2/{tenant_id}/images/{image_id}/metadata")
proxy.unimplemented('POST',   "/v2/{tenant_id}/images/{image_id}/metadata")
proxy.unimplemented('GET',    "/v2/{tenant_id}/images/{image_id}/metadata/{key}")
proxy.unimplemented('PUT',    "/v2/{tenant_id}/images/{image_id}/metadata/{key}")
proxy.unimplemented('DELETE', "/v2/{tenant_id}/images/{image_id}/metadata/{key}")

# create VM
@proxy.bind('POST', "/v2/{tenant_id}/servers")
def createVM(handler, m, imgLinkRegex=re.compile("https?:.*/images/(.+)")):
	json = handler.json
	
	imgref = json['server']['imageRef']
	imgmatch = imgLinkRegex.match(imgref)
	if imgmatch is not None:
		imgref = imgmatch.groups()[0]
	
	json['server']['block_device_mapping_v2'] = [{
			'uuid': imgref,
			'boot_index': 0,
			'source_type': "snapshot",
			'destination_type': "volume",
			'delete_on_termination': False,
		}]
	json['server']['imageRef'] = ""
	
#	query = "/v2/{tenant_id}/os-volumes_boot".format(tenant_id=m.groups()[0])
	query = "/v2/{tenant_id}/servers".format(tenant_id=m.groups()[0])
	req = handler.sendRequest('POST', handler.proxyHost, handler.proxyPort, query, 	handler._headers, json=json)
	handler.sendResponse(req.status, req.headers, req.data)

proxy.run(BIND_HOST, NOVA_PORT_PROXY)

