"""
Ручной demo-скрипт поиска по векторной базе.

Не pytest-тест (без assert, без функций test_*, делает живой платный
вызов OpenAI API при каждом запуске) — раньше лежал в tests/ как
test_search.py и по имени файла собирался pytest'ом как модуль
тестов; сам импорт (без единого реального теста внутри) уже выполнял
API-вызов и требовал существования 'test_full_pipeline/vector_db/' —
это ронять весь `pytest tests/` без внятной причины (см.
decisions/decision-log.md). Перед запуском поправьте путь к своей
векторной базе ниже.
"""
import json
import numpy as np
import faiss
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
import os

# Загружаем базу
index = faiss.read_index('test_full_pipeline/vector_db/index.faiss')
data = json.load(open('test_full_pipeline/vector_db/dataset.json', 'r', encoding='utf-8'))

# Клиент
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url='https://openai.api.proxyapi.ru/v1'
)

# Поисковый запрос
query = 'что такое RAG?'
response = client.embeddings.create(
    model='text-embedding-3-small',
    input=query
)
query_vector = np.array([response.data[0].embedding], dtype='float32')

# Ищем
D, I = index.search(query_vector, k=3)

print('=== Поиск по запросу:', query, '===')
print()
for i, idx in enumerate(I[0]):
    print(f'Результат {i+1}:')
    print(f'  Text: {data[idx]["text"][:100]}...')
    print(f'  Summary: {data[idx]["metadata"].get("summary", "N/A")}')
    print(f'  Keywords: {data[idx]["metadata"].get("keywords", [])}')
    print()
