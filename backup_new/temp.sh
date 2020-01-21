#!/bin/bash
su - oneadmin -c "touch /backup/file-$(date '+%H%M')"
