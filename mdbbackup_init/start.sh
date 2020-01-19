#!/bin/bash
mdbusr=Sonic2005
podman build --build-arg dbpass="$mdbusr" -t mdback .
