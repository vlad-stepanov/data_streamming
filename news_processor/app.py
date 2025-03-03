import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
import asyncpg
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)

app = FastAPI()

DB_CONFIG = {
    "user": "news_user",
    "password": "news_pass",
    "database": "news_db",
    "host": "postgres"
}

KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_TOPIC_ENRICHED = "news_enriched"

async def init_db():
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id SERIAL PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            entities JSONB DEFAULT '{}'::jsonb,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await conn.close()

async def consume_enriched_news():
    while True:
        try:
            consumer = AIOKafkaConsumer(
                KAFKA_TOPIC_ENRICHED,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="news_group",
                auto_offset_reset="earliest"
            )
            await consumer.start()
            db_conn = await asyncpg.connect(**DB_CONFIG)
            try:
                async for msg in consumer:
                    news_data = json.loads(msg.value.decode())
                    await db_conn.execute(
                        "INSERT INTO news (source, title, content, entities) VALUES ($1, $2, $3, $4)",
                        news_data["source"], news_data["title"], news_data.get("content"), json.dumps(news_data.get("entities", {}))
                    )
                    logging.info(f"Сохранена новость: {news_data['title']} с сущностями {news_data.get('entities')}")
            finally:
                await consumer.stop()
                await db_conn.close()
        except Exception as e:
            logging.error(f"Ошибка подключения к Kafka или БД: {e}. Переподключаемся через 10 секунд...")
            await asyncio.sleep(10)

@app.on_event("startup")
async def startup():
    logging.info("Waiting for 60 seconds before startup...")
    await asyncio.sleep(60)  # Ждем 60 секунд перед подключением
    await init_db()
    asyncio.create_task(consume_enriched_news())

@app.get("/")
async def health_check():
    return {"status": "running"}
