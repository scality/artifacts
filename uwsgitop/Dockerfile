FROM ubuntu:xenial

RUN apt-get update && apt install -y python wget
RUN wget --no-verbose --tries=3 --timeout=30 https://bootstrap.pypa.io/get-pip.py
RUN python get-pip.py pip==9.0.2
RUN pip install uwsgitop

CMD ["tail", "-f", "/dev/null"]
