FROM nginx:1.15.1-alpine

ENV NGINX_LISTEN_PORT 80
ENV ARTIFACTS_HOST 127.0.0.1:50000
ENV NGINX_NO_CACHE 0

COPY artifacts.conf.template /etc/nginx/conf.d/

COPY start.sh /

VOLUME ["/data/nginx"]

EXPOSE 80

CMD ["/start.sh"]
