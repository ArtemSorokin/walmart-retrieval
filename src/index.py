from bs4 import BeautifulSoup
from collections import defaultdict
import logging
import json
import requests
import pickle
from copy import deepcopy

logger = logging.getLogger(__name__)


class Index:
    """"""

    SITE_URL = "https://walmart.com"

    CATEGORIES = {
        "tablets": "/browse/tablets/3944_1078524",
        "laptops": "/browse/electronics/all-laptop-computers/3944_3951_1089430_132960",
    }

    def __init__(self, category: str = None):
        self.category = category
        if category:
            self.downloadable = True
            self.href = Index.SITE_URL + Index.CATEGORIES[self.category]
        else:
            self.downloadable = False

        self.index = []
        self.inv_index = defaultdict(lambda: defaultdict(list))
        self.products = []

    def download_data(self, start_page=1, end_page=1, max_n_tries=5):
        """
        Скачать данные о товарах со страниц <start_page>..<end_page>
        включительно.
        <max_n_tries> попыток обращени к сайту на каждый товар
        """

        if not self.downloadable:
            logger.error("index cannot be downloaded")
            return

        logger.info("downloading pages {} to {} in {}...".format(str(start_page), str(end_page), self.category))

        product_id = -1
        for page_n in range(start_page, end_page + 1):
            product_n = 0

            href = self.href + "?page={}".format(page_n)
            html = requests.get(href)
            parsed_html = BeautifulSoup(html.text, "html.parser")
            all_products_html = parsed_html.find_all(attrs=["product-title-link"])

            for product_html in all_products_html:
                for _ in range(max_n_tries):
                    href = product_html["href"]
                    product_page = requests.get(Index.SITE_URL + href)
                    parsed_product_page = BeautifulSoup(product_page.text, "html.parser")
                    parsed_specs = parsed_product_page.find(attrs=["Specifications"])

                    if parsed_specs is None:
                        continue
                    else:
                        product_id += 1
                        product_n += 1

                    raw_specs = [spec.text for spec in parsed_specs.find_all("td")]

                    product_name = parsed_product_page.find("h1", {"class": "prod-ProductTitle"})["content"]
                    feature_names = raw_specs[::2]
                    feature_values = raw_specs[1::2]
                    features = dict(zip(feature_names, feature_values))

                    self.products.append(product_name)

                    for feature, value in features.items():
                        self.inv_index[feature][value].append(product_id)

                    break

            logger.info("downloaded data for page {}/{} in {} ({}/10 products)".format(str(page_n - start_page + 1), str(end_page - start_page + 1), self.category, str(product_n)))

        logger.info("finished downloading")

    def to_json(self, filename="index.json"):
        path = "data/{}".format(filename)
        index_dumps = json.dumps(self.inv_index)

        with open(path, "w") as f:
            f.write(index_dumps)

        with open(path.replace(".json", ".pkl"), "wb") as f:
            pickle.dump(self.products, f)

    def from_json(self, filename="index.json"):
        path = "data/{}".format(filename)

        with open(path, "r") as f:
            self.inv_index = json.load(f)

        with open(path.replace(".json", ".pkl"), "rb") as f:
            self.products = pickle.load(f)

    def merge_indices(self, other, inverted=True):
        new_index = Index()
        old_len = len(self.products)
        new_index.products = deepcopy(self.products) + deepcopy(other.products)

        if inverted:
            new_index.inv_index = deepcopy(self.inv_index)
            for feature, values in other.inv_index.items():
                for value, products in values.items():
                    for product in products:
                        new_index.inv_index[feature][value].append(old_len + product)
        else:
            print("not implemented")

        return new_index
