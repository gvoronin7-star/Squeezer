# API Модуля 5: Создание RAG-баз данных

**Версия:** 2.3.0  
**Дата:** 2026-02-18  
**Автор:** Line_GV

## Обзор

Модуль 5 предоставляет инструменты для создания полноценных RAG-баз данных из нескольких PDF-файлов с инструкциями по подключению и использованию.

### Основные компоненты

1. **`src/rag_instructions.py`** — Генерация инструкций для RAG-баз
2. **`src/ui/rag_builder_ui.py`** — Графический интерфейс для создания RAG-баз
3. **`rag_builder.py`** — Основное приложение для создания RAG-баз

---

## Генерация инструкций (src/rag_instructions.py)

### `generate_rag_readme(rag_base_name, metadata, source_files, output_dir)`

Генерирует README.md для RAG-базы данных.

**Параметры:**

- `rag_base_name` (str): Название RAG-базы
- `metadata` (Dict[str, Any]): Метаданные индекса
- `source_files` (List[str]): Список исходных PDF-файлов
- `output_dir` (Path): Директория RAG-базы

**Возвращает:**

- `str`: Путь к созданному файлу README.md

**Пример использования:**

```python
from src.rag_instructions import generate_rag_readme
from pathlib import Path

readme_path = generate_rag_readme(
    rag_base_name="MyKnowledgeBase",
    metadata={
        "model_name": "text-embedding-3-small",
        "embedding_dim": 1536,
        "total_vectors": 1234,
        "db_type": "faiss"
    },
    source_files=["doc1.pdf", "doc2.pdf"],
    output_dir=Path("rag_bases/MyKnowledgeBase")
)

print(f"README создан: {readme_path}")
```

---

### `generate_connection_example_python(rag_base_name, metadata, output_dir)`

Генерирует пример подключения на Python.

**Параметры:**

- `rag_base_name` (str): Название RAG-базы
- `metadata` (Dict[str, Any]): Метаданные индекса
- `output_dir` (Path): Директория RAG-базы

**Возвращает:**

- `str`: Путь к созданному файлу example_connection.py

**Пример использования:**

```python
from src.rag_instructions import generate_connection_example_python

example_path = generate_connection_example_python(
    rag_base_name="MyKnowledgeBase",
    metadata={
        "model_name": "text-embedding-3-small",
        "embedding_dim": 1536
    },
    output_dir=Path("rag_bases/MyKnowledgeBase")
)

print(f"Пример подключения создан: {example_path}")
```

---

### `generate_rag_package(rag_base_name, index_path, dataset_path, metadata_path, source_files, output_base_dir)`

Создаёт полный пакет RAG-базы данных.

**Параметры:**

- `rag_base_name` (str): Название RAG-базы
- `index_path` (Path): Путь к индексу FAISS
- `dataset_path` (Path): Путь к датасету JSON
- `metadata_path` (Path): Путь к метаданным
- `source_files` (List[Path]): Список исходных PDF-файлов
- `output_base_dir` (Path): Базовая директория для RAG-баз

**Возвращает:**

- `Dict[str, str]`: Словарь с путями к созданным файлам:
  - `rag_dir`: Путь к директории RAG-базы
  - `readme`: Путь к README.md
  - `example`: Путь к example_connection.py
  - `index`: Путь к index.faiss
  - `dataset`: Путь к dataset.json
  - `metadata`: Путь к metadata.json
  - `source_documents_dir`: Путь к папке с исходными документами

**Пример использования:**

```python
from src.rag_instructions import generate_rag_package
from pathlib import Path

rag_package = generate_rag_package(
    rag_base_name="MyKnowledgeBase",
    index_path=Path("output/vector_db/index.faiss"),
    dataset_path=Path("output/vector_db/dataset.json"),
    metadata_path=Path("output/vector_db/metadata.json"),
    source_files=[
        Path("pdfs/doc1.pdf"),
        Path("pdfs/doc2.pdf")
    ],
    output_base_dir=Path("rag_bases")
)

print(f"RAG-база создана: {rag_package['rag_dir']}")
print(f"README: {rag_package['readme']}")
print(f"Пример: {rag_package['example']}")
```

---

## Графический интерфейс (src/ui/rag_builder_ui.py)

### `RAGBuilderUI`

