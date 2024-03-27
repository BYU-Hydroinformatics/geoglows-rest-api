# GEOGLOWS ECMWF Streamflow Model Data Service

This is source code for the REST data service for the GEOGLOWS ECMWF Streamflow Project. This repository contains code for a docker container of a flask app. The data service is deployed at https://geoglows.ecmwf.int. Documentation and tutorials can be found at https://geoglows.ecmwf.int/training.

Required Environment Variables for Metrics tracking
- AWS_ACCESS_KEY_ID: AWS access key ID
- AWS_SECRET_ACCESS_KEY: AWS secret
- AWS_LOG_GROUP_NAME: AWS Cloudwatch log group
- AWS_LOG_STREAM_NAME AWS Cloudwatch log stream
- AWS_REGION: AWS region
