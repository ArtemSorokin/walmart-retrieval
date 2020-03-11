import logging
from pprint import pprint
from index import Index


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    index = Index()
    index.from_json("index.json")

    query = 'intel core i5, windows 10, black'
    scores, products = index.search_products(query, n_results=2)
    print(scores)
    pprint(products)

    query = 'Wi-Fi and Bluetooth 4.2 Combo (MU-MIMO supported)'
    scores, products = index.search_products(query, n_results=1)
    print(scores)
    pprint(products)
