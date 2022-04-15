import importlib
import logging

from linkypy import CONF

logger = logging.getLogger(__name__)


def get_price_extractors():

    pes = []
    for price_extractor in CONF.linkypy.price_extractors:
        logger.info("Loading price extractor '%s'..." % price_extractor)
        try:
            module_name, class_name = price_extractor.rsplit(".", 1)
            klass = getattr(importlib.import_module(module_name), class_name)
            pes.append(klass())
        except Exception as e:
            logger.error("An error occured while loading price extractor '%s': %s" % (price_extractor, str(e)))
            continue
    return pes
