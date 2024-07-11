#!/bin/bash

if ! [ -f "$1" ]; then
  echo "Invalid env file"
fi


kubectl create configmap conf-skystore-server --from-env-file=$1
