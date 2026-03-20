# Руководство пользователя "Соковыжималка" (Squeezer)

**Версия:** 3.3.0  
**Автор:** [Line_GV](https://t.me/Line_GV)

> **📋 История изменений:** см. [CHANGELOG.md](CHANGELOG.md)

## Введение

"Соковыжималка" — это система для обработки PDF-документов и подготовки данных для использования в RAG-системах. Система выполняет 8 этапов обработки:

1. Извлечение текста из PDF
2. Очистка данных
3. Нормализация данных
4. Структурирование текста
5. Гибридный чанкинг
6. Добавление метаданных
7. Проверка качества данных
8. Векторизация и сохранение в векторную БД

## Поддержка LLM моделей

Система поддерживает работу с LLM моделями через proxyAPI для обогащения метаданных чанков.

### OpenAI модели (через OpenAI SDK)

- **gpt-4o-mini** - ⚡ Быстрая и дешёвая (рекомендуется по умолчанию)
- **gpt-4o** - ⭐ Лучшее качество OpenAI

### Claude модели (через Anthropic SDK)

- **claude-sonnet-4-6** - 🏆 Лучший баланс, 1M контекст (рекомендуется для больших документов)
- **claude-haiku-4-5** - 💨 Быстрый Claude
- **claude-opus-4-6** - 👑 Максимальное качество

### Выбор модели в GUI

В графическом интерфейсе доступен удобный селектор моделей с пояснениями:

```
Модель LLM: [GPT-4o Mini - Для обычной обработки ▼]
            ⚡ Быстрая и дешёвая
```

### Рекомендации по выбору модели

| Сценарий | Модель | Причина |
|----------|--------|---------|
| **Обычная обработка** | gpt-4o-mini | Быстрая, дешёвая |
| **Большие документы** | claude-sonnet-4-6 | 1M токенов контекста |
| **Максимальное качество** | claude-opus-4-6 | Лучшее качество |

> 📖 Подробнее см. [PROXYAPI_GUIDE.md](docs/guides/PROXYAPI_GUIDE.md)

## Установка

### Требования

- Python 3.8+
- pip (менеджер пакетов Python)

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка переменных окружения

Для работы Модуля 4 (векторизация) требуется настройка API ключа OpenAI.

1. Скопируйте шаблон `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Откройте файл `.env` и заполните свои значения:
   ```env
   # API ключ OpenAI (обязательно для векторизации)
   OPENAI_API_KEY=your-api-key-here

   # Базовый URL API (опционально, для прокси)
   OPENAI_API_BASE=https://openai.api.proxyapi.ru/v1
   ```

**⚠️ Важно:** Файл `.env` не должен коммититься в репозиторий.

## Быстрый старт

### Через графический интерфейс (рекомендуется)

1. Запустите приложение:
   ```bash
   python gui_app.py
   ```

2. Нажмите кнопку "Загрузить PDF" и выберите файл

3. Нажмите кнопку "Обработать"

4. Дождитесь завершения обработки

5. Посмотрите результаты в диалоговом окне

### Через командную строку

```bash
python squeezer.py --input document.pdf --output output_module_2/
```

## Использование

### Графический интерфейс (GUI)

#### Загрузка файла

1. Запустите приложение: `python gui_app.py`
2. Нажмите кнопку "Загрузить PDF"
3. Выберите PDF-файл через диалоговое окно

**Ограничения:**
- Максимальный размер файла: 50 МБ
- Поддерживаемые форматы: PDF

#### Обработка файла

1. После загрузки файла нажмите кнопку "Обработать"
2. Дождитесь завершения обработки (индикатор прогресса)
3. Результаты будут отображены в диалоговом окне

#### Результаты обработки

**Модуль 2 (этапы 1-4):**
- Отчёт: `output_module_2/report.txt`
- Демонстрация: `output_module_2/transformation_demo.txt`

**Модуль 3 (этапы 5-6):**
- Отчёт по чанкингу: `output_module_3/chunking_report.txt`
- Демонстрация: `output_module_3/content_demonstrator.txt`

**Модуль 4 (этапы 7-8):**
- Отчёт по векторизации: `output_module_4/vectorization_report.txt`
- Векторная БД: `output/vector_db/index.faiss`
- Датасет: `output/vector_db/dataset.json`
- Метаданные: `output/vector_db/metadata.json`

### Командная строка (CLI)

#### Базовая обработка

```bash
python squeezer.py --input document.pdf --output output_module_2/
```

#### С чанкингом

```bash
python squeezer.py --input document.pdf --output output_module_2/ --enable-chunking --chunk-size 500 --overlap 50
```

#### Параметры

- `--input` (обязательный): Путь к PDF-файлу или директории
- `--output` (обязательный): Путь к выходной директории
- `--config` (опциональный): Путь к конфигурационному файлу
- `--enable-chunking` (опциональный): Включить этапы 5-6 (чанкинг)
- `--chunk-size` (опциональный): Максимальный размер чанка (по умолчанию: 500)
- `--overlap` (опциональный): Перекрытие между чанками (по умолчанию: 50)
- `--enable-vectorization` (опциональный): Включить этапы 7-8 (векторизация)
- `--embedding-model` (опциональный): Модель эмбеддингов (по умолчанию: text-embedding-3-small)
- `--api-key` (опциональный): API ключ OpenAI (если не задан в .env)

### Использование как библиотеки

#### Базовая обработка (этапы 1-4)

```python
from src.preprocessor import process_pdf

result = process_pdf(
    pdf_path="document.pdf",
    output_dir="output_module_2/",
    ocr_enabled=True,
    ocr_lang="rus+eng"
)

# Доступ к результатам
for page in result["pages"]:
    print(f"Страница {page['page_number']}")
    print(f"Заголовки: {page['structure']['headings']}")
    print(f"Абзацев: {len(page['structure']['paragraphs'])}")
```

#### С чанкингом (этапы 1-6)

```python
from src.preprocessor import process_pdf

result = process_pdf(
    pdf_path="document.pdf",
    output_dir="output_module_2/",
    enable_chunking=True,
    max_chunk_size=500,
    overlap=50,
    generate_demo=True
)

# Доступ к чанкам
for chunk in result["chunks"]:
    print(f"{chunk['metadata']['chunk_id']}: {chunk['text'][:50]}...")
    print(f"Тип: {chunk['metadata']['chunk_type']}")
    print(f"Символов: {chunk['metadata']['char_count']}")

# Доступ к отчётам
print(f"Отчёт по чанкингу: {result['chunking_report_path']}")
print(f"Демонстрация: {result['chunking_demo_path']}")
```

#### С векторизацией (этапы 1-8)

```python
from src.preprocessor import process_pdf
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

result = process_pdf(
    pdf_path="document.pdf",
    output_dir="output/",
    enable_chunking=True,          # Включить этапы 5-6
    max_chunk_size=500,
    overlap=50,
    enable_vectorization=True,     # Включить этапы 7-8
    embedding_model="text-embedding-3-small",
    vector_db_type="faiss"
)

# Доступ к результатам векторизации
vectorization = result.get("vectorization", {})
print(f"Валидация: {vectorization['validation']['stats']['total_chunks']} чанков")
print(f"Векторизация: {vectorization['vectorization']['total_vectors']} векторов")
print(f"Размерность: {vectorization['vectorization']['embedding_dim']}")
print(f"Отчёт: {vectorization['report_path']}")
```

#### Прямое использование модуля векторизации

```python
from src.vectorizer import process_vectorization
from dotenv import load_dotenv

load_dotenv()

result = process_vectorization(
    chunks,
    output_dir="output",
    model_name="text-embedding-3-small",
    db_type="faiss"
)

# Загрузка индекса для поиска
import faiss
import json

index = faiss.read_index("output/vector_db/index.faiss")
with open("output/vector_db/dataset.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

# Поиск похожих векторов
import numpy as np
query_vector = np.array([query_embedding], dtype='float32')
distances, indices = index.search(query_vector, k=5)

for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
    chunk = dataset[idx]
    print(f"#{i+1} (расстояние: {dist:.4f})")
    print(f"Текст: {chunk['text'][:100]}...")
```

## Этапы обработки

### Этап 1: Извлечение текста

- Извлекает текст из PDF-файлов
- Поддерживает текстовые и сканированные PDF (OCR)
- Сохраняет постраничную структуру

### Этап 2: Очистка данных

- Удаляет HTML-теги
- Удаляет навигационные элементы
- Нормализует пробелы
- Удаляет управляющие символы

### Этап 3: Нормализация данных

- Приводит к единому регистру
- Расширяет сокращения (т.е. → то есть)
- Стандартизирует даты в ISO формат

### Этап 4: Структурирование текста

- Распознаёт заголовки
- Выделяет абзацы
- Распознаёт списки (маркированные и нумерованные)
- Выделяет FAQ-блоки

### Этап 5: Гибридный чанкинг

- Семантическое разбиение на блоки (заголовки, абзацы, списки)
- Фиксированное разбиение с перекрытием для больших блоков
- Настраиваемый размер чанка и перекрытие

### Этап 6: Добавление метаданных

Каждый чанк получает метаданные:
- `source`: путь к PDF-файлу
- `page_number`: номер страницы
- `chunk_id`: уникальный идентификатор
- `timestamp`: время создания
- `chunk_type`: тип чанка
- `char_count`: количество символов
- `word_count`: количество слов

### Этап 7: Проверка качества данных

- Подсчёт пустых чанков
- Вычисление средней длины чанков
- Статистика по данным (мин./макс. длина)
- Проверка корректности данных перед векторизацией

### Этап 8: Векторизация и сохранение в БД

- Генерация эмбеддингов через OpenAI API (модель `text-embedding-3-small`)
- Поддержка прокси API (`https://openai.api.proxyapi.ru/v1`)
- Создание индекса FAISS (L2-метрика)
- Сохранение векторной БД в `output/vector_db/index.faiss`
- Сохранение датасета в `output/vector_db/dataset.json`
- Сохранение метаданных в `output/vector_db/metadata.json`

## Выходные файлы

### output_module_2/

- **report.txt**: Отчёт по обработке (этапы 1-4)
  - Статистика по каждому этапу
  - Количество заголовков, абзацев, списков

- **transformation_demo.txt**: Демонстрация трансформации текста
  - Примеры текста на каждом этапе

### output_module_3/

- **chunking_report.txt**: Отчёт по чанкингу (этапы 5-6)
  - Параметры чанкинга
  - Статистика по чанкам
  - Распределение по типам

- **content_demonstrator.txt**: Демонстрация результатов Модуля 3
  - Исходный структурированный текст
  - Результаты чанкинга с примерами
  - Примеры полных метаданных

### output_module_4/

- **vectorization_report.txt**: Отчёт по векторизации (этапы 7-8)
  - Проверка качества данных (этап 7)
  - Параметры векторизации (модель, тип БД, количество векторов)
  - Статистика по данным
  - Итоговый статус обработки

### output/vector_db/

- **index.faiss**: Индекс FAISS с эмбеддингами
  - Векторный индекс для быстрого поиска
  - L2-метрика расстояния
  - Размерность: 1536 (для `text-embedding-3-small`)

- **dataset.json**: Полный датасет в формате JSON
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
    }
  ]
  ```

- **metadata.json**: Метаданные индекса
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

## Конфигурация

### config.json

Основные параметры в `config.json`:

```json
{
  "version": "3.3.0",
  "author": "Line_GV",
  "author_url": "https://t.me/Line_GV",
  "release_date": "2026-03-20",
  "input_dir": "./pdfs/",
  "output_dir": "./output/",
  "chunk_size": 500,
  "overlap": 50,
  "embedding_model": "text-embedding-3-small",
  "llm_model": "gpt-4o-mini",
  "vector_db_type": "faiss",
  "api_base": "https://api.proxyapi.ru/openai/v1",
  "ocr_enabled": true,
  "log_level": "INFO"
}
```

### Переменные окружения (.env)

Файл `.env` используется для хранения чувствительных данных:

```env
# API ключ OpenAI (обязательно для векторизации)
OPENAI_API_KEY=your-api-key-here

