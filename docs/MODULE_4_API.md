# API Модуля 4: Векторизация и векторная БД

**Версия:** 2.2.0  
**Дата:** 2026-02-18  
**Автор:** Line_GV

## Обзор

Модуль 4 реализует этапы 7–8 пайплайна подготовки данных для RAG-систем:

- **Этап 7:** Проверка качества данных перед векторизацией
- **Этап 8:** Генерация эмбеддингов через OpenAI API и сохранение в векторную БД (FAISS)

## Зависимости

```bash
pip install openai faiss-cpu numpy
```

## Основные функции

### `validate_data(final_dataset)`

Проверяет качество данных перед векторизацией.

**Параметры:**

- `final_dataset` (List[Dict[str, Any]]): Список чанков с текстом и метаданными.

**Возвращает:**

- `Dict[str, Any]`: Словарь с результатами валидации:
  - `total_chunks`: Общее количество чанков
  - `empty_chunks`: Список индексов пустых чанков
  - `avg_length`: Средняя длина чанка в символах
  - `stats`: Подробная статистика

**Пример использования:**

```python
from src.vectorizer import validate_data

validation_result = validate_data(chunks)

print(f"Всего чанков: {validation_result['total_chunks']}")
print(f"Пустых чанков: {len(validation_result['empty_chunks'])}")
print(f"Средняя длина: {validation_result['avg_length']:.2f} символов")
```

**Вывод в консоль:**

```
============================================================
[Этап 7: Проверка качества]
Всего чанков: 48
Пустых чанков: 0
Средняя длина: 480 символов
Мин/Макс длина: 50/1500
============================================================
```

---

### `save_to_vector_db(final_dataset, db_type, model_name, api_key, api_base, output_dir)`

Генерирует эмбеддинги и сохраняет в векторную БД.

**Параметры:**

- `final_dataset` (List[Dict[str, Any]]): Список чанков с текстом и метаданными.
- `db_type` (str, optional): Тип векторной БД. По умолчанию `"faiss"`.
- `model_name` (str, optional): Название модели эмбеддингов OpenAI. По умолчанию `"text-embedding-3-small"`.
- `api_key` (str, optional): API ключ OpenAI. Если `None`, использует переменную окружения `OPENAI_API_KEY`.
- `api_base` (str, optional): Базовый URL API. По умолчанию `"https://openai.api.proxyapi.ru/v1"`.
- `output_dir` (str, optional): Директория для сохранения результатов. По умолчанию `"output"`.

**Возвращает:**

- `Dict[str, Any]`: Словарь с результатами векторизации:
  - `success`: Успешность операции
  - `embeddings`: Список эмбеддингов
  - `embedding_dim`: Размерность эмбеддингов
  - `vector_db_path`: Путь к индексу FAISS
  - `dataset_path`: Путь к датасету JSON
  - `metadata_path`: Путь к метаданным индекса
  - `total_vectors`: Количество векторов

**Создаваемые файлы:**

- `output/vector_db/index.faiss`: Индекс FAISS
- `output/vector_db/dataset.json`: Полный датасет в формате JSON
- `output/vector_db/metadata.json`: Метаданные индекса

**Пример использования:**

```python
from src.vectorizer import save_to_vector_db

vectorization_result = save_to_vector_db(
    chunks,
    db_type="faiss",
    model_name="text-embedding-3-small",
    api_base="https://openai.api.proxyapi.ru/v1",
    output_dir="output"
)

print(f"Создано {vectorization_result['total_vectors']} векторов")
print(f"Размерность: {vectorization_result['embedding_dim']}")
print(f"Индекс сохранён: {vectorization_result['vector_db_path']}")
```

**Настройка API ключа:**

```python
import os

# Через переменную окружения
os.environ["OPENAI_API_KEY"] = "your-api-key-here"

# Или напрямую в функции
vectorization_result = save_to_vector_db(
    chunks,
    api_key="your-api-key-here"
)
```

---

### `generate_vectorization_report(validation_result, vectorization_result, model_name, db_type, output_dir)`

Генерирует отчёт по этапам 7–8.

**Параметры:**

- `validation_result` (Dict[str, Any]): Результаты валидации данных.
- `vectorization_result` (Dict[str, Any]): Результаты векторизации.
- `model_name` (str): Название модели эмбеддингов.
- `db_type` (str): Тип векторной БД.
- `output_dir` (str, optional): Директория для сохранения отчёта. По умолчанию `"output_module_4"`.

**Возвращает:**

- `str`: Путь к созданному файлу отчёта.

**Формат отчёта (Markdown):**

```markdown
# Отчёт по векторизации и векторной БД

**Дата генерации:** 2026-02-18 12:00:00

## Этап 7: Проверка качества данных

**Статистика:**
| Параметр | Значение |
|----------|----------|
| Всего чанков | 48 |
| Пустых чанков | 0 |
| Всего символов | 23040 |
| Средняя длина (символы) | 480.00 |
| Минимальная длина (символы) | 50 |
| Максимальная длина (символы) | 1500 |

**Статус валидации:** ✅ Данные прошли валидацию

## Этап 8: Векторизация и векторная БД

**Параметры:**
- **Модель:** text-embedding-3-small
- **Тип БД:** faiss
- **Векторов:** 48
- **Размерность:** 1536
- **Путь к индексу:** `output/vector_db/index.faiss`
- **Путь к датасету:** `output/vector_db/dataset.json`

**Статус векторизации:** ✅ Векторизация успешно завершена

---
**Итоговый статус:** ✅ Все этапы успешно завершены
```

**Пример использования:**

