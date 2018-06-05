FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN pip install --upgrade pip
RUN pip install awscli requests uwsgitop

# patch entrypoint to limit nginx bandwidth
# protect against changes in original with sha512 check
COPY entrypoint_sha512 entrypoint_patch /
RUN sha512sum -c /entrypoint_sha512
RUN patch -t -p 0 -d / < /entrypoint_patch
# end patch

COPY ./artifacts /app

RUN mkdir -p /data/nginx
VOLUME ["/data/nginx"]
RUN cp /app/cache.conf /etc/nginx/conf.d/cache.conf
RUN cat /app/cache_settings.conf >> /etc/nginx/uwsgi_params

ENV NGINX_MAX_UPLOAD 8g
