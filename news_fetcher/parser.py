import requests
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from dedup import is_processed, mark_processed

class BaseParser(ABC):
    def __init__(self, base_url=None):
        self.base_url = base_url

    def fetch(self, url=None):
        # Если не передан URL, используем базовый
        if url is None:
            if self.base_url is None:
                raise ValueError("URL не задан ни в параметрах, ни в базовом URL")
            url = self.base_url
        response = requests.get(url)
        response.encoding = response.apparent_encoding  # Автоопределение кодировки
        response.raise_for_status()
        return response.text

    def is_same_domain(self, url):
        if self.base_url is None:
            raise ValueError("Базовый URL не установлен")
        domain1 = urlparse(self.base_url).netloc.lower()
        domain2 = urlparse(url).netloc.lower()
        return domain1 == domain2

    @abstractmethod
    def parse(self, html):
        """Метод для парсинга HTML, должен быть реализован в наследниках."""
        pass


class LentaParser(BaseParser):
    def parse(self, html):
        logging.info(f"LentaParser начинает парсить {self.base_url}... ")
        soup = BeautifulSoup(html, 'html.parser')

        tab_content = soup.find('div', class_='parts-page')
        cards = tab_content.find_all('li', class_='parts-page__item')

        cards_data = []
        for idx, card in enumerate(cards):
            card_full_news_elem = card.find('a', class_='card-full-news _parts-news', href=True)
            if not card_full_news_elem:
                continue

            title = card_full_news_elem.find('h3', class_='card-full-news__title').text.strip()

            inner_url = urljoin(self.base_url, card_full_news_elem['href'])
            
            # Дедупликация
            if is_processed(inner_url):
                logging.info(f"{inner_url} is already has been parsed...")
                continue
            mark_processed(inner_url)

            logging.info(f"Fetching inner_url {inner_url}...")
            inner_page = self.fetch(inner_url)

            logging.info(f"Parsing inner_url {inner_url}...")
            if self.is_same_domain(inner_url):
                inner_soup = BeautifulSoup(inner_page, 'html.parser')
                article = inner_soup.find('div', class_='topic-body _news')

                title_div = article.find('div', class_='topic-body__title')
                content_div = article.find('div', class_='topic-body__content')

                if content_div:
                    content = content_div.get_text(separator=' ', strip=True)

                if title_div:
                    title = title_div.get_text(separator=' ', strip=True)
                    logging.info(title)
            else:
                content = None

            logging.info("Структура статьи собрана...")
            cards_data.append({
                "source": "lenta",
                "inner_url": inner_url,
                "title": title, 
                "content": content
            })

        logging.info(f"LentaParser закончила парсить {self.base_url}. ")
        return cards_data

class RIAParser(BaseParser):
    def parse(self, html):
        logging.info(f"RIAParser начинает парсить {self.base_url}... ")
        soup = BeautifulSoup(html, 'html.parser')

        # Находим блок с карточками
        tab_content = soup.find('div', class_='list')
        cards = tab_content.find_all('div', class_='list-item')

        # Извлекаем данные карточек
        cards_data = []
        for idx, card in enumerate(cards):
            # Получаем заголовок
            card_full_news_elem = card.find('a', class_='list-item__title', href=True)
            if not card_full_news_elem:
                continue

            title = card_full_news_elem.text.strip()

            inner_url = urljoin(self.base_url, card_full_news_elem['href'])
            
            # Дедупликация
            if is_processed(inner_url):
                logging.info(f"{inner_url} is already has been parsed...")
                continue
            mark_processed(inner_url)

            logging.info(f"Fetching inner_url {inner_url}...")
            inner_page = self.fetch(inner_url)

            logging.info(f"Parsing inner_url {inner_url}...")
            if self.is_same_domain(inner_url):
                inner_soup = BeautifulSoup(inner_page, 'html.parser')
                article = inner_soup.find('div', class_='layout-article__600-align')

                title_div = article.find('div', class_='article__title')
                content_div = article.find('div', class_='article__body')

                if content_div:
                    content = content_div.get_text(separator=' ', strip=True)

                if title_div:
                    title = title_div.get_text(separator=' ', strip=True)
                    logging.info(title)
            else:
                content = None

            logging.info("Структура статьи собрана...")
            cards_data.append({
                "source": "ria",
                "inner_url": inner_url,
                "title": title, 
                "content": content
            })
            
        logging.info(f"RIAParser закончила парсить {self.base_url}. ")
        return cards_data

class InterfaxParser(BaseParser):
    def parse(self, html):
        logging.info(f"InterfaxParser начинает парсить {self.base_url}... ")
        soup = BeautifulSoup(html, 'html.parser')

        # Находим контейнер с новостями
        news_container = soup.find('div', class_='newsmain')
        if not news_container:
            logging.warning("Не найден блок новостей на Interfax.")
            return []

        # Извлекаем ссылки на новости
        news_data = []
        for news_item in news_container.find_all('a', href=True):
            title_tag = news_item.find('h3')
            if not title_tag:
                continue

            title = title_tag.text.strip()
            inner_url = urljoin(self.base_url, news_item['href'])

            # Дедупликация
            if is_processed(inner_url):
                logging.info(f"{inner_url} уже обработан.")
                continue
            mark_processed(inner_url)

            logging.info(f"Fetching inner_url {inner_url}...")
            inner_page = self.fetch(inner_url)

            if not inner_page:
                logging.warning(f"Не удалось загрузить {inner_url}")
                continue

            logging.info(f"Parsing inner_url {inner_url}...")
            if self.is_same_domain(inner_url):
                inner_soup = BeautifulSoup(inner_page, 'html.parser')

                article = inner_soup.find('article', itemprop='articleBody')
                if article:
                    title_tag = article.find('h1', itemprop='headline')
                    title = title_tag.text.strip() if title_tag else title
                    content = article.get_text(separator=' ', strip=True)
                else:
                    logging.warning(f"Не найден article в {inner_url}")
                    content = None
            else:
                content = None

            logging.info(title)
            logging.info("Структура статьи собрана...")
            news_data.append({
                "source": "interfax",
                "inner_url": inner_url,
                "title": title,
                "content": content
            })

        logging.info(f"InterfaxParser завершил парсинг {self.base_url}. ")
        return news_data


