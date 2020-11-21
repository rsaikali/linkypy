# -*- coding: utf-8 -*-
import logging
import serial
import click
import os
from linkypy.reader.packet_reader import LinkyPyPacketReader
from linkypy.callback.influxdb_callback import InfluxDBCallback

LINKY_PORT = os.getenv('LINKY_PORT', '/dev/ttyUSB0')
LINKY_BAUDRATE = int(os.getenv('LINKY_BAUDRATE', 1200))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(name)20s] %(levelname)8s %(message)s')
logger = logging.getLogger("linkypy")


@click.group()
def linkypy():
    """LinkyPy command line utility."""
    pass


@linkypy.command()
def run():
    """Launch LinkyPy reader."""

    lpr = LinkyPyPacketReader
    lpr.callbacks = [InfluxDBCallback().callback]

    linky_serial_port = serial.serial_for_url(LINKY_PORT, LINKY_BAUDRATE,
                                              parity=serial.PARITY_EVEN,
                                              stopbits=serial.STOPBITS_ONE,
                                              bytesize=serial.SEVENBITS)

    reader_thread = serial.threaded.ReaderThread(linky_serial_port, lpr)
    reader_thread.run()
