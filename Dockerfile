FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN pip install --upgrade pip
RUN pip install awscli requests

COPY ./artifacts /app

RUN mkdir -p /data/nginx
VOLUME ["/data/nginx"]
RUN cp /app/cache.conf /etc/nginx/conf.d/cache.conf
RUN cat /app/cache_settings.conf >> /etc/nginx/uwsgi_params

# Setup nginx on debug mode
RUN sed -i -e 's/warn/debug/g' /etc/nginx/nginx.conf

ENV NGINX_MAX_UPLOAD 8g