Класс для создания графического интерфейса RAG-строителя.

**Инициализация:**

```python
from src.ui.rag_builder_ui import RAGBuilderUI
import tkinter as tk

root = tk.Tk()
app = RAGBuilderUI(root, language='ru')
```

**Параметры:**

- `master` (tk.Tk): Родительское окно Tkinter
- `language` (str, optional): Язык интерфейса ('ru' или 'en'). По умолчанию 'ru'
- `on_rag_created` (Callable, optional): Callback при создании RAG-базы

**Методы:**

#### `_load_file(file_path)`

Загружает PDF-файл в список.

**Параметры:**

- `file_path` (Path): Путь к файлу

#### `_remove_button_click()`

Удаляет выбранные файлы из списка.

#### `_clear_button_click()`

Удаляет все файлы из списка.

#### `_get_rag_config()`

Возвращает конфигурацию для создания RAG-базы.

**Возвращает:**

- `Dict[str, Any]`: Конфигурация RAG-базы:
  - `rag_name`: Название базы
  - `files`: Список файлов
  - `stats`: Статистика

#### `complete_processing(rag_info)`

Завершает обработку и показывает результаты.

**Параметры:**

- `rag_info` (Dict[str, Any]): Информация о созданной RAG-базе

---

## Основное приложение (rag_builder.py)

### `RAGBuilderApp`

Класс основного приложения для создания RAG-баз.

**Инициализация:**

```python
from rag_builder import RAGBuilderApp
import tkinter as tk

root = tk.Tk()
app = RAGBuilderApp(root, language='ru')
app.run()
```

**Параметры:**

- `root` (tk.Tk): Корневое окно Tkinter
- `language` (str, optional): Язык интерфейса. По умолчанию 'ru'

**Методы:**

#### `_on_rag_create_start(config)`

Начинает процесс создания RAG-базы.

**Параметры:**

- `config` (Dict[str, Any]): Конфигурация RAG-базы

#### `run()`

Запускает приложение.

---

## Структура RAG-базы

После создания RAG-база имеет следующую структуру:

```
RAG_BASE_NAME/
├── README_RAG.md          # Инструкция по подключению и использованию
├── example_connection.py  # Пример кода на Python
├── index.faiss           # Индекс FAISS с эмбеддингами
├── dataset.json          # Датасет с чанками и метаданными
├── metadata.json         # Метаданные индекса
└── source_documents/     # Исходные PDF-файлы
    ├── doc1.pdf
    ├── doc2.pdf
    └── ...
```

---

## Использование

### Запуск приложения

```bash
python rag_builder.py
```

### Создание RAG-базы через код

```python
from rag_builder import RAGBuilderApp
import tkinter as tk

root = tk.Tk()
app = RAGBuilderApp(root, language='ru')
app.run()
```

---

## Конфигурация

### Параметры RAG-базы

- **rag_name**: Название базы (автоматически генерируется, если не указано)
- **files**: Список PDF-файлов для обработки
- **stats**: Статистика по файлам (количество, страницы, размер)

---

## Интеграция с другими системами

### Подключение к RAG-базе

```python
import faiss
import numpy as np
import json
from openai import OpenAI

# Загрузка индекса
index = faiss.read_index("index.faiss")

# Загрузка датасета
with open("dataset.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

# Настройка клиента
client = OpenAI(api_key="your-api-key", base_url="https://openai.api.proxyapi.ru/v1")

# Генерация эмбеддинга
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Ваш запрос"
)
query_embedding = response.data[0].embedding

# Поиск
query_vector = np.array([query_embedding], dtype='float32')
distances, indices = index.search(query_vector, k=5)

# Результаты
for dist, idx in zip(distances[0], indices[0]):
    chunk = dataset[idx]
    print(f"Текст: {chunk['text']}")
    print(f"Источник: {chunk['metadata']['source']}")
```

---

## Логирование

Логи записываются в `logs/rag_builder.log`.

Формат логов:
```
[ГГГГ-ММ-ДД ЧЧ:ММ:СС] УРОВЕНЬ: Сообщение
```

---

## Контакты

**Автор:** Line_GV  
**Telegram:** [@Line_GV](https://t.me/Line_GV)

---

## Лицензия

Проект разработан для образовательных целей в рамках обучения Prompt Engineering 3.0 от Zerocoder.
