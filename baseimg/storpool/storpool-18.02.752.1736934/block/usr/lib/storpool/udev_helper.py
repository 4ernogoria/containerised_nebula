#!/usr/bin/python
#
#-
# Copyright (c) 2013  StorPool.
# All rights reserved.
#
import os
import sys
import re

#log = open("/tmp/log", "a+")
#log.write( str(os.environ) + "\n" )

devPath = os.environ.get('DEVPATH')

if not devPath:
	sys.exit(1)

m = re.match('\/devices/virtual/block\/sp-(\d+)(?:\/sp-\d+p(.*))?$', devPath)

if m:
	devId = m.groups()[0]
	part = m.groups()[1]
	
	nameFile = open("/sys/devices/virtual/storpool_bd/storpool_bd/info/" + devId + "/name" )
	name = nameFile.read()
	
	res = "storpool/" + name
	if part:
		res += "-part" + part
	
#	log.write( "res:" + res + "\n" )
	print res
	sys.exit(0)

#log.write("no match!\n")
sys.exit(1)