# Базовый URL API (опционально, для прокси)
OPENAI_API_BASE=https://openai.api.proxyapi.ru/v1
```

## Локализация

Поддерживаются два языка:
- Русский ('ru')
- Английский ('en')

Для смены языка в GUI используйте параметр `language` при инициализации.

## Логирование

Логи записываются в:
- `logs/gui_app.log` (для GUI)
- `logs/squeezer.log` (для CLI)

Формат логов:
```
[ГГГГ-ММ-ДД ЧЧ:ММ:СС] УРОВЕНЬ: Сообщение
```

## Бэкап и восстановление

Система включает инструменты для создания бэкапов и восстановления проекта.

### Создание бэкапа

Создаёт полную копию системы в папку `backups/`:

```bash
python utils/create_backup.py
```

**Что копируется:**
- Все исходные файлы проекта (`src/`, `ui/`, и т.д.)
- Конфигурационные файлы
- Документация

**Что НЕ копируется:**
- Временные файлы (`__pycache__`, `*.pyc`)
- Логи (`logs/`, `*.log`)
- Виртуальное окружение (`venv/`, `.env`)
- Выходные данные (`output/`, `rag_bases/`)
- PDF файлы (`pdfs/`)
- Git метаданные (`.git/`)

### Восстановление из бэкапа

Восстанавливает систему из выбранного бэкапа:

```bash
python utils/restore_backup.py
```

## Устранение неполадок

### Проблема: Ошибка при импорте модулей

**Решение:**
```bash
pip install -r requirements.txt
```

### Проблема: Текст не читается (крякозябры)

**Решение:**
- Убедитесь, что файл сохранён в кодировке UTF-8
- Проверьте настройки логирования (кодировка UTF-8)

### Проблема: Чанкинг не работает

**Решение:**
- Убедитесь, что параметр `enable_chunking=True`
- Проверьте наличие модуля `src/chunker.py`

### Проблема: Векторизация не работает

**Решение:**
- Убедитесь, что параметр `enable_vectorization=True`
- Проверьте наличие файла `.env` с API ключом
- Убедитесь, что установлен `python-dotenv`: `pip install python-dotenv`
- Проверьте наличие модуля `src/vectorizer.py`

### Проблема: Ошибка API ключа

**Решение:**
- Проверьте, что API ключ указан в файле `.env`
- Убедитесь, что API ключ корректный и активен
- Проверьте подключение к интернету

### Проблема: GUI не запускается

**Решение:**
- Убедитесь, что установлен Tkinter
- Для Linux: `sudo apt-get install python3-tk`

## Примеры

### Пример 1: Обработка одного файла

```bash
python squeezer.py --input document.pdf --output output/
```

### Пример 2: Обработка с чанкингом

```bash
python squeezer.py --input document.pdf --output output/ --enable-chunking --chunk-size 500 --overlap 50
```

### Пример 3: Обработка с векторизацией

```bash
python squeezer.py --input document.pdf --output output/ --enable-chunking --enable-vectorization
```

### Пример 4: Использование как библиотеки с векторизацией

```python
from src.preprocessor import process_pdf
from dotenv import load_dotenv

