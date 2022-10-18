import logging
import os
import click
import serial
from linkypy import CONF
from linkypy.reader.packet_reader import LinkyPyPacketReader
from linkypy.prices_extractors import get_price_extractors


logging.basicConfig(level=getattr(logging, CONF.linkypy.loglevel),
                    format='%(asctime)s %(levelname)8s %(filename)24s %(message)s')
logging.propagate = False
logging.getLogger().setLevel(logging.WARN)

logging.getLogger("urllib3").setLevel(logging.WARN)
logging.getLogger("pdfminer").setLevel(logging.WARN)
logging.getLogger("camelot").setLevel(logging.WARN)
logging.getLogger("pdfplumber").setLevel(logging.WARN)
logging.getLogger("ghostscript").setLevel(logging.WARN)
logging.getLogger("linkypy").setLevel(getattr(logging, CONF.linkypy.loglevel))

logger = logging.getLogger(__name__)


@click.group()
def linkypy():
    """LinkyPy command line utility."""
    logger.info("Using configuration file: %s" % CONF.config_file)


@linkypy.command()
def run():
    """Launch LinkyPy reader loop."""

    # Get USB connection details through environment variables.
    linky_port = os.getenv('LINKY_PORT', '/dev/ttyUSB0')
    linky_baudrate = int(os.getenv('LINKY_BAUDRATE', 1200))

    logger.info("Connecting to Linky through USB dongle on %s (baudrate=%dbps)" % (linky_port, linky_baudrate))

    # Connect to serial port.
    linky_serial_port = serial.serial_for_url(linky_port, linky_baudrate,
                                              parity=serial.PARITY_EVEN,
                                              stopbits=serial.STOPBITS_ONE,
                                              bytesize=serial.SEVENBITS)

    logger.info("Connected to Linky: %s" % linky_serial_port.get_settings())

    # Launch the reader thread
    reader_thread = serial.threaded.ReaderThread(linky_serial_port, LinkyPyPacketReader)
    reader_thread.run()


@linkypy.command()
def prices():
    """Get prices from extractors."""
    prices_extractors = get_price_extractors()

    for prices_extractor in prices_extractors:
        for offer_name in prices_extractor.get_available_offers_names():
            for offer_type in prices_extractor.get_available_offers_types():
                print(prices_extractor.__class__.__name__, offer_name, offer_type, prices_extractor.get_prices(offer_name, offer_type, 9))
