FROM sgtwilko/rpi-raspbian-opencv:stretch-latest

# Linky USB dongle
ENV LINKY_PORT "/dev/ttyUSB0"
ENV LINKY_BAUDRATE "1200"

# InfluxDB configuration
ENV INFLUXDB_SERVICE_HOST influxdb.local
ENV INFLUXDB_SERVICE_PORT 8086
ENV INFLUXDB_DATABASE linky
ENV INFLUXDB_USERNAME admin
ENV INFLUXDB_PASSWORD password

# Use PDF extraction to get prices from providers (fallback to HP_KWH_PRICE/HC_KWH_PRICE below).
ENV CURRENT_POWER "9"

# Fallback prices (0 if not set)
# ENV HP_KWH_PRICE "0.1657"
# ENV HC_KWH_PRICE "0.1249"
# ENV MONTHLY_SUBSCRIPTION_PRICE "14.34"

# Timezone
ENV TZ "Europe/Paris"

RUN apt-get update && \
    apt-get install --no-install-recommends -y git-core build-essential libjpeg-dev libssl-dev zlib1g-dev libffi-dev ghostscript && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /opt/linkypy/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/linkypy/requirements.txt

COPY . /opt/linkypy
WORKDIR /opt/linkypy

RUN git init
RUN python3 setup.py install
RUN rm -Rf /opt/linkypy

ENTRYPOINT ["linkypy", "run"]