FROM python:3.9-slim-buster

ENV LINKY_PORT "/dev/ttyUSB0"
ENV LINKY_BAUDRATE "1200"

ENV HP_KWH_PRICE "0.1657"
ENV HC_KWH_PRICE "0.1249"
ENV MONTHLY_SUBSCRIPTION_PRICE "14.34"

ENV INFLUXDB_SERVICE_HOST influxdb.local
ENV INFLUXDB_SERVICE_PORT 31086
ENV INFLUXDB_DATABASE linky
ENV INFLUXDB_USERNAME admin
ENV INFLUXDB_PASSWORD password
ENV TZ "Europe/Paris"

RUN apt-get update && \
    apt-get install --no-install-recommends -y git-core && \
    rm -rf /var/lib/apt/lists/*

COPY . /opt/linkypy

WORKDIR /opt/linkypy

RUN git init
RUN pip install --no-cache-dir -r requirements.txt
RUN python setup.py install
RUN rm -Rf /opt/linkypy

ENTRYPOINT ["linkypy", "run"]