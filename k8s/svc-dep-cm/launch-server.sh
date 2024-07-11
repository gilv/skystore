#!/bin/bash

SERVER_YAML=$1

: ${SERVER_YAML:="server.yaml"}

kubectl apply -f $SERVER_YAML


