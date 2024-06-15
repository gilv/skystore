#!/bin/bash

docker run -d --env-file=$1 skystore-server

