import logging
from collections import defaultdict
from rank_bm25 import BM25Okapi
from index import Index
from pprint import pprint


def baseline_model(query: str, n_results: int):
    def preprocess(token):
        token = token.replace('-', ' ')
        token = ''.join([c for c in token if (c.isalnum() or c == ' ') and c != 'â'])
        return token

    index = Index()
    index.from_json("index.json")

    products = []
    for product in index.products:
        products.append(defaultdict(str))
        for feature, value in product.items():
            products[-1][preprocess(feature.lower())] = preprocess(value.lower())

    tokenized_corpus = [[value for value in product.values()] for product in products]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = [preprocess(token) for token in query.split()]

    return bm25.get_top_n(tokenized_query, list(zip(index.descs, index.products)),
                          n=n_results)


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    pprint(baseline_model("intel-core-i3 windows-10 black", n_results=1))
