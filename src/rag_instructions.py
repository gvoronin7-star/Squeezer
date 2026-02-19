"""
Модуль генерации инструкций для RAG-баз данных.

Создаёт документацию по подключению и использованию векторной базы данных.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def generate_rag_readme(
    rag_base_name: str,
    metadata: Dict[str, Any],
    source_files: List[str],
    output_dir: Path
) -> str:
    """
    Генерирует README.md для RAG-базы данных.

    Args:
        rag_base_name: Название RAG-базы.
        metadata: Метаданные индекса.
        source_files: Список исходных PDF-файлов.
        output_dir: Директория RAG-базы.

    Returns:
        Путь к созданному файлу README.md.
    """
    readme_path = output_dir / "README_RAG.md"

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"# RAG База данных: {rag_base_name}\n\n")
        f.write(f"**Дата создания:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # Обзор
        f.write("## Обзор\n\n")
        f.write(f"Эта RAG-база данных содержит векторизованные документы, подготовленные для использования ")
        f.write(f"в системах семантического поиска и генерации ответов на основе контекста.\n\n")

        f.write("**Параметры базы данных:**\n\n")
        f.write(f"- **Название:** {rag_base_name}\n")
        f.write(f"- **Модель эмбеддингов:** {metadata.get('model_name', 'N/A')}\n")
        f.write(f"- **Размерность:** {metadata.get('embedding_dim', 'N/A')}\n")
        f.write(f"- **Количество векторов:** {metadata.get('total_vectors', 0)}\n")
        f.write(f"- **Тип БД:** {metadata.get('db_type', 'faiss')}\n\n")

        # Структура файлов
        f.write("## Структура файлов\n\n")
        f.write("```\n")
        f.write(f"{rag_base_name}/\n")
        f.write("├── README_RAG.md          # Эта инструкция\n")
        f.write("├── index.faiss           # Индекс FAISS с эмбеддингами\n")
        f.write("├── dataset.json          # Датасет с чанками и метаданными\n")
        f.write("├── metadata.json         # Метаданные индекса\n")
        f.write("└── source_documents/     # Исходные PDF-файлы\n")
        for i, file in enumerate(source_files, 1):
            f.write(f"    ├── {Path(file).name}\n")
        f.write("```\n\n")

        # Описание файлов
        f.write("### Описание файлов\n\n")
        f.write("**index.faiss**\n\n")
        f.write("Индекс FAISS, содержащий векторные представления всех чанков документов. ")
        f.write("Используется для быстрого поиска ближайших векторов.\n\n")

        f.write("**dataset.json**\n\n")
        f.write("JSON-файл с полным набором чанков документов. Каждый чанк содержит:\n\n")
        f.write("```json\n")
        f.write("{\n")
        f.write('  "text": "Текст чанка...",\n')
        f.write('  "type": "paragraph",\n')
        f.write('  "context": {},\n')
        f.write('  "metadata": {\n')
        f.write('    "source": "document.pdf",\n')
        f.write('    "page_number": 1,\n')
        f.write('    "chunk_id": "chunk_000",\n')
        f.write('    "timestamp": "2026-02-18T12:00:00",\n')
        f.write('    "chunk_type": "paragraph",\n')
        f.write('    "char_count": 480,\n')
        f.write('    "word_count": 80\n')
        f.write('  }\n')
        f.write("}\n")
        f.write("```\n\n")

        f.write("**metadata.json**\n\n")
        f.write("Метаданные индекса, включая параметры модели и статистику.\n\n")

        f.write("**source_documents/**\n\n")
        f.write("Папка с исходными PDF-файлами, использованными для создания базы данных.\n\n")

        # Быстрый старт (Python)
        f.write("## Быстрый старт (Python)\n\n")

        f.write("### Установка зависимостей\n\n")
        f.write("```bash\n")
        f.write("pip install faiss-cpu numpy openai\n")
        f.write("```\n\n")

        f.write("### Пример кода\n\n")
        f.write("```python\n")
        f.write("import faiss\n")
        f.write("import numpy as np\n")
        f.write("import json\n")
        f.write("from openai import OpenAI\n\n")

        f.write("# 1. Загрузка индекса FAISS\n")
        f.write(f'index = faiss.read_index("index.faiss")\n')
        f.write('print(f"Загружено {index.ntotal} векторов размерности {index.d}")\n\n')

        f.write("# 2. Загрузка датасета\n")
        f.write(f'with open("dataset.json", "r", encoding="utf-8") as f:\n')
        f.write('    dataset = json.load(f)\n')
        f.write('print(f"Загружено {len(dataset)} чанков")\n\n')

        f.write("# 3. Настройка клиента OpenAI для генерации эмбеддингов\n")
        f.write('client = OpenAI(\n')
        f.write('    api_key="your-api-key-here",\n')
        f.write('    base_url="https://openai.api.proxyapi.ru/v1"\n')
        f.write(')\n\n')

        f.write("# 4. Функция генерации эмбеддинга для запроса\n")
        f.write("def generate_embedding(text: str) -> list:\n")
        f.write('    """Генерирует эмбеддинг для текста."""\n')
        f.write('    response = client.embeddings.create(\n')
        f.write(f'        model="{metadata.get("model_name", "text-embedding-3-small")}",\n')
        f.write('        input=text\n')
        f.write('    )\n')
        f.write('    return response.data[0].embedding\n\n')

        f.write("# 5. Поиск релевантных чанков\n")
        f.write("def search(query: str, k: int = 5) -> list:\n")
        f.write('    """Ищет топ-k релевантных чанков для запроса."""\n')
        f.write('    # Генерируем эмбеддинг запроса\n')
        f.write('    query_embedding = generate_embedding(query)\n')
        f.write('    query_vector = np.array([query_embedding], dtype="float32")\n\n')

        f.write('    # Ищем ближайшие векторы\n')
        f.write('    distances, indices = index.search(query_vector, k)\n\n')

        f.write('    # Формируем результаты\n')
        f.write('    results = []\n')
        f.write('    for dist, idx in zip(distances[0], indices[0]):\n')
        f.write('        chunk = dataset[idx]\n')
        f.write('        results.append({\n')
        f.write('            "distance": float(dist),\n')
        f.write('            "text": chunk["text"],\n')
        f.write('            "source": chunk["metadata"]["source"],\n')
        f.write('            "page": chunk["metadata"]["page_number"],\n')
        f.write('            "chunk_id": chunk["metadata"]["chunk_id"]\n')
        f.write('        })\n')
        f.write('    return results\n\n')

        f.write("# 6. Использование\n")
        f.write('if __name__ == "__main__":\n')
        f.write('    query = "Ваш запрос здесь"\n')
        f.write('    results = search(query, k=5)\n\n')

        f.write('    print(f"Запрос: {query}")\n')
        f.write('    print(f"Найдено: {len(results)} результатов\\n")\n\n')

        f.write('    for i, result in enumerate(results, 1):\n')
        f.write('        print(f"#{i} (расстояние: {result["distance"]:.4f})")\n')
        f.write('        print(f"Текст: {result["text"][:100]}...")\n')
        f.write('        print(f"Источник: {result["source"]}, страница {result["page"]}")\n')
        f.write('        print()\n')
        f.write("```\n\n")

        # Использование в RAG-системах
        f.write("## Использование в RAG-системах\n\n")

        f.write("### Основной принцип\n\n")
        f.write("1. **Пользователь задаёт вопрос**\n")
        f.write("2. **Генерируем эмбеддинг вопроса** через OpenAI API\n")
        f.write("3. **Ищем релевантные чанки** в индексе FAISS\n")
        f.write("4. **Формируем контекст** из найденных чанков\n")
        f.write("5. **Генерируем ответ** LLM на основе вопроса и контекста\n\n")

        f.write("### Пример интеграции с LangChain\n\n")
        f.write("```python\n")
        f.write("from langchain.vectorstores import FAISS\n")
        f.write("from langchain.embeddings import OpenAIEmbeddings\n")
        f.write("from langchain.docstore.document import Document\n\n")

        f.write("# Настройка эмбеддингов\n")
        f.write('embeddings = OpenAIEmbeddings(\n')
        f.write('    openai_api_key="your-api-key-here",\n')
        f.write('    openai_api_base="https://openai.api.proxyapi.ru/v1",\n')
        f.write(f'    model="{metadata.get("model_name", "text-embedding-3-small")}"\n')
        f.write(')\n\n')

        f.write("# Загрузка индекса\n")
        f.write(f'vectorstore = FAISS.load_local("", embeddings, index_name="index")\n\n')

        f.write("# Поиск\n")
        f.write('results = vectorstore.similarity_search("Ваш запрос", k=5)\n')
        f.write("for doc in results:\n")
        f.write("    print(doc.page_content)\n")
        f.write("```\n\n")

        # Метрики и статистика
        f.write("## Статистика базы данных\n\n")
        f.write("| Параметр | Значение |\n")
        f.write("|----------|----------|\n")
        f.write(f"| Название | {rag_base_name} |\n")
        f.write(f"| Модель эмбеддингов | {metadata.get('model_name', 'N/A')} |\n")
        f.write(f"| Размерность | {metadata.get('embedding_dim', 0)} |\n")
        f.write(f"| Количество векторов | {metadata.get('total_vectors', 0)} |\n")
        f.write(f"| Тип индекса | {metadata.get('db_type', 'faiss')} |\n")
        f.write(f"| Количество исходных файлов | {len(source_files)} |\n\n")

        # Исходные файлы
        if source_files:
            f.write("## Исходные файлы\n\n")
            f.write("База данных создана на основе следующих PDF-файлов:\n\n")
            for i, file in enumerate(source_files, 1):
                f.write(f"{i}. `{Path(file).name}`\n")
            f.write("\n")

        # FAQ
        f.write("## FAQ\n\n")

        f.write("**Q: Как изменить модель эмбеддингов?**\n\n")
        f.write("A: Измените параметр `model` при вызове `client.embeddings.create()` ")
        f.write("на другую модель OpenAI (например, `text-embedding-3-large`).\n\n")

        f.write("**Q: Как добавить новые документы в базу?**\n\n")
        f.write("A: Обработайте новые документы через систему \"Соковыжималка\", ")
        f.write("затем добавьте полученные эмбеддинги в существующий индекс FAISS с помощью `index.add()`.\n\n")

        f.write("**Q: Как использовать базу без интернета?**\n\n")
        f.write("A: Генерация эмбеддингов требует подключения к OpenAI API. ")
        f.write("Поиск по индексу FAISS может работать локально.\n\n")

        f.write("**Q: Какой размерность должен быть эмбеддинг запроса?**\n\n")
        f.write(f"A: Размерность эмбеддинга запроса должна совпадать с размерностью индекса: {metadata.get('embedding_dim', 0)}.\n\n")

        # Контакты
        f.write("---\n\n")
        f.write("## Контакты\n\n")
        f.write("**Автор системы:** Line_GV  \n")
        f.write("**Telegram:** [@Line_GV](https://t.me/Line_GV)\n\n")

        f.write("База данных создана с помощью системы \"Соковыжималка\" (Squeezer) v2.2.0\n\n")

    return str(readme_path)


def generate_connection_example_python(
    rag_base_name: str,
    metadata: Dict[str, Any],
    output_dir: Path
) -> str:
    """
    Генерирует пример подключения на Python.

    Args:
        rag_base_name: Название RAG-базы.
        metadata: Метаданные индекса.
        output_dir: Директория RAG-базы.

    Returns:
        Путь к созданному файлу.
    """
    example_path = output_dir / "example_connection.py"

    with open(example_path, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write(f'Пример подключения к RAG-базе данных: {rag_base_name}\n')
        f.write('"""\n\n')
        f.write('import faiss\n')
        f.write('import numpy as np\n')
        f.write('import json\n')
        f.write('from openai import OpenAI\n\n')

        f.write('# Настройка API\n')
        f.write('API_KEY = "your-api-key-here"\n')
        f.write('API_BASE = "https://openai.api.proxyapi.ru/v1"\n')
        f.write(f'MODEL_NAME = "{metadata.get("model_name", "text-embedding-3-small")}"\n\n')

        f.write('class RAGDatabase:\n')
        f.write('    """Класс для работы с RAG-базой данных."""\n\n')
        f.write('    def __init__(self, index_path: str, dataset_path: str):\n')
        f.write('        """Инициализация базы данных."""\n')
        f.write('        self.index = faiss.read_index(index_path)\n')
        f.write('        with open(dataset_path, "r", encoding="utf-8") as f:\n')
        f.write('            self.dataset = json.load(f)\n')
        f.write('        self.client = OpenAI(api_key=API_KEY, base_url=API_BASE)\n\n')
        f.write('        print(f"Загружено {self.index.ntotal} векторов")\n')
        f.write('        print(f"Размерность: {self.index.d}")\n\n')

        f.write('    def generate_embedding(self, text: str) -> list:\n')
        f.write('        """Генерирует эмбеддинг для текста."""\n')
        f.write('        response = self.client.embeddings.create(\n')
        f.write('            model=MODEL_NAME,\n')
        f.write('            input=text\n')
        f.write('        )\n')
        f.write('        return response.data[0].embedding\n\n')

        f.write('    def search(self, query: str, k: int = 5) -> list:\n')
        f.write('        """Ищет топ-k релевантных чанков."""\n')
        f.write('        query_embedding = self.generate_embedding(query)\n')
        f.write('        query_vector = np.array([query_embedding], dtype="float32")\n')
        f.write('        distances, indices = self.index.search(query_vector, k)\n\n')

        f.write('        results = []\n')
        f.write('        for dist, idx in zip(distances[0], indices[0]):\n')
        f.write('            chunk = self.dataset[idx]\n')
        f.write('            results.append({\n')
        f.write('                "distance": float(dist),\n')
        f.write('                "text": chunk["text"],\n')
        f.write('                "source": chunk["metadata"]["source"],\n')
        f.write('                "page": chunk["metadata"]["page_number"],\n')
        f.write('                "chunk_id": chunk["metadata"]["chunk_id"]\n')
        f.write('            })\n')
        f.write('        return results\n\n')

        f.write('    def get_context(self, query: str, k: int = 5) -> str:\n')
        f.write('        """Возвращает контекст для запроса."""\n')
        f.write('        results = self.search(query, k)\n')
        f.write('        context = "\\n\\n".join([r["text"] for r in results])\n')
        f.write('        return context\n\n')

        f.write('# Использование\n')
        f.write('if __name__ == "__main__":\n')
        f.write('    # Инициализация\n')
        f.write('    rag = RAGDatabase("index.faiss", "dataset.json")\n\n')

        f.write('    # Пример поиска\n')
        f.write('    query = "Ваш запрос здесь"\n')
        f.write('    results = rag.search(query, k=3)\n\n')

        f.write('    print(f"Запрос: {query}\\n")\n')
        f.write('    for i, result in enumerate(results, 1):\n')
        f.write('        print(f"#{i} (расстояние: {result["distance"]:.4f})")\n')
        f.write('        print(f"Текст: {result["text"][:150]}...")\n')
        f.write('        print(f"Источник: {result["source"]}, страница {result["page"]}")\n')
        f.write('        print()\n')

    return str(example_path)