load_dotenv()

result = process_pdf(
    pdf_path="document.pdf",
    output_dir="output/",
    enable_chunking=True,
    enable_vectorization=True
)

# Получить чанки
chunks = result["chunks"]

# Получить результаты векторизации
vectorization = result["vectorization"]
```

## Advanced RAG (v2.6.0 - v2.8.0)

Система включает полный набор Advanced RAG техник:

### Re-ranking (v2.6.0)
Переранжирование документов для повышения точности (+15-30%).

```python
from src.reranker import rerank_results

results = rerank_results(query, documents, llm_model="gpt-4o-mini")
```

### HyDE Search (v2.6.0)
Поиск по гипотетическому ответу для улучшения recall (+10-20%).

```python
from src.hyde_search import hyde_search

results = hyde_search(query, index, dataset, llm_model="gpt-4o-mini")
```

### Fusion Retrieval (v2.6.0)
Объединение векторного, ключевого и LLM поиска (+20-40%).

```python
from src.retriever import fusion_search

results = fusion_search(query, index, dataset, llm_model="gpt-4o-mini")
```

### Query Rewriting (v2.8.0)
Перезапись запросов для улучшения поиска.

```python
from src.query_rewriter import rewrite_query

result = rewrite_query("как создать бота", llm_model="gpt-4o-mini")
# Результат: "как создать telegram бота с помощью python"
```

### Answer с цитатами (v2.8.0)
Генерация ответов с автоматическими ссылками на источники.

```python
from src.answer_generator import generate_answer_with_citations

