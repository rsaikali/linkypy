# -*- coding: utf-8 -*-
import datetime
import logging
import os

from influxdb import InfluxDBClient

logger = logging.getLogger(__name__)


class InfluxDBCallback(object):

    def __init__(self):

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

        # Retention policy
        self.influx_client.create_retention_policy('linky_rp', '1w', 1, database=influxdb_database, default=False)

        # Continuous query
        self.influx_client.drop_continuous_query('linky_mean_cq', influxdb_database)
        select_clause = 'SELECT mean("PAPP") as PAPP, last("HCHC") AS HCHC, last("HCHP") AS HCHP INTO "linky_mean" FROM linky_rp.linky GROUP BY time(1h)'
        self.influx_client.create_continuous_query('linky_mean_cq', select_clause, influxdb_database, 'EVERY 1m FOR 1h')

        logger.info("Successfully connected to InfluxDB: " + self.influx_client.ping())

    def compute(self, data, timestamp):
        """
        Stores data into InfluxDB.
        """
        keep_data = {}

        for key, value in data.items():
            if key not in ['HCHC', 'HCHP', 'PAPP']:
                continue
            try:
                keep_data[key] = int(value)
                logger.info("Keeping Linky data: %12s = %-12s" % (key, value))
            except Exception as e:
                logger.error(e)

        # JSON body to send to influxdb.
        # Add month tag for InfluxDB 'GROUP BY'
        json_body = [{
            "measurement": "linky",
            "tags": {
                "month_number": datetime.datetime.now().month,
                "year_number": datetime.datetime.now().year,
                "month_name": datetime.datetime.now().strftime("%B").title()
            },
            "time": timestamp,
            "fields": keep_data
        }]

        self.save(json_body)

    def save(self, json_body):
        logger.info("Writing InfluxDB points")
        self.influx_client.write_points(json_body, time_precision='s', retention_policy='linky_rp')
