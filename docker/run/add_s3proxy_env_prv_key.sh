#!/bin/bash

cp $1 $1.withprvkey
echo "SKYSTORE_PRV_KEY="$(./encode.sh keys/skystore) >> $1.withprvkey
 
