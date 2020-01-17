#
#-
# Copyright (c) 2015  StorPool.
# All rights reserved.
#
from config import *
from proxy import Proxy

proxy = Proxy(TARGET_HOST, CINDER_PORT_REAL)
proxy.run(BIND_HOST, CINDER_PORT_PROXY)
