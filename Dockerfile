FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN pip install --upgrade pip
RUN pip install awscli requests

COPY ./artifacts /app

RUN mkdir -p /data/nginx
VOLUME ["/data/nginx"]
#RUN cp /app/cache.conf /etc/nginx/conf.d/cache.conf
#RUN cat /app/cache_settings.conf >> /etc/nginx/uwsgi_params

# Setup nginx on debug mode
RUN sed -i -e 's/warn/debug/g' /etc/nginx/nginx.conf

RUN sed -i -e 's/keepalive_timeout  65;/keepalive_timeout 240s;/g' /etc/nginx/nginx.conf

RUN ln -s /dev/stdout /var/log/uwsgi.log

RUN echo "buffer-size = 65535" >> /etc/uwsgi/uwsgi.ini

# RUN echo "post-buffering = 65535" >> /etc/uwsgi/uwsgi.ini

ENV NGINX_MAX_UPLOAD 8g
