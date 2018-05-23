FROM python:3.6

RUN pip install --upgrade pip

COPY ./artifacts /app

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

WORKDIR /app

CMD ["python", "main.py"]
