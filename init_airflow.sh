#!/bin/bash

# Wait for Airflow webserver to be ready
sleep 20

# Delete existing connection if it exists
airflow connections delete 'minio_default' || true

# Set up Airflow connections
airflow connections add 'minio_default' \
    --conn-type 'aws' \
    --conn-extra '{"aws_access_key_id": "rootuser", "aws_secret_access_key": "rootpassword", "host": "http://minio:9000"}'

# Continue with the default Airflow entrypoint
exec /entrypoint "$@"