```python
from src.vectorizer import generate_vectorization_report

report_path = generate_vectorization_report(
    validation_result,
    vectorization_result,
    model_name="text-embedding-3-small",
    db_type="faiss"
)

print(f"Отчёт сохранён: {report_path}")
```

---

### `process_vectorization(final_dataset, output_dir, model_name, db_type, api_key, api_base)`

Полный цикл векторизации и сохранения в БД.

**Параметры:**

- `final_dataset` (List[Dict[str, Any]]): Список чанков с текстом и метаданными.
- `output_dir` (str, optional): Директория для сохранения результатов. По умолчанию `"output"`.
- `model_name` (str, optional): Название модели эмбеддингов. По умолчанию `"text-embedding-3-small"`.
- `db_type` (str, optional): Тип векторной БД. По умолчанию `"faiss"`.
- `api_key` (str, optional): API ключ OpenAI.
- `api_base` (str, optional): Базовый URL API. По умолчанию `"https://openai.api.proxyapi.ru/v1"`.

**Возвращает:**

- `Dict[str, Any]`: Словарь с результатами обработки:
  - `validation`: Результаты валидации
  - `vectorization`: Результаты векторизации
  - `report_path`: Путь к отчёту

**Пример использования:**

```python
from src.vectorizer import process_vectorization

result = process_vectorization(
    chunks,
    output_dir="output",
    model_name="text-embedding-3-small",
    db_type="faiss",
    api_base="https://openai.api.proxyapi.ru/v1"
)

print(f"Валидация: {result['validation']['stats']['total_chunks']} чанков")
print(f"Векторизация: {result['vectorization']['total_vectors']} векторов")
print(f"Отчёт: {result['report_path']}")
```

---

## Интеграция с process_pdf()

Модуль 4 интегрирован в функцию `process_pdf()` из `src/preprocessor.py`.

**Пример использования:**

```python
from src.preprocessor import process_pdf

result = process_pdf(
    pdf_path="document.pdf",
    output_dir="./output/",
    ocr_enabled=False,
    enable_chunking=True,          # Этапы 5-6
    max_chunk_size=500,
    overlap=50,
    enable_vectorization=True,     # Этапы 7-8
    embedding_model="text-embedding-3-small",
    vector_db_type="faiss",
    api_base="https://openai.api.proxyapi.ru/v1"
)

# Результаты векторизации
vectorization = result.get("vectorization", {})
print(f"Отчёт: {vectorization.get('report_path')}")
```

---

## Структура выходных данных

### dataset.json

```json
[
  {
    "text": "Текст чанка...",
    "type": "paragraph",
    "context": {},
    "metadata": {
      "source": "document.pdf",
      "page_number": 1,
      "chunk_id": "chunk_000",
      "timestamp": "2026-02-18T12:00:00",
      "chunk_type": "paragraph",
      "char_count": 480,
      "word_count": 80
    }
  },
  ...
]
```

### metadata.json

```json
{
  "model_name": "text-embedding-3-small",
  "embedding_dim": 1536,
  "total_vectors": 48,
  "db_type": "faiss",
  "created_at": "2026-02-18T12:00:00",
  "index_path": "output/vector_db/index.faiss",
  "dataset_path": "output/vector_db/dataset.json"
}
```

---

## Использование индекса FAISS

**Загрузка индекса:**

```python
import faiss
import numpy as np
import json

# Загрузка индекса
index = faiss.read_index("output/vector_db/index.faiss")

# Загрузка датасета
with open("output/vector_db/dataset.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

# Поиск похожих векторов
query_text = "Пример запроса"
query_embedding = generate_embedding(query_text)  # Ваша функция генерации
query_vector = np.array([query_embedding], dtype='float32')

# Поиск top-5 ближайших
k = 5
distances, indices = index.search(query_vector, k)

# Вывод результатов
for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
    chunk = dataset[idx]
    print(f"#{i+1} (расстояние: {dist:.4f})")
    print(f"Текст: {chunk['text'][:100]}...")
    print(f"Источник: {chunk['metadata']['source']}")
    print(f"Страница: {chunk['metadata']['page_number']}")
    print()
```

---

## Обработка ошибок

**Отсутствие библиотек:**

```python
try:
    from src.vectorizer import save_to_vector_db
    result = save_to_vector_db(chunks)
except ImportError as e:
    print(f"Ошибка: {e}")
    print("Установите зависимости: pip install openai faiss-cpu numpy")
```

**Ошибки API:**

```python
try:
    result = save_to_vector_db(chunks)
except Exception as e:
    print(f"Ошибка при векторизации: {e}")
    # Проверьте API ключ и подключение к интернету
```

---

## Конфигурация

**config.json:**

```json
{
  "embedding_model": "text-embedding-3-small",
  "vector_db_type": "faiss",
  "api_base": "https://openai.api.proxyapi.ru/v1"
}
```

---

## Логирование

Модуль использует стандартное логирование Python:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Логи модуля
# [2026-02-18 12:00:00] INFO: [Этап 7] Проверка качества данных
# [2026-02-18 12:00:01] INFO: [Этап 8] Начало векторизации (модель: text-embedding-3-small)
# [2026-02-18 12:00:05] INFO: [Этап 8] Сгенерировано 48 эмбеддингов размерности 1536
```

---

## Критерии приёмки

- ✅ Векторная БД создана и содержит корректные векторы
- ✅ `dataset.json` соответствует схеме
- ✅ Отчёт включает параметры векторизации

---

## Контакты

**Автор:** Line_GV  
**Telegram:** [@Line_GV](https://t.me/Line_GV)
