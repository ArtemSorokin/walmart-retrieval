from bs4 import BeautifulSoup
from collections import defaultdict
import logging
import json
import requests
import pickle
from copy import deepcopy

logger = logging.getLogger(__name__)


class Index:
    """
    products: List[dict]
        Список товаров как словарей <параметр>-<значение>
    descs: List[str]
        Список описаний товаров
    downloaders: Dict[str: Downloader]
        Список скачивателей данных — по одному на категорию
    """

    class Downloader:
        """
        category: str
            Категория товаров для скачивания
        href: str
            Ссылка на страницу со списком товаров
        index: Index
            Индекс, к которому относится скачиватель
        """

        SITE_URL = "https://walmart.com"

        CATEGORIES = {
            "tablets": "/browse/tablets/3944_1078524",
            "laptops": "/browse/electronics/all-laptop-computers/3944_3951_1089430_132960",
        }

        def __init__(self, index, category: str):
            self.category = category
            self.href = Index.Downloader.SITE_URL + Index.Downloader.CATEGORIES[self.category]
            self.index = index

        def download_data(self, start_page=1, end_page=1, max_n_tries=5):
            """
            Скачать данные о товарах со страниц <start_page>..<end_page>
            включительно в индекс.
            <max_n_tries> попыток обращени к сайту на каждый товар
            """

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
                        product_page = requests.get(Index.Downloader.SITE_URL + href)
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

                        self.index.products.append(features)
                        self.index.descs.append(product_name)

                        break

                logger.info("downloaded data for page {}/{} in {}".format(str(page_n - start_page + 1), str(end_page - start_page + 1), self.category))

            logger.info("finished downloading")

    def __init__(self, category: str = None):
        self.products = []
        self.descs = []
        self.downloaders = {}

    def add_downloader(self, category: str):
        downloader = Index.Downloader(self, category)
        self.downloaders[category] = downloader

    def to_json(self, filename="index.json"):
        path = "data/{}".format(filename)

        with open(path, "w") as f:
            f.write(json.dumps(self.products))

        with open(path.replace(".json", ".pkl"), "wb") as f:
            pickle.dump(self.descs, f)

    def from_json(self, filename="index.json"):
        path = "data/{}".format(filename)

        with open(path, "r") as f:
            self.products = json.load(f)

        with open(path.replace(".json", ".pkl"), "rb") as f:
            self.descs = pickle.load(f)

    def find_matches(self, query):
        pass
