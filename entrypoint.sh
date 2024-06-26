#!/bin/sh

# Start the MinIO server in the background
minio server /data --console-address ":9001" &

# Function to check if MinIO server is ready
is_minio_ready() {
    curl --output /dev/null --silent --head --fail http://localhost:9000/minio/health/live
}

# Wait for the MinIO server to be ready
while ! is_minio_ready; do
    echo "Waiting for MinIO to be ready..."
    sleep 5
done

# Run MinIO client commands to create the buckets
/usr/local/bin/mc alias set myminio http://localhost:9000 rootuser rootpassword
/usr/local/bin/mc mb myminio/rawfile
/usr/local/bin/mc mb myminio/donefile

# Keep the container running
tail -f /dev/null
