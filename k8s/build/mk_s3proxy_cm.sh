#!/bin/bash

if ! [ -f "$1" ]; then
  echo "Invalid env file"
fi

suffix="$2"

# Prepend dash if suffix is non-empty and does not start with dash
[[ -n "$suffix" ]] && ! [[ "$suffix" == -* ]] && suffix="-$suffix"


kubectl create configmap conf-skystore-s3proxy"$suffix" --from-env-file=$1
