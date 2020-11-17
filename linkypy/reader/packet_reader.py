# -*- coding: utf-8 -*-
import datetime
from collections import OrderedDict
from string import printable

import serial.threaded
import _thread as thread

import logging


logger = logging.getLogger("linkypy")
KEEP_ONLY_KEYS = ['HCHC', 'HCHP', 'PAPP']


class LinkyPyChecksumError(Exception):
    pass


class LinkyPyPacketReader(serial.threaded.Packetizer):

    TERMINATOR = b'\x03\x02'

    def __init__(self, *args, **kwargs):
        super(LinkyPyPacketReader, self).__init__(*args, **kwargs)

    def handle_packet(self, packet):
        """
        Compute a Linky packet from the serial connection. Launches a new thread to handle data.
        """
        thread.start_new_thread(self.compute_packet, (packet, datetime.datetime.utcnow().isoformat()))

    def compute_packet(self, packet, timestamp):
        """
        Compute a Linky packet into a dictionary.
        """
        logger.info("-" * 80)
        logger.info("Timestamp: %s" % timestamp)

        # Remove unprintable characters
        packet = ''.join(c for c in str(packet.decode("utf-8")).strip() if c in printable)

        data = OrderedDict()

        for line in packet.splitlines():
            try:
                key, value = self.compute_line(line)
                if key is not None:
                    data[key] = value
            except ValueError:
                continue
            except Exception as e:
                logger.error(e)
                continue

        # for plugin in self.plugins:
        #     thread.start_new_thread(plugin.compute, (data.copy(), timestamp))

        return data

    def compute_line(self, line):
        """
        Try to read the 3 fields in given line: key / value / cksum

        Compute checksum as implemented by Enedis.

        .. note::

            Le principe du calcul du checksum est le suivant:

                - calcul de la somme ``S1`` de tous les caractères allant du début du champ «Etiquette» jusqu’au délimiteur (inclus) entre les
                  champs «Donnée» et «Checksum»).
                - cette somme déduite est tronquée sur 6 bits (cette opération est faite à l’aide d’un ET logique avec ``0x3F``).
                - pour obtenir le checksum, on additionne le résultat précédent ``S2`` à ``0x20``.

            En résumé: ``checksum = (S1 & 0x3F) + 0x20``

            Le résultat sera toujours un caractère ASCII imprimable compris entre ``0x20`` et ``0x5F``.

        .. seealso::

            PDF document: `Sorties de télé-information client des appareils de comptage Linky utilisés
            en généralisation par Enedis <https://www.enedis.fr/sites/default/files/Enedis-NOI-CPT_54E.pdf>`_

        """
        try:
            key, value, checksum = line.split()
            if key not in KEEP_ONLY_KEYS:
                logger.info("%12s = %-15s [not flagged as kept]" % (key, value))
                return None, None

        except ValueError:
            raise

        computed_checksum = (sum(bytearray(key + ' ' + value, encoding='ascii')) & 0x3F) + 0x20
        if chr(computed_checksum) != checksum:
            raise LinkyPyChecksumError("%12s = %-15s [invalid checksum '%s' != '%s']" % (key, value, checksum, chr(computed_checksum)))

        logger.info("%12s = %-15s [checksum '%s' is OK, flagged as kept]" % (key, value, checksum))

        return key, value