result = generate_answer_with_citations(query, documents)
print(result['answer'])  # Ответ с цитатами [source: chunk_001, p.1]
```

### Извлечение таблиц (v2.8.0)
Извлечение и интерпретация таблиц из PDF.

```python
from src.table_extractor import extract_tables_from_pdf

tables = extract_tables_from_pdf("document.pdf", use_llm=True)
# Результат: JSON с описаниями и данными таблиц
```

### Self-RAG (v2.8.0)
Самокорректирующийся RAG с оценкой качества.

```python
from src.self_rag import self_rag_query

result = self_rag_query(query, vector_store, top_k=5)
print(result['final_confidence'])  # Оценка уверенности
print(result['answer_evaluation']['quality'])  # quality: excellent/good/partial
```

### RAG Engine (v3.1.0) - РЕКОМЕНДУЕТСЯ
Интегрированный RAG-движок с единым интерфейсом.

```python
from src.rag_engine import ask_rag, create_rag_engine

# Быстрый вызов
result = ask_rag("Ваш вопрос", "vector_db/", llm_model="gpt-4o-mini")
print(result['answer'])
print(result['sources'])

# Или создайте движок с настройками
rag = create_rag_engine(
    db_path="vector_db/",
    use_reranker=True,
    use_hyde=False,
    use_cache=True
)
answer = rag.ask("Вопрос?")
```

### Метрики и мониторинг (v3.1.0)
Сбор метрик с поддержкой Prometheus.

```python
from src.metrics import get_metrics, Timer
from src.rag_engine import ask_rag

