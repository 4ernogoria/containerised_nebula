#!/usr/bin/env bash
#
#-
# Copyright (c) 2013  StorPool.
# All rights reserved.
#

if [ ! -f ca.key ]; then
echo "#generating ca.key"
echo "----------------------------------------------"
openssl genrsa \
			-des3 \
			-out ca.key -passout pass:StorPool \
			4096
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
fi

if [ ! -f ca.crt ]; then
echo "#generating ca.crt"
echo "----------------------------------------------"
sed -i.bak "s/^emailAddress_default.*/emailAddress_default = ca-$$@storpool.local/" openssl.conf
sed -i.bak "s/^commonName_default.*/commonName_default = CA-$$/" openssl.conf
openssl req \
			-config openssl.conf -batch \
			-new -x509 -days 3650 \
			-key ca.key -passin pass:StorPool \
			-out ca.crt -passout pass:StorPool
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
#openssl x509 -noout -text -in ca.crt >ca.crt.txt
#openssl x509 -in ca.crt -noout -subject -nameopt multiline,-lname,-align > ca.crt.txt2
fi

if [ ! -f server.key ]; then
echo "#generating server.key"
echo "----------------------------------------------"
openssl genrsa \
			-des3 \
			-out server.key -passout pass:StorPool \
			1024
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
fi

if [ ! -f server.key.rsa ]; then
echo "# RSA w/o password server.key.rsa"
echo "----------------------------------------------"
openssl rsa \
			-in server.key -passin pass:StorPool \
			-out server.key.rsa
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
fi

if [ ! -f server.csr ]; then
echo "#generating server.csr"
echo "----------------------------------------------"
sed -i.bak "s/^emailAddress_default.*/emailAddress_default = server-$$@storpool.local/" openssl.conf
sed -i.bak "s/^commonName_default.*/commonName_default = storpool.local/" openssl.conf
openssl req \
			-config openssl.conf -batch \
			-new \
			-key server.key -passin pass:StorPool \
			-out server.csr
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
fi

if [ ! -f server.crt ]; then
echo "#sign server.csr to server.crt"
echo "----------------------------------------------"
openssl x509 \
			-req -days 365 \
			-set_serial 01 \
			-CA ca.crt -CAkey ca.key \
			-in server.csr -passin pass:StorPool \
			-out server.crt
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
#openssl x509 -noout -text -in server.crt > server.crt.txt
fi

if [ ! -f client.key ]; then
echo "#generating client.key"
echo "----------------------------------------------"
openssl genrsa \
			-des3 \
			-out client.key -passout pass:StorPool \
			1024
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
fi

if [ ! -f client.csr ];then
echo "#generating client.csr"
echo "----------------------------------------------"
sed -i.bak "s/^emailAddress_default.*/emailAddress_default = client-$$@storpool.local/" openssl.conf
sed -i.bak "s/^commonName_default.*/commonName_default = 'SP client'/" openssl.conf
openssl req \
			-config openssl.conf -batch \
			-new \
			-key client.key -passin pass:StorPool \
			-out client.csr -passout pass:StorPool
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
fi

if [ ! -f client.crt ];then
echo "#sign client.csr to client.crt"
echo "----------------------------------------------"
openssl x509 \
			-req -days 365 \
			-set_serial 02 \
			-CA ca.crt -CAkey ca.key \
			-in client.csr  -passin pass:StorPool \
			-out client.crt
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
#openssl x509 -noout -text -in client.crt > client.crt.txt
fi

if [ ! -f client.p12 ];then
echo "#convert to pkcs#12"
echo "----------------------------------------------"
openssl pkcs12 \
			-export \
			-inkey client.key \
			-certfile ca.crt \
			-name "SP client" \
			-in client.crt -passin pass:StorPool \
			-out client.p12 -passout pass:StorPool
RET=$?
if [ $RET != 0 ]; then
	echo "### Error!"
	exit $RET
fi
#openssl pkcs12 -in client.p12 -passin pass:StorPool > client.p12.txt
fi

rm -f *.bak
