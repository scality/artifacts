#!/bin/sh

export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

echo "Stopping nginx..."
# Wait a bit before signaling the process to stop
sleep 5
PID=$(cat /run/nginx.pid)
nginx -s quit

echo "Waiting for nginx PID: ${PID} to stop..."
while [ -d /proc/$PID ]; do
  sleep 0.1
done
