#!/bin/sh

export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

echo "Stopping nginx..."
# Wait a bit before signaling the process to stop
sleep 5

# retrieve nginx status and check if there's any active connection
ACTIVE_CONNECTION="0"

while [ ${ACTIVE_CONNECTION} != "1" ]; do
  ACTIVE_CONNECTION=$(curl -s http://localhost/nginx_status | grep 'Active connections' | awk '{print $3}')
  echo "Active connections: ${ACTIVE_CONNECTION}"
  sleep 1
done

PID=$(cat /run/nginx.pid)
nginx -s quit
