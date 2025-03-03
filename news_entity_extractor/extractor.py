import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import spacy

logging.basicConfig(level=logging.INFO)

KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_TOPIC_IN = "news"
KAFKA_TOPIC_OUT = "news_enriched"

# Загружаем модель spaCy
nlp = spacy.load("ru_core_news_sm")

async def extract_entities():
    """Читает новости, извлекает сущности и отправляет в Kafka"""
    while True:
        try:
            consumer = AIOKafkaConsumer(
                KAFKA_TOPIC_IN,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="news_entity_group",
                auto_offset_reset="earliest"
            )
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

            await consumer.start()
            await producer.start()

            try:
                async for msg in consumer:
                    news_data = json.loads(msg.value.decode())
                    content = news_data.get("content", "")
                    
                    doc = nlp(content)
                    entities = {ent.text: ent.label_ for ent in doc.ents}

                    news_data["entities"] = entities
                    
                    # Отправляем обработанные данные в news_enriched
                    await producer.send_and_wait(KAFKA_TOPIC_OUT, json.dumps(news_data).encode())

                    logging.info(f"Обработана новость: {news_data['title']} -> {entities}")
            finally:
                await consumer.stop()
                await producer.stop()
        except Exception as e:
            logging.error(f"Ошибка в обработке сущностей: {e}. Переподключаемся через 10 секунд...")
            await asyncio.sleep(10)

async def main():
    await extract_entities()

if __name__ == "__main__":
    asyncio.run(main())
