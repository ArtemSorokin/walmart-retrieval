import logging
from index import Index


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    index = Index()
    index.add_downloader("laptops")
    index.add_downloader("tablets")
    index.downloaders["laptops"].download_data(start_page=1, end_page=30)
    index.downloaders["tablets"].download_data(start_page=1, end_page=15)
    index.to_json()
