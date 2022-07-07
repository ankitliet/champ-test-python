#!/bin/bash

set -e


cp -r /root/.ansible/collections/ /usr/share/ansible/collections/
/usr/local/bin/python /usr/src/app/hcmp_orchestrator_processor/processor/service.py startworker -r dev -l debug -q orchestrator-dev --proxy-enabled True
