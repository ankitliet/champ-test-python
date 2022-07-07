#!/bin/bash

set -e

/usr/local/bin/python /usr/src/app/hcmp_orchestrator_processor/processor/service.py startworker -r dev -l debug -q orchestrator-dev --proxy-enabled True
