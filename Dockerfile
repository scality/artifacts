FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN pip install --upgrade pip
RUN pip install awscli requests

COPY ./artifacts /app

ENV NGINX_MAX_UPLOAD 2g
