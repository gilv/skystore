'''
Created on Nov 19, 2023

@author: gilvernik
'''

import os
import datetime
import boto3
from botocore.client import ClientError 

AWS_BACKUP_ZONES = {
    'us-west-1':'us-west-2',
    'us-east-1':'us-east-2',
    'eu-south-1':'eu-south-2',
    }

sky_store_prefix = 'skystore-gvernik'


def modification_date(filename  , nice_print = False):
    t = os.path.getmtime(filename)
    if nice_print:
        return datetime.datetime.fromtimestamp(t)
    return t

def db_replicator(db_file, skystore_prefix, dest_region):
    dst_bucket = f'{skystore_prefix}-{dest_region}'
    s3_client = boto3.client('s3',verify=False,
                          region_name = dest_region)
    
    try:
        s3_client.head_bucket(Bucket=dst_bucket)
        s3_client.upload_file(db_file, dst_bucket, 'skystore.db')
    except ClientError as e:
        response = s3_client.create_bucket(
            Bucket=dst_bucket,
            CreateBucketConfiguration={
                'LocationConstraint': dest_region,
                },
            )
        print(e)

    try:
        s3_client.head_bucket(Bucket=dst_bucket)
        s3_client.upload_file(db_file, dst_bucket, 'skystore.db')
    except ClientError as e:
        print(e)



def run():

    src_region = ""
    config_file = os.path.join(os.path.expanduser('~'), 'skystore-host.config')
    state_file  = os.path.join(os.path.expanduser('~'), 'db_replicator.state')
    db_file = os.path.join(os.path.expanduser('~'), 'skystore', 'store-server', 'skystore.db')

    # get current region
    if os.path.isfile(config_file):
        f = open(config_file, "r")
        data = f.read()
        src_region = data[data.find(':')+1:].strip()
        dst_region = AWS_BACKUP_ZONES.get(str(src_region))

        db_last_update = modification_date(db_file)

        last_timestamp = None
        if os.path.isfile(state_file):
            f = open(state_file, "r")
            last_timestamp = float(f.read())
            f.close()

        if last_timestamp is None or db_last_update > last_timestamp:
            print (f"DB Sync. Last update {db_last_update}, last sync at {last_timestamp}")
            db_replicator(db_file, sky_store_prefix, dst_region)

            f = open(state_file, "w")
            f.write(str(db_last_update))
            f.close()

if __name__ == '__main__':
    run()
