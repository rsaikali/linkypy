import logging
import os
import uuid
from multiprocessing.dummy import Pool as ThreadPool
from linkypy.prices_extractors.base import BasePriceExtractor

import pdfplumber
import requests
from cachetools import TTLCache, cached

logger = logging.getLogger(__name__)


ttl = 2592000
cache = TTLCache(maxsize=128, ttl=ttl)


class TotalDirectEnergiePriceExtractor(BasePriceExtractor):

    PDFS = {
        "classique": "https://total.direct-energie.com/fileadmin/Digital/Documents-contractuels/GT/grille-tarifaire-classique-particuliers.pdf",
        "online": "https://total.direct-energie.com/fileadmin/Digital/Documents-contractuels/GT/grille-tarifaire-online-particuliers.pdf",
        "verte": "https://total.direct-energie.com/fileadmin/Digital/Documents-contractuels/GT/grille-tarifaire-verte-particuliers.pdf",
    }
    OFFER_NAMES = PDFS.keys()
    OFFER_TYPES = ('BASE', 'HPHC')

    def __init__(self):

        self.provider_name = "Total Direct Energie"

        # Preload PDFs
        pool = ThreadPool()
        _ = pool.map(self.download_pdf, TotalDirectEnergiePriceExtractor.PDFS.values())
        pool.close()
        pool.join()

    def get_available_offers_names(self):
        return TotalDirectEnergiePriceExtractor.OFFER_NAMES

    def get_available_offers_types(self):
        return TotalDirectEnergiePriceExtractor.OFFER_TYPES

    @cached(cache)
    def download_pdf(self, url):

        logger.info("Updating prices cache from %s" % url)
        tmp_output = os.path.join("/tmp/%s.pdf" % str(uuid.uuid5(uuid.NAMESPACE_DNS, url)))
        with open(tmp_output, 'wb') as f:
            # Downloading PDF file
            f.write(requests.get(url).content)

        # Load PDF file
        pdf = pdfplumber.open(tmp_output)
        os.remove(tmp_output)

        return pdf

    @cached(cache)
    def get_prices_list(self, offer_name, offer_type):

        url = TotalDirectEnergiePriceExtractor.PDFS[offer_name]

        # Load PDF file
        pdf = self.download_pdf(url)

        # Find page with table
        table = None
        for i, page in enumerate(pdf.pages):
            table = page.extract_table()
            if table is not None:
                break

        # Error if not table found
        if table is None:
            raise Exception("Cannot find prices table in PDF %s" % url)

        # Search line with power (kVA) as first element
        data = []
        for line in table:
            if "kVA" in str(line):
                if offer_type == "BASE":
                    power = line[0]
                    if power is not None:
                        data.append(line[:7])
                elif offer_type == "HPHC":
                    power = line[7]
                    if power is not None:
                        data.append(line[7:])

        for i, line in enumerate(data):
            for j, item in enumerate(line):
                if item is None or len(item) == 0:
                    data[i][j] = data[i - 1][j]

        prices = {}
        for line in data:
            prices[int(line[0].split()[0])] = line

        return prices

    def get_prices(self, offer_name, offer_type, power):

        try:

            prices = self.get_prices_list(offer_name, offer_type)
            line = prices[power]

            if offer_type == "BASE":
                return {
                    'MONTHLY_SUBSCRIPTION_PRICE': float(line[2].replace(',', '.')),
                    'HP_KWH_PRICE': float(line[6].replace(',', '.')),
                    'HC_KWH_PRICE': float(line[6].replace(',', '.'))

                }
            elif offer_type == "HPHC":
                return {
                    'MONTHLY_SUBSCRIPTION_PRICE': float(line[2].replace(',', '.')),
                    'HP_KWH_PRICE': float(line[6].replace(',', '.')),
                    'HC_KWH_PRICE': float(line[10].replace(',', '.'))
                }

        except Exception:
            logger.error("An error occured while syncing prices. Falling back to environment variable prices: %s" % self.fallback_prices, exc_info=True)
            return self.fallback_prices