# Автоматический сбор метрик
result = ask_rag("Question?", "vector_db/")

# Получение статистики
metrics = get_metrics()
print(metrics.get_stats())

# Экспорт в Prometheus
print(metrics.export_prometheus())
```

### Async/Parallel Processing (v3.1.0)
Параллельная обработка для ускорения.

```python
from src.async_processor import ParallelProcessor, ParallelConfig

processor = ParallelProcessor(ParallelConfig(max_workers=4))
results = processor.map_parallel(func, items)
```

### Интеграционный пайплайн (v2.8.0)
Объединяет все Advanced RAG функции.

```python
from src.advanced_rag_pipeline import create_advanced_rag_pipeline

pipeline = create_advanced_rag_pipeline(config, vector_store)

result = pipeline.query(
    query="ваш вопрос",
    use_query_rewrite=True,
    use_self_rag=True,
    use_citations=True,
    top_k=5
)
```

### Кэширование эмбеддингов (v2.8.0)
Экономия API вызовов при повторной обработке.

```python
from src.embedding_cache import get_embedding_with_cache

embedding = get_embedding_with_cache(text, model, client)
# Автоматически проверяет кэш перед запросом к API
```

## Тестирование

### Запуск тестов

```bash
# Установка зависимостей для тестирования
pip install pytest pytest-cov

# Запуск всех тестов
python -m pytest tests/ -v

# Запуск с покрытием кода
python -m pytest tests/ -v --cov=src --cov-report=html

# Запуск конкретного теста
python -m pytest tests/test_preprocessor.py -v
```

### Структура тестов

```
tests/
├── conftest.py           # Общие фикстуры pytest
├── test_preprocessor.py  # Тесты модуля предобработки
├── test_chunker.py       # Тесты модуля чанкинга
├── test_vectorizer.py    # Тесты модуля векторизации
├── test_llm_chunker.py   # Тесты LLM-усиленного чанкинга
├── test_rag_engine.py    # Тесты RAG-движка
└── integration/          # Интеграционные тесты
```

### Code Style

Проект использует следующие инструменты для контроля качества кода:

```bash
# Форматирование кода
pip install black isort
black src/ tests/
isort src/ tests/

# Линтинг
pip install flake8
flake8 src/ --max-line-length=100

# Проверка типов
pip install mypy
mypy src/ --ignore-missing-imports

# Pre-commit hooks (опционально)
pip install pre-commit
pre-commit install
```

## Поддержка

**Автор:** Line_GV  
**Telegram:** [@Line_GV](https://t.me/Line_GV)

## Ссылки

- [CHANGELOG.md](CHANGELOG.md) — История изменений
- [ROADMAP.md](ROADMAP.md) — Дорожная карта
- [PROXYAPI_GUIDE.md](docs/guides/PROXYAPI_GUIDE.md) — Работа с LLM моделями через proxyAPI
- [GUI_LLM_SELECTOR.md](docs/guides/GUI_LLM_SELECTOR.md) — Документация GUI селектора моделей

## Лицензия

Проект разработан для образовательных целей в рамках обучения Prompt Engineering 3.0 от Zerocoder.
