import logging
import os
import uuid
from multiprocessing.dummy import Pool as ThreadPool

import camelot
import pandas as pd
import requests
from cachetools import TTLCache, cached
from linkypy.prices_extractors.base import BasePriceExtractor

logger = logging.getLogger(__name__)


ttl = 2592000
cache = TTLCache(maxsize=128, ttl=ttl)


class EDFPriceExtractor(BasePriceExtractor):

    PDFS = {
        "bleu": "https://particulier.edf.fr/content/dam/2-Actifs/Documents/Offres/Grille_prix_Tarif_Bleu.pdf",
        "vert": "https://particulier.edf.fr/content/dam/2-Actifs/Documents/Offres/grille-prix-vert-electrique.pdf",

    }
    OFFER_NAMES = PDFS.keys()
    OFFER_TYPES = ('BASE', 'HPHC')

    def __init__(self):

        super().__init__()

        self.provider_name = "EDF"

        # Preload PDFs
        pool = ThreadPool(1)
        _ = pool.map(self.download_from_provider, EDFPriceExtractor.PDFS.values())
        pool.close()
        pool.join()

    def get_available_offers_names(self):
        return EDFPriceExtractor.OFFER_NAMES

    def get_available_offers_types(self):
        return EDFPriceExtractor.OFFER_TYPES

    @cached(cache)
    def download_from_provider(self, url):

        logger.info("Updating prices cache from %s" % url)
        tmp_output = os.path.join("/tmp/%s.pdf" % str(uuid.uuid5(uuid.NAMESPACE_DNS, url)))
        headers = {"user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0"}

        with open(tmp_output, 'wb') as f:
            # Downloading PDF file
            f.write(requests.get(url, headers=headers).content)

        # Get tables from PDF
        tables = camelot.read_pdf(tmp_output)
        os.remove(tmp_output)

        # Cleaning raw table
        for table in tables[0:2]:
            # Keep only numerical values
            table.df = table.df.apply(lambda x: pd.to_numeric(x.astype(str).str.replace(',', '.'), errors='coerce'))
            # Drop rows with Nan
            table.df.dropna(how='all', inplace=True)
            # Reset indexes
            table.df.reset_index(drop=True, inplace=True)

        #############
        # Base prices
        df_base = tables[0].df
        # Rename columns
        df_base.columns = ['power', 'subscription', 'hp_kwh_price']
        # Set kWh price in euros, not cents.
        df_base['hp_kwh_price'] /= 100
        # Set power as integer
        df_base = df_base.astype({'power': 'int32'})
        # Set power as index
        df_base.set_index('power', inplace=True)

        #############
        # HPHC prices
        df_hphc = tables[1].df
        # Rename columns
        df_hphc.columns = ['power', 'subscription', 'hp_kwh_price', 'hc_kwh_price']
        # Set kWh price in euros, not cents.
        df_hphc['hp_kwh_price'] /= 100
        df_hphc['hc_kwh_price'] /= 100
        # Set power as integer
        df_hphc = df_hphc.astype({'power': 'int32'})
        # Set power as index
        df_hphc.set_index('power', inplace=True)

        # Return tables
        return df_base, df_hphc

    def get_prices_list(self, offer_name, offer_type):

        url = EDFPriceExtractor.PDFS[offer_name]
        df_base, df_hphc = self.download_from_provider(url)

        if offer_type == "BASE":
            return df_base
        elif offer_type == "HPHC":
            return df_hphc

    def get_prices(self, offer_name, offer_type, power):

        try:
            prices = self.get_prices_list(offer_name, offer_type).loc[power]
            return {
                'MONTHLY_SUBSCRIPTION_PRICE': prices['subscription'],
                'HP_KWH_PRICE': prices['hp_kwh_price'],
                'HC_KWH_PRICE': prices.get('hc_kwh_price', prices['hp_kwh_price']),
            }

        except Exception:
            logger.error("An error occured while syncing prices. Falling back to environment variable prices: %s" % self.fallback_prices, exc_info=True)
            return self.fallback_prices
