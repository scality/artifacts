FROM tiangolo/uwsgi-nginx-flask:flask-python3.5

RUN pip install --upgrade pip
RUN pip install awscli requests moto

COPY ./artifacts /app
COPY upload_1g.conf /etc/nginx/conf.d/
