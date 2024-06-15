#!/bin/bash

cp $1 $1.withpubkey
echo "SKYSTORE_PUB_KEY="$(./encode.sh keys/skystore.pub) >> $1.withpubkey
 
