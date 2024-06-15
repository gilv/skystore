#!/bin/bash

# First arg is env file, second arg is S3 Proxy JSON config file
cp $1 $1.withs3pjsoncfg
echo "SKYSTORE_S3P_CFG="$(./encode.sh $2) >> $1.withs3pjsoncfg

