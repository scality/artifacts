FROM nginx:1.15.1-alpine

ENV NGINX_LISTEN_PORT 80
ENV ARTIFACTS_HOST 127.0.0.1:50000

COPY artifacts.conf.template /etc/nginx/conf.d/

VOLUME ["/data/nginx"]

EXPOSE 80

CMD ["/bin/sh", "-c", "envsubst '${NGINX_LISTEN_PORT} ${ARTIFACTS_HOST}' < /etc/nginx/conf.d/artifacts.conf.template > /etc/nginx/conf.d/default.conf && cat /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
