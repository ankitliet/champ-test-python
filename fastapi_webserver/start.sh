#!/bin/bash

set -e

python /usr/src/app/webserver/fastapi_webserver/service.py startworker -r dev -t true
