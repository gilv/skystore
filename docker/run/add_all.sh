#!/bin/bash

../add_s3proxy_env_prv_key.sh env.base
../add_s3proxy_env_s3_cfg.sh env.base.withprvkey aws.config
../add_s3proxy_env_s3pjson_cfg.sh env.base.withprvkey.withs3cfg s3proxy.json
mv env.base.withprvkey.withs3cfg.withs3pjsoncfg env.final
rm -f *with*

