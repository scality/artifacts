FROM python:3.6

RUN pip install --upgrade pip
COPY requirements.txt /tmp/requirements.txt                                                    
RUN pip install -r /tmp/requirements.txt

WORKDIR /app
COPY ./artifacts /app

CMD ["uwsgi", "uwsgi.ini", "--master", "--thunder-lock"]
