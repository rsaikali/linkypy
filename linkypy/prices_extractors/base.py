import logging
import os

logger = logging.getLogger(__name__)


class BasePriceExtractor(object):

    def __init__(self):

        # Retrieve fallback prices from environment variables.
        self.fallback_prices = {
            'MONTHLY_SUBSCRIPTION_PRICE': float(os.getenv('MONTHLY_SUBSCRIPTION_PRICE', 0)),
            'HP_KWH_PRICE': float(os.getenv('HP_KWH_PRICE', 0)),
            'HC_KWH_PRICE': float(os.getenv('HC_KWH_PRICE', 0))
        }
