import importlib
import logging

from linkypy import CONF

logger = logging.getLogger(__name__)


def get_callbacks():

    callbacks = []

    for callback in CONF.linkypy.callbacks:

        logger.info("Loading callback '%s'" % callback)
        try:
            module_name, class_name = callback.rsplit(".", 1)
            klass = getattr(importlib.import_module(module_name), class_name)
            instance = klass()
            callbacks.append(instance)
        except (ImportError, AttributeError) as e:
            logger.error("An error occured while loading callback '%s': %s" % (callback, str(e)))
            continue

    return callbacks
