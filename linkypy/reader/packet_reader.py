# -*- coding: utf-8 -*-
import datetime
import logging
import re

import serial.threaded
try:
    import thread  # noqa
except ImportError:
    import _thread as thread  # noqa

from linkypy.callbacks import get_callbacks

logger = logging.getLogger(__name__)


class LinkyPyChecksumError(Exception):
    pass


class LinkyPyPacketError(Exception):
    pass


class LinkyPyPacketReader(serial.threaded.Packetizer):

    TERMINATOR = b'\x03\x02'

    def __init__(self, *args, **kwargs):
        super(LinkyPyPacketReader, self).__init__(*args, **kwargs)
        self.callbacks = []

    def connection_made(self, transport):
        super(LinkyPyPacketReader, self).connection_made(transport)

        # Load callbacks from configuration file.
        self.callbacks = get_callbacks()

        logger.warn("First packet may have checksum errors as it is not complete.")

    def handle_packet(self, packet):
        """
        Compute a Linky packet into a dictionary.
        """
        logger.info("Received packet from Linky [%d characters]" % len(packet))
        timestamp = datetime.datetime.utcnow().isoformat()
        data = {}

        # Compute each line and fill a dictionary.
        for line in packet.decode("utf-8").strip().splitlines():
            try:
                key, value = self.compute_line(line)
                data[key] = value
            except (LinkyPyChecksumError, LinkyPyPacketError) as lpe:
                logger.error(lpe)
                return data.copy()
            except Exception as e:
                logger.error(e, exc_info=True)
                return data.copy()

        # Compute data through each declared callback
        for callback in self.callbacks:
            try:
                callback.compute(data.copy(), timestamp)
            except LinkyPyChecksumError:
                logger.error("An error occured.", exc_info=True)

        return data.copy()

    def compute_line(self, line):
        """
        Try to read the 3 fields in given line: key / value / checksum

        Compute checksum as implemented by Enedis.

        .. note::

            Le principe du calcul du checksum est le suivant:

                - calcul de la somme ``S1`` de tous les caractères allant du début du champ «Etiquette» jusqu’au délimiteur (inclus) entre les champs «Donnée» et «Checksum»).
                - cette somme déduite est tronquée sur 6 bits (cette opération est faite à l’aide d’un ET logique avec ``0x3F``).
                - pour obtenir le checksum, on additionne le résultat précédent ``S2`` à ``0x20``.

            En résumé: ``checksum = (S1 & 0x3F) + 0x20``

            Le résultat sera toujours un caractère ASCII imprimable compris entre ``0x20`` et ``0x5F``.

        .. seealso::

            PDF document: `Sorties de télé-information client des appareils de comptage Linky utilisés
            en généralisation par Enedis <https://www.enedis.fr/sites/default/files/Enedis-NOI-CPT_54E.pdf>`_

        """
        # Split line with spaces.
        try:
            key, value, checksum = re.split(' +', line)

            # Fix checksum if it was a space. Not nice, will see later how to do better.
            checksum = ' ' if checksum == '' else checksum

            # Compute checksum following Enedis specifications.
            computed_checksum = (sum(bytearray(key + ' ' + value, encoding='ascii')) & 0x3F) + 0x20
        except Exception:
            raise LinkyPyPacketError("Invalid line received: [%s]" % line)

        # If checksum is incorrect, raise error.
        if chr(computed_checksum) != checksum:
            raise LinkyPyChecksumError("%12s = %-15s [invalid checksum '%s' != '%s']" % (key, value, checksum, chr(computed_checksum)))

        logger.debug("%12s = %-15s [checksum '%s' is OK]" % (key, value, checksum))

        # Return key and value if checksum is correct.
        return key, value
