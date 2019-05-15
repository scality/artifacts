#!/bin/sh

envsubst '${NGINX_LISTEN_PORT} ${ARTIFACTS_HOST} ${NGINX_NO_CACHE}'  \
  < /etc/nginx/conf.d/artifacts.conf.template \
  > /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'
