#!/bin/bash
full_url=$1

status=$(wget -q -S -O /dev/null $full_url 2>&1 | head -1 | sed -e 's/^ *//' | cut -d\  -f2)

echo $status

if [ -n "$status" ] && [ $status -eq 404 ]
then
  exit 0
fi

exit 1
