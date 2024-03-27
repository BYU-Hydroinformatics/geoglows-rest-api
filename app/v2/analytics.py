import json
import logging
import os
import time

import boto3

LOG_GROUP_NAME = os.getenv('AWS_LOG_GROUP_NAME')
LOG_STREAM_NAME = os.getenv('AWS_LOG_STREAM_NAME')
ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
REGION = os.getenv('AWS_REGION')

# Create a CloudWatch Logs client
client = boto3.client(
    'logs',
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    region_name=REGION
)

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log_request(version: str, product: str, reach_id: int, return_format: str, source: str):
    log_message = {
        'version': version,
        'product': product.lower().replace(" ", ""),
        'reach_id': reach_id,
        'return_format': return_format,
        'source': source,
    }

    # Send the log message to CloudWatch
    response = client.put_log_events(
        logGroupName=LOG_GROUP_NAME,
        logStreamName=LOG_STREAM_NAME,
        logEvents=[
            {
                'timestamp': int(round(time.time() * 1000)),
                'message': json.dumps(log_message)
            }
        ]
    )
    return response
