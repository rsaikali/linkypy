import logging
import os
import uuid
from multiprocessing.dummy import Pool as ThreadPool
from linkypy.prices_extractors.base import BasePriceExtractor

import camelot
import numpy as np
import pandas as pd
import requests
from cachetools import TTLCache, cached

logger = logging.getLogger(__name__)


ttl = 2592000
cache = TTLCache(maxsize=128, ttl=ttl)


class EngiePriceExtractor(BasePriceExtractor):

    PDFS = {
        "elec_energie": "https://particuliers.engie.fr/content/dam/pdf/fiches-descriptives/fiche-descriptive-elec-energie-garantie.pdf"
    }
    OFFER_NAMES = PDFS.keys()
    OFFER_TYPES = ('BASE', 'HPHC')

    def __init__(self):

        super().__init__()

        self.provider_name = "Engie"

        # Preload PDFs
        pool = ThreadPool(1)
        _ = pool.map(self.download_from_provider, EngiePriceExtractor.PDFS.values())
        pool.close()
        pool.join()

    def get_available_offers_names(self):
        return EngiePriceExtractor.OFFER_NAMES

    def get_available_offers_types(self):
        return EngiePriceExtractor.OFFER_TYPES

    @cached(cache)
    def download_from_provider(self, url):

        logger.info("Updating prices cache from %s" % url)

        tmp_output = os.path.join("/tmp/%s.pdf" % str(uuid.uuid5(uuid.NAMESPACE_DNS, url)))
        headers = {"user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0"}

        with open(tmp_output, 'wb') as f:
            # Downloading PDF file
            f.write(requests.get(url, headers=headers).content)

        # Get tables from PDF
        tables = camelot.read_pdf(tmp_output, pages="3")
        os.remove(tmp_output)

        table = tables[0]

        # Add a power column at the end before split
        table.df['power'] = table.df[0]

        # Split base and hphc prices list
        dfs = np.split(table.df, [5], axis=1)

        # Cleaning raw table
        for i, df in enumerate(dfs):
            # Keep only numerical values
            df = df.apply(lambda x: pd.to_numeric(x.astype(str).str.replace(',', '.'), errors='coerce'))
            # Drop rows with Nan
            df.dropna(how='all', inplace=True)
            # Reset indexes
            df.reset_index(drop=True, inplace=True)
            dfs[i] = df

        #############
        # Base prices
        df_base = dfs[0]
        # Drop HT prices
        df_base.drop([1, 3], axis=1, inplace=True)
        # Fill NaN from previous values
        df_base.fillna(method='ffill', inplace=True)
        # Rename columns
        df_base.columns = ['power', 'subscription', 'hp_kwh_price']
        # Set subscription per month instead of per year
        df_base['subscription'] /= 12
        # Set power as integer
        df_base = df_base.astype({'power': 'int32'})
        # Set power as index
        df_base.set_index('power', inplace=True)

        #############
        # HPHC prices
        df_hphc = dfs[1]
        # Drop empty first row
        df_hphc.drop([0], axis=0, inplace=True)
        # Reset column names
        df_hphc.columns = range(df_hphc.shape[1])
        # Drop HT prices
        df_hphc.drop([0, 2, 4], axis=1, inplace=True)
        # Fill NaN from previous values
        df_hphc.fillna(method='ffill', inplace=True)
        # Rename columns
        df_hphc.columns = ['subscription', 'hp_kwh_price', 'hc_kwh_price', 'power']
        # Set subscription per month instead of per year
        df_hphc['subscription'] /= 12
        # Set power as integer
        df_hphc = df.astype({'power': 'int32'})
        # Set power as index
        df_hphc.set_index('power', inplace=True)

        # Return tables
        return df_base, df_hphc

    def get_prices_list(self, offer_name, offer_type):

        url = EngiePriceExtractor.PDFS[offer_name]
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