def generate_rag_package(
    rag_base_name: str,
    index_path: Path,
    dataset_path: Path,
    metadata_path: Path,
    source_files: List[Path],
    output_base_dir: Path
) -> Dict[str, str]:
    """
    Создаёт полный пакет RAG-базы данных.

    Args:
        rag_base_name: Название RAG-базы.
        index_path: Путь к индексу FAISS.
        dataset_path: Путь к датасету JSON.
        metadata_path: Путь к метаданным.
        source_files: Список исходных PDF-файлов.
        output_base_dir: Базовая директория для RAG-баз.

    Returns:
        Словарь с путями к созданным файлам.
    """
    import shutil

    logger.info(f"Создание RAG-пакета: {rag_base_name}")
    logger.info(f"  Index path: {index_path}")
    logger.info(f"  Dataset path: {dataset_path}")
    logger.info(f"  Metadata path: {metadata_path}")
    logger.info(f"  Source files: {len(source_files)}")

    # Проверяем существование файлов
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    # Создаём директорию для RAG-базы
    rag_dir = output_base_dir / rag_base_name
    rag_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"RAG directory created: {rag_dir}")

    # Создаём папку для исходных документов
    source_docs_dir = rag_dir / "source_documents"
    source_docs_dir.mkdir(exist_ok=True)

    # Копируем файлы базы данных
    shutil.copy2(index_path, rag_dir / "index.faiss")
    shutil.copy2(dataset_path, rag_dir / "dataset.json")
    shutil.copy2(metadata_path, rag_dir / "metadata.json")
    logger.info("Database files copied")

    # Копируем исходные PDF-файлы
    source_file_names = []
    for src_file in source_files:
        if src_file.exists():
            dest_file = source_docs_dir / src_file.name
            shutil.copy2(src_file, dest_file)
            source_file_names.append(src_file.name)
            logger.info(f"Source file copied: {src_file.name}")
        else:
            logger.warning(f"Source file not found: {src_file}")

    # Загружаем метаданные
    logger.info("Loading metadata...")
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    logger.info("Metadata loaded")

    # Генерируем README
    logger.info("Generating README...")
    readme_path = generate_rag_readme(
        rag_base_name,
        metadata,
        source_file_names,
        rag_dir
    )
    logger.info(f"README generated: {readme_path}")

    # Генерируем пример подключения
    logger.info("Generating example...")
    example_path = generate_connection_example_python(
        rag_base_name,
        metadata,
        rag_dir
    )
    logger.info(f"Example generated: {example_path}")

    logger.info("RAG package creation completed")
    return {
        "rag_dir": str(rag_dir),
        "readme": readme_path,
        "example": example_path,
        "index": str(rag_dir / "index.faiss"),
        "dataset": str(rag_dir / "dataset.json"),
        "metadata": str(rag_dir / "metadata.json"),
        "source_documents_dir": str(source_docs_dir)
    }
