# -*- coding: utf-8 -*-
import datetime

import os
import pytz
from dateutil.relativedelta import relativedelta
from datetime import timedelta, tzinfo

import logging
from influxdb import InfluxDBClient


logger = logging.getLogger("influxdb_callback")
logging.getLogger("urllib3").setLevel(logging.ERROR)

KEEP_ONLY_KEYS = ['HCHC', 'HCHP', 'PAPP']

HP_KWH_PRICE = float(os.getenv('HP_KWH_PRICE', 0.1657))
HC_KWH_PRICE = float(os.getenv('HC_KWH_PRICE', 0.1249))
MONTHLY_SUBSCRIPTION_PRICE = float(os.getenv('MONTHLY_SUBSCRIPTION_PRICE', 14.34))

INFLUXDB_SERVICE_HOST = os.getenv('INFLUXDB_SERVICE_HOST', 'influxdb.local')
INFLUXDB_SERVICE_PORT = int(os.getenv('INFLUXDB_SERVICE_PORT', 31086))
INFLUXDB_DATABASE = os.getenv('INFLUXDB_DATABASE', 'linky')
INFLUXDB_USERNAME = os.getenv('INFLUXDB_USERNAME', 'admin')
INFLUXDB_PASSWORD = os.getenv('INFLUXDB_PASSWORD', 'password')


class InfluxDBCallback(object):

    def __init__(self, *args, **kwargs):
        super(InfluxDBCallback, self).__init__(*args, **kwargs)
        logger.info("Connecting to InfluxDB %s:%s ..." % (INFLUXDB_SERVICE_HOST, INFLUXDB_SERVICE_PORT))

        self.influx_client = InfluxDBClient(INFLUXDB_SERVICE_HOST, INFLUXDB_SERVICE_PORT,
                                            INFLUXDB_USERNAME, INFLUXDB_PASSWORD,
                                            INFLUXDB_DATABASE,
                                            retries=0, gzip=True)
        self.influx_client.create_database(INFLUXDB_DATABASE)
        logger.info("Connected to InfluxDB.")

    def callback(self, data, timestamp):
        """
        Stores data into InfluxDB.
        """
        keep_data = {}

        for key, value in data.items():
            if key not in KEEP_ONLY_KEYS:
                continue
            keep_data[key] = int(value)

        keep_data['CURRENT_COST'], keep_data['ESTIMATED_COST'] = self.get_price_and_estimate()

        json_body = [{
            "measurement": "linky",
            "time": timestamp,
            "fields": keep_data
        }]
        logger.info("Writing data [%s]" % keep_data)
        self.influx_client.write_points(json_body)

    def get_price_and_estimate(self):

        try:
            n = datetime.datetime.now().replace(tzinfo=simple_utc())
            local_tz = pytz.timezone('Europe/Paris')
            local_dt = n.replace(tzinfo=pytz.utc).astimezone(local_tz)
            now = local_tz.normalize(local_dt)

            # Get first day of month
            first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Get elapsed seconds since beginning of month
            elapsed_seconds = (now - first_of_month).total_seconds()

            # Get HP/HC consumption up to now.
            query = "SELECT first(HCHP) AS first_hp, last(HCHP) AS last_hp, \
                            first(HCHC) AS first_hc, last(HCHC) AS last_hc \
                     FROM linky WHERE time >= '%s'" % first_of_month.isoformat()
            results = next(self.influx_client.query(query).get_points())
            consumed_kwh_hp = (results['last_hp'] - results['first_hp']) / 1000.
            consumed_kwh_hc = (results['last_hc'] - results['first_hc']) / 1000.

            # Get consumed price
            price_today = (consumed_kwh_hp * HP_KWH_PRICE) + (consumed_kwh_hc * HC_KWH_PRICE)

            # Get beginning of next month
            first_of_next_of_month = first_of_month + relativedelta(months=1)

            # Get remaining seconds to beginning of next month
            remaining_seconds = (first_of_next_of_month - now).total_seconds()

            # Get remaining price from average price per second
            price_remaining = remaining_seconds * (price_today / elapsed_seconds)

            # Add everything, price since beginning of month + estimate + monthly subscription
            estimate_monthly = price_today + price_remaining + MONTHLY_SUBSCRIPTION_PRICE

            return float(round(price_today, 4) + MONTHLY_SUBSCRIPTION_PRICE), float(round(estimate_monthly, 4))
        except Exception:
            logger.error("An error occured while estimating price.", exc_info=True)
            return 0.0, 0.0


class simple_utc(tzinfo):
    def tzname(self, **kwargs):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)
