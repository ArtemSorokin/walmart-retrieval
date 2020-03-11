from bs4 import BeautifulSoup
from collections import defaultdict
import logging
import json
import numpy as np
import requests
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

logger = logging.getLogger(__name__)


class Index:
    """
    products: List[dict]
        Список товаров как словарей <параметр>-<значение>
    descs: List[str]
        Список описаний товаров
    downloaders: Dict[str: Downloader]
        Список скачивателей данных — по одному на категорию
    idf: Dict[str: Dict[str: int]]
        Веса значений параметров
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
        self.idf = defaultdict(lambda: defaultdict(int))

    def add_downloader(self, category: str):
        downloader = Index.Downloader(self, category)
        self.downloaders[category] = downloader

    def to_json(self, filename="index.json"):
        path = "data/{}".format(filename)

        with open(path, "w") as f:
            f.write(json.dumps(self.products))

        with open(path.replace(".json", ".txt"), "w") as f:
            f.write('\n'.join(self.descs))

    def from_json(self, filename="index.json"):
        path = "data/{}".format(filename)

        with open(path, "r") as f:
            self.products = json.load(f)

        with open(path.replace(".json", ".txt"), "r") as f:
            self.descs = [desc[:-1] for desc in f.readlines()]

    def search_products(self,query: str, n_results: int):
        products = self.products

        def preprocess(token):
            try:
                return ''.join([c for c in token.lower() if (c.isalnum() or c == ' ') and c != 'â'])
            except AttributeError:
                return ''
            return token

        preprocessed_products = [defaultdict(str) for _ in range(len(products))]
        for i, product in enumerate(products):
            for feature, value in product.items():
                preprocessed_products[i][preprocess(feature)] = preprocess(value)

        # инвертировать индекс
        inv_index = defaultdict(lambda: defaultdict(list))
        for i, product in enumerate(products):
            for feature, value in product.items():
                inv_index[preprocess(feature)][preprocess(value)].append(i)

        # посчитать сколько товаров с каждой фичей
        feature_counts = defaultdict(int)
        for feature, values in inv_index.items():
            for value, products_with_value in values.items():
                feature_counts[feature] += len(products_with_value)

        # найти для каждого значения похожие
        feature_values = []
        for feature, values in inv_index.items():
            feature_values += values.keys()
        feature_values = list(set(feature_values))
        similar_values = defaultdict(list)

        vectorizer = TfidfVectorizer(ngram_range=(1, 4),
                                    analyzer="char",
                                    preprocessor=preprocess,)
        tfidf = vectorizer.fit_transform(feature_values)

        for i in range(len(feature_values) - 1):
            cosine_similarities = linear_kernel(tfidf[i:i+1], tfidf).flatten()
            related_docs_indices = cosine_similarities.argsort()[:-6:-1]
            similar_values[feature_values[i]] = related_docs_indices

        # дополнить индекс похожими
        for i, product in enumerate(products):
            for feature, value in product.items():
                if len(value) < 100:
                    inv_index[preprocess(feature)][preprocess(value)].append(i)
                    for similar_value_index in similar_values[feature]:
                        inv_index[preprocess(feature)][feature_values[similar_value_index]].append(i)

        # посчитать сколько раз встречается каждое значение
        value_counts = defaultdict(lambda: defaultdict(int))
        for feature, values in inv_index.items():
            for value, products_with_value in values.items():
                value_counts[feature][value] = len(products_with_value)

        # ~idf
        idf = defaultdict(lambda: defaultdict(int))
        for feature, counts in value_counts.items():
            for value, count in counts.items():
                idf[feature][value] = np.log(max([(feature_counts[feature] - count), 1e-5]) / (count + 1))

        tokenized_query = [preprocess(token.strip()) for token in query.split(',')]
        token_tfidf = vectorizer.transform(tokenized_query)
        scores = [0] * len(products)
        for i, token in enumerate(tokenized_query):
            candidates = []
            for product in products:
                for feature, value in product.items():
                    for product_n in inv_index[preprocess(feature)][preprocess(value)]:
                        candidates.append(product_n)
            for candidate in set(candidates):
                for feature, value in preprocessed_products[candidate].items():
                    value_i = feature_values.index(preprocessed_products[candidate][feature])
                    cosine_similarity = linear_kernel(tfidf[value_i:value_i+1], token_tfidf[i:i+1]).flatten()[0]
                    scores[candidate] += idf[preprocess(feature)][preprocess(value)] * np.log(1 + cosine_similarity)

        ranged_indices = np.argsort(scores)[::-1]
        return [scores[i] for i in ranged_indices[:n_results]],\
               [products[i] for i in ranged_indices[:n_results]]
