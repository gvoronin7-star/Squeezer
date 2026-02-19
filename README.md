# Руководство пользователя "Соковыжималка" (Squeezer)

**Версия:** 2.4.0
**Автор:** [Line_GV](https://t.me/Line_GV)

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
  "version": "2.2.0",
  "author": "Line_GV",
  "author_url": "https://t.me/Line_GV",
  "release_date": "2026-02-18",
  "input_dir": "./pdfs/",
  "output_dir": "./output_module_2/",
  "chunk_size": 500,
  "overlap": 50,
  "embedding_model": "text-embedding-3-small",
  "vector_db_type": "faiss",
  "api_base": "https://openai.api.proxyapi.ru/v1",
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
python create_backup.py
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
python restore_backup.py
```

**Действия:**
1. Показывает список доступных бэкапов
2. Позволяет выбрать нужный бэкап
3. Предлагает выбрать режим:
   - **Обычный** - копирует файлы в проект
   - **Проверка** - только показывает что будет сделано

### Рекомендации по бэкапу

**Перед обновлением версии:**
```bash
# 1. Создайте бэкап
python create_backup.py

# 2. Установите новую версию
pip install --upgrade squeezer-rag

# 3. Если что-то пошло не так, восстановитесь
python restore_backup.py
```

**Перед критическими изменениями:**
```bash
# Создайте бэкап перед изменением кода
python create_backup.py

# Внесите изменения в код
# ...

# Если нужно откатиться
python restore_backup.py
```

Подробнее см. [BACKUP_GUIDE.md](BACKUP_GUIDE.md)

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

## Поддержка

**Автор:** Line_GV  
**Telegram:** [@Line_GV](https://t.me/Line_GV)

## Лицензия

Проект разработан для образовательных целей в рамках обучения Prompt Engineering 3.0 от Zerocoder.
