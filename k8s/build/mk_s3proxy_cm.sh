#!/bin/bash

if ! [ -f "$1" ]; then
  echo "Invalid env file"
fi


kubectl create configmap conf-skystore-s3proxy --from-env-file=$1
