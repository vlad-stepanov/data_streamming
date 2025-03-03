FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Загружаем модель spaCy
RUN python -m spacy download ru_core_news_sm

COPY . .

CMD ["python", "extractor.py"]
