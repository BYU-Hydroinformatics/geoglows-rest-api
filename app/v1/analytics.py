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
    """
    Posts a custom log to the aws cloudwatch logging service

    Requires environment variables
    - AWS_LOG_GROUP_NAME: the group name for the AWS CloudWatch log group within "logs".
    - AWS_LOG_STREAM_NAME: the stream name within the CloudWatch log group.

    Args:
        version: Either v1 or v2. Will be converted to a two digit code and placed at the beginning of the log message
        product: One of the product strings from the products tuple. Will be converted to a code using the product map
        reach_id: The unique id of the river being requested for. If not given, will be set to 00

        **kwargs:
            - region_no: Two digit code for the nga region (ex. 70 for north america)
            - source: Code defining source of request, i.e. app, api, etc. Defaults to 2

    Example usage:
        analytics.log_request(
            version="v2",
            product="forecaststats",
            reach_id=102001
        )

    Returns:
        the response from the CloudWatch service
    """
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
