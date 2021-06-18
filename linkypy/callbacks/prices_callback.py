# -*- coding: utf-8 -*-
import datetime
import logging
import os
from multiprocessing.dummy import Pool as ThreadPool

import pytz
from cachetools import TTLCache, cached
from dateutil.relativedelta import relativedelta
from influxdb import InfluxDBClient
from linkypy.prices_extractors import get_price_extractors

logger = logging.getLogger(__name__)

ttl = 60
cache = TTLCache(maxsize=128, ttl=ttl)


class PricesCallback(object):

    def __init__(self):

        self.prices_extractors = get_price_extractors()

        influxdb_service_host = os.getenv('INFLUXDB_SERVICE_HOST', 'influxdb.local')
        influxdb_service_port = int(os.getenv('INFLUXDB_SERVICE_PORT', 8086))
        influxdb_database = os.getenv('INFLUXDB_DATABASE', 'linky')
        influxdb_username = os.getenv('INFLUXDB_USERNAME', 'admin')
        influxdb_password = os.getenv('INFLUXDB_PASSWORD', 'password')

        logger.info("Connecting to InfluxDB %s:%s ..." % (influxdb_service_host, influxdb_service_port))
        self.influx_client = InfluxDBClient(influxdb_service_host, influxdb_service_port,
                                            influxdb_username, influxdb_password,
                                            influxdb_database, retries=0, gzip=True)
        self.influx_client.create_database(influxdb_database)
        logger.info("Successfully connected to InfluxDB: " + self.influx_client.ping())

        # Retention policy
        self.influx_client.create_retention_policy('linky_rp', '1w', 1, database=influxdb_database, default=False)

        # Continuous query
        self.influx_client.drop_continuous_query('prices_mean_cq', influxdb_database)
        select_clause = 'SELECT last("CURRENT_COST") as CURRENT_COST, last("ESTIMATED_COST") AS ESTIMATED_COST INTO prices_mean FROM linky_rp.prices GROUP BY time(1h), provider, offer_name, offer_type, month_name, month_number, year_number'
        self.influx_client.create_continuous_query('prices_mean_cq', select_clause, influxdb_database, 'EVERY 1m FOR 1h')

        self.power = int(os.getenv('CURRENT_POWER', 9))

    def compute(self, data, timestamp):
        """
        Stores data into InfluxDB.
        """
        if 'HCHP' not in data.keys() or 'HCHC' not in data.keys():
            logger.info("Incomplete Linky packet. Passing...")
            return

        self.data = data
        self.timestamp = timestamp

        # Make the Pool of workers
        pool = ThreadPool()
        _ = pool.map(self.calculate_prices, self.prices_extractors)
        pool.close()
        pool.join()

    def calculate_prices(self, price_extractor):

        for offer_name in price_extractor.get_available_offers_names():
            for offer_type in price_extractor.get_available_offers_types():
                try:
                    prices = price_extractor.get_prices(offer_name, offer_type, self.power)
                    costs = {}
                    if offer_type == "BASE":
                        costs = self.get_base_prices(int(self.data['HCHP']) + int(self.data['HCHC']), prices['HP_KWH_PRICE'],
                                                     prices['MONTHLY_SUBSCRIPTION_PRICE'])
                    elif offer_type == "HPHC":
                        costs = self.get_hphc_prices(int(self.data['HCHP']), int(self.data['HCHC']), prices['HP_KWH_PRICE'],
                                                     prices['HC_KWH_PRICE'], prices['MONTHLY_SUBSCRIPTION_PRICE'])

                    logger.info("%24s [%14s / %s]: %s" % (price_extractor.provider_name, offer_name, offer_type.lower(), costs))

                    # JSON body to send to influxdb.
                    # Add month tag for InfluxDB 'GROUP BY'
                    json_body = [{
                        "measurement": "prices",
                        "tags": {
                            "provider": price_extractor.provider_name,
                            "offer_name": offer_name,
                            "offer_type": offer_type,
                            "power": self.power,
                            "subscription_price": prices['MONTHLY_SUBSCRIPTION_PRICE'],
                            "hp_kwh_price": prices['HP_KWH_PRICE'],
                            "hc_kwh_price": prices['HC_KWH_PRICE'],
                            "month_number": datetime.datetime.now().month,
                            "year_number": datetime.datetime.now().year,
                            "month_name": datetime.datetime.now().strftime("%B").title()
                        },
                        "time": self.timestamp,
                        "fields": costs
                    }]

                    self.influx_client.write_points(json_body, time_precision='s', retention_policy='linky_rp')

                except Exception as e:
                    logger.error(e)
                    continue

    def get_hphc_prices(self, last_hp, last_hc, hp_price, hc_price, subscription_price):

        try:
            # Get first day of month
            first_of_month = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            tz = pytz.timezone(os.getenv("TZ", "Europe/Paris"))
            first_of_month = first_of_month.replace(tzinfo=tz)

            first_hp, first_hc = self.get_first_hphc(first_of_month.astimezone(pytz.utc).isoformat())

            consumed_kwh_hp = (last_hp - first_hp) / 1000.
            consumed_kwh_hc = (last_hc - first_hc) / 1000.

            # Get consumed price
            price_today = (consumed_kwh_hp * hp_price) + (consumed_kwh_hc * hc_price)

            # Get beginning of next month
            first_of_next_of_month = first_of_month + relativedelta(months=1)

            now = datetime.datetime.now()
            tz = pytz.timezone(os.getenv("TZ", "Europe/Paris"))
            now = now.replace(tzinfo=tz)

            # Get elapsed seconds since beginning of month
            elapsed_seconds = (now - first_of_month).total_seconds()

            # Get remaining seconds to beginning of next month
            remaining_seconds = (first_of_next_of_month - now).total_seconds()

            # Get remaining price from average price per second
            price_remaining = remaining_seconds * (price_today / elapsed_seconds)

            # Add everything, price since beginning of month + estimate + monthly subscription
            estimate_monthly = price_today + price_remaining + subscription_price

            return {
                'CURRENT_COST': round(price_today + subscription_price, 2),
                'ESTIMATED_COST': round(estimate_monthly, 2),
            }

        except Exception:
            logger.error("An error occured while estimating price.", exc_info=True)
            return None

    def get_base_prices(self, last_hp, hp_price, subscription_price):

        try:
            # Get first day of month
            first_of_month = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            tz = pytz.timezone(os.getenv("TZ", "Europe/Paris"))
            first_of_month = first_of_month.replace(tzinfo=tz)

            first_hp, first_hc = self.get_first_hphc(first_of_month.astimezone(pytz.utc).isoformat())
            first_kwh = first_hp + first_hc
            consumed_kwh = (last_hp - first_kwh) / 1000.

            # Get consumed price
            price_today = (consumed_kwh * hp_price)

            # Get beginning of next month
            first_of_next_of_month = first_of_month + relativedelta(months=1)

            now = datetime.datetime.now()
            tz = pytz.timezone(os.getenv("TZ", "Europe/Paris"))
            now = now.replace(tzinfo=tz)

            # Get elapsed seconds since beginning of month
            elapsed_seconds = (now - first_of_month).total_seconds()

            # Get remaining seconds to beginning of next month
            remaining_seconds = (first_of_next_of_month - now).total_seconds()

            # Get remaining price from average price per second
            price_remaining = remaining_seconds * (price_today / elapsed_seconds)

            # Add everything, price since beginning of month + estimate + monthly subscription
            estimate_monthly = price_today + price_remaining + subscription_price

            return {
                'CURRENT_COST': round(price_today + subscription_price, 2),
                'ESTIMATED_COST': round(estimate_monthly, 2),
            }

        except Exception:
            logger.error("An error occured while estimating price.", exc_info=True)
            return None

    @cached(cache)
    def get_first_hphc(self, first_of_month):

        # Get HP/HC consumption from beginning of month to now.
        query = "SELECT first(HCHP) AS first_hp, first(HCHC) AS first_hc \
                     FROM linky_mean WHERE time >= '%s'" % first_of_month
        results = next(self.influx_client.query(query).get_points())

        logger.info("Getting first HP/HC of the month: %s / %s" % (results['first_hp'], results['first_hc']))
        return results['first_hp'], results['first_hc']
