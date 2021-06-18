import os

import yaml
from munch import munchify
import logging

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader as SafeLoader

logger = logging.getLogger(__name__)


def get_config(name):
    default_filenames = [
        # DEV
        "%s/etc/%s/%s.yaml" % (os.path.dirname(os.path.dirname(__file__)), name, name),
        # USER
        "%s/.%s.yaml" % (os.path.expanduser("~"), name),
        # SYSTEM
        "/etc/%s/%s.yaml" % (name, name),
        # LOCAL
        "/usr/local/etc/%s/%s.yaml" % (name, name),
    ]

    for filename in default_filenames:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                conf = munchify(yaml.load(f.read(), SafeLoader))
                conf.config_file = filename
                return conf

    message = "Cannot find any configuration file. Tried in order:"
    for f in default_filenames:
        message += "    - %s" % f
    raise Exception(message)


CONF = get_config('linkypy')
