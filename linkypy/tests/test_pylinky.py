import unittest

from linkypy.reader.packet_reader import LinkyPyChecksumError, LinkyPyPacketReader
from linkypy import CONF

GOOD_PACKET = bytearray(b"ADCO 012345678901 E\r\n\
OPTARIF HC.. <\r\n\
ISOUSC 45 ?\r\n\
HCHC 000835358 &\r\n\
HCHP 001262798 6\r\n\
PTEC HP..  \r\n\
IINST 002 Y\r\n\
IMAX 090 H\r\n\
PAPP 00510 \'\r\n\
HHPHC A ,\r\n\
MOTDETAT 000000 B\r")


class TestLinkyPy(unittest.TestCase):
    """
    PyLinky unittests.
    """

    def setUp(self):
        CONF.linkypy.plugins = []

    def test_001_compute_line(self):
        """
        Testing correct checksum
        """
        key, value = LinkyPyPacketReader().compute_line("ADCO 012345678901 E")
        self.assertEqual(key, "ADCO")
        self.assertEqual(value, "012345678901")

    def test_002_compute_line_error(self):
        """
        Testing incorrect checksum
        """
        with self.assertRaises(LinkyPyChecksumError):
            LinkyPyPacketReader().compute_line("ADCO 012345678901 0")

    def test_003_handle_packet(self):
        """
        Testing a correct Linky packet
        """
        lpr = LinkyPyPacketReader()
        data = lpr.handle_packet(GOOD_PACKET)
        self.assertEqual(len(data.keys()), 11, "Should find keys in Linky packet.")
