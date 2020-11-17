FROM python:3.8-alpine

ENV LINKY_PORT /dev/ttyUSB0
ENV LINKY_BAUDRATE 1200

RUN apk add -U tzdata
RUN cp /usr/share/zoneinfo/Europe/Paris /etc/localtime

COPY . /opt/linkypy

WORKDIR /opt/linkypy

RUN pip3 install --no-cache-dir -r requirements.txt
RUN python setup.py install

ENTRYPOINT "linkypy run"