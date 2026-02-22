#!/bin/bash

if ! [ -f "$1" ]; then
  echo "Invalid env file";
  exit 1;
fi


kubectl create configmap conf-skystore-server --from-env-file=$1
