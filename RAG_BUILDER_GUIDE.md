# Руководство по созданию RAG-баз данных

**Версия:** 2.3.0  
**Автор:** [Line_GV](https://t.me/Line_GV)

## Обзор

RAG Builder — это инструмент для создания полноценных RAG-баз данных из PDF-файлов. Система автоматически:

1. Обрабатывает несколько PDF-файлов
2. Создаёт чанки и метаданные
3. Генерирует эмбеддинги через OpenAI API
4. Создаёт векторную БД (FAISS)
5. Формирует инструкцию по подключению
6. Сохраняет всё в отдельную папку с названием базы

---

## Быстрый старт

### Шаг 1: Запуск приложения

```bash
python rag_builder.py
```

### Шаг 2: Добавление PDF-файлов

1. Нажмите кнопку **"Добавить PDF"**
2. Выберите один или несколько PDF-файлов
3. Файлы появятся в списке

### Шаг 3: Указание названия базы

- В поле **"Название RAG-базы"** введите название
- Если поле пустое — название сгенерируется автоматически на основе файлов

### Шаг 4: Создание RAG-базы

1. Нажмите кнопку **"Создать RAG-базу"**
2. Дождитесь завершения обработки
3. После завершения появится сообщение с расположением базы

---

## Структура RAG-базы

После создания в папке `rag_bases/` появится папка с вашей базой:

```
MyKnowledgeBase/
├── README_RAG.md          # Полная инструкция
├── example_connection.py  # Пример кода на Python
├── index.faiss           # Индекс FAISS
├── dataset.json          # Датасет с чанками
├── metadata.json         # Метаданные
└── source_documents/     # Исходные PDF
    ├── doc1.pdf
    ├── doc2.pdf
    └── ...
```

---

## Использование RAG-базы

### Способ 1: Пример из example_connection.py

Откройте файл `example_connection.py` в созданной папке и запустите:

```bash
python example_connection.py
```

### Способ 2: Собственный код

```python
import faiss
import numpy as np
import json
from openai import OpenAI

# 1. Загрузка индекса
index = faiss.read_index("index.faiss")

# 2. Загрузка датасета
with open("dataset.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

# 3. Настройка клиента OpenAI
client = OpenAI(
    api_key="your-api-key",
    base_url="https://openai.api.proxyapi.ru/v1"
)

# 4. Функция поиска
def search(query: str, k: int = 5):
    # Генерация эмбеддинга
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_embedding = response.data[0].embedding

    # Поиск
    query_vector = np.array([query_embedding], dtype='float32')
    distances, indices = index.search(query_vector, k)

    # Результаты
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        chunk = dataset[idx]
        results.append({
            "distance": float(dist),
            "text": chunk["text"],
            "source": chunk["metadata"]["source"],
            "page": chunk["metadata"]["page_number"]
        })
    return results

# 5. Использование
results = search("Ваш запрос", k=3)
for i, r in enumerate(results, 1):
    print(f"#{i} (расстояние: {r['distance']:.4f})")
    print(f"Текст: {r['text'][:100]}...")
    print()
```

---

## Интеграция с RAG-системами

### LangChain

```python
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings

# Настройка
embeddings = OpenAIEmbeddings(
    openai_api_key="your-api-key",
    openai_api_base="https://openai.api.proxyapi.ru/v1",
    model="text-embedding-3-small"
)

# Загрузка
vectorstore = FAISS.load_local("", embeddings, index_name="index")

# Поиск
results = vectorstore.similarity_search("Ваш запрос", k=5)
for doc in results:
    print(doc.page_content)
```

### LlamaIndex

```python
from llama_index import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores import FAISSVectorStore

# Загрузка документов
documents = SimpleDirectoryReader("source_documents").load_data()

# Создание индекса
index = VectorStoreIndex.from_documents(documents)

# Поиск
query_engine = index.as_query_engine()
response = query_engine.query("Ваш запрос")
print(response)
```

---

## Передача базы другим программам

### Вариант 1: Архивирование

```bash
# Windows
tar -czf MyKnowledgeBase.tar.gz MyKnowledgeBase/

# Linux/Mac
tar -czf MyKnowledgeBase.tar.gz MyKnowledgeBase/
```

### Вариант 2: Копирование файлов

Просто скопируйте папку с базой в нужное место.

### Вариант 3: Облачное хранилище

Загрузите папку в Google Drive, Dropbox или другое облачное хранилище.

---

## Требования

- Python 3.8+
- API ключ OpenAI (настроен в `.env`)
- Установленные зависимости:
  ```bash
  pip install -r requirements.txt
  ```

---

## Устранение неполадок

### Ошибка: "Выберите хотя бы один PDF-файл"

**Решение:** Добавьте хотя бы один PDF-файл через кнопку "Добавить PDF".

### Ошибка: "API ключ не установлен"

**Решение:** Заполните `OPENAI_API_KEY` в файле `.env`.

### Ошибка: "Не удалось создать чанки"

**Решение:** Убедитесь, что PDF-файлы содержат текст (не только изображения).

### Медленная обработка

**Причина:** Генерация эмбеддингов требует времени.

**Решение:**
- Обрабатывайте файлы небольшими пакетами
- Используйте более быструю модель (text-embedding-3-large)
- Проверьте подключение к интернету

---

## Примеры использования

### Пример 1: База знаний компании

1. Добавьте PDF-файлы с документацией
2. Назовите базу: "CompanyKnowledgeBase"
3. Создайте базу
4. Интегрируйте в корпоративный ассистент

### Пример 2: База научных статей

1. Добавьте PDF-файлы со статьями
2. Назовите базу: "SciencePapers2024"
3. Создайте базу
4. Используйте для поиска релевантных исследований

### Пример 3: База юридических документов

1. Добавьте PDF-файлы с законами и нормативами
2. Назовите базу: "LegalDocuments"
3. Создайте базу
4. Интегрируйте в юридического ассистента

---

## Контакты

**Автор:** Line_GV  
**Telegram:** [@Line_GV](https://t.me/Line_GV)

## Лицензия

Проект разработан для образовательных целей в рамках обучения Prompt Engineering 3.0 от Zerocoder.
