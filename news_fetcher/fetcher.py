import asyncio
import json
import logging
import os
import json

from aiokafka import AIOKafkaProducer

import parser

logging.basicConfig(level=logging.INFO)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = 'news'

WEB_SOURCES = 'web_sources.json'

PARSER_REGISTRY = {
    'LentaParser': parser.LentaParser,
    'RIAParser': parser.RIAParser,
    'InterfaxParser': parser.InterfaxParser
}

logging.info("Reading input config...")

with open(WEB_SOURCES, 'r') as file:
    CONFIG = json.load(file)

async def send_to_kafka(producer, news_item):
    logging.info(f"Sending news_item and waiting...")
    await producer.send_and_wait(KAFKA_TOPIC, json.dumps(news_item).encode())

async def fetch_and_send():
    web_news = []
    for url, parser_class_name in CONFIG.items():
        try:
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
            await producer.start()

            parser_class = PARSER_REGISTRY.get(parser_class_name)
            if not parser_class:
                logging.info(f"Парсер с именем {parser_class_name} не найден для URL: {url}")
                continue
            
            parser_instance = parser_class(url)
            logging.info(f"Fetching {url}...")
            html = parser_instance.fetch()
            logging.info(f"Parsing {url} with {parser_class_name}...")
            data = parser_instance.parse(html)
            web_news.extend(data)

            for news_item in web_news:
                await send_to_kafka(producer, news_item)
                logging.info(f"Sending news_item to Kafka: {news_item['title']}")

        finally:
            await producer.stop()

async def main():
    logging.info("Waiting for 5 seconds...")
    await asyncio.sleep(5)  # Ждем 5 секунд перед подключением
    while True:
        logging.info("KafkaProducer is fetching and sending...")
        await fetch_and_send()
        logging.info("Waiting for 120 seconds...")
        await asyncio.sleep(120)  # Повторяем раз в 2 минуты

if __name__ == "__main__":
    asyncio.run(main())
