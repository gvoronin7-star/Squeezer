"""
Тестовый скрипт для проверки Модуля 4 (Векторизация и векторная БД).
"""

import sys
import os
from pathlib import Path

# Настройка кодировки вывода для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("Тестирование Модуля 4: Векторизация и векторная БД")
print("=" * 60)

# Импорт модуля векторизации
try:
    from src.vectorizer import (
        validate_data,
        save_to_vector_db,
        generate_vectorization_report,
        process_vectorization
    )
    print("\n[OK] Модуль vectorizer импортирован")
except ImportError as e:
    print(f"\n[ERROR] Не удалось импортировать модуль vectorizer: {e}")
    exit(1)

# Создание тестовых данных
test_chunks = [
    {
        "text": "Это первый тестовый чанк. Он содержит некоторый текст для проверки векторизации.",
        "type": "paragraph",
        "context": {},
        "metadata": {
            "source": "test_document.pdf",
            "page_number": 1,
            "chunk_id": "chunk_000",
            "timestamp": "2026-02-18T12:00:00",
            "chunk_type": "paragraph",
            "char_count": 85,
            "word_count": 15
        }
    },
    {
        "text": "Второй чанк с другим содержимым. Тестирование правильности генерации эмбеддингов.",
        "type": "paragraph",
        "context": {},
        "metadata": {
            "source": "test_document.pdf",
            "page_number": 1,
            "chunk_id": "chunk_001",
            "timestamp": "2026-02-18T12:00:00",
            "chunk_type": "paragraph",
            "char_count": 92,
            "word_count": 14
        }
    },
    {
        "text": "Третий чанк для проверки корректности работы всей системы векторизации.",
        "type": "paragraph",
        "context": {},
        "metadata": {
            "source": "test_document.pdf",
            "page_number": 2,
            "chunk_id": "chunk_002",
            "timestamp": "2026-02-18T12:00:00",
            "chunk_type": "paragraph",
            "char_count": 78,
            "word_count": 13
        }
    }
]

print(f"\n[INFO] Создано {len(test_chunks)} тестовых чанков")

# Тест 1: Валидация данных
print("\n" + "-" * 60)
print("Тест 1: Валидация данных")
print("-" * 60)

try:
    validation_result = validate_data(test_chunks)
    print(f"[OK] Валидация пройдена")
    print(f"  Всего чанков: {validation_result['stats']['total_chunks']}")
    print(f"  Пустых чанков: {validation_result['stats']['empty_chunks']}")
    print(f"  Средняя длина: {validation_result['stats']['avg_char_count']:.2f}")
except Exception as e:
    print(f"[ERROR] Ошибка валидации: {e}")
    exit(1)

# Тест 2: Векторизация и сохранение в БД
print("\n" + "-" * 60)
print("Тест 2: Векторизация и сохранение в БД")
print("-" * 60)

test_output_dir = "test_output"

try:
    vectorization_result = save_to_vector_db(
        test_chunks,
        db_type="faiss",
        model_name="text-embedding-3-small",
        output_dir=test_output_dir
    )

    if vectorization_result['success']:
        print(f"[OK] Векторизация пройдена")
        print(f"  Всего векторов: {vectorization_result['total_vectors']}")
        print(f"  Размерность: {vectorization_result['embedding_dim']}")
        print(f"  Индекс: {vectorization_result['vector_db_path']}")
        print(f"  Датасет: {vectorization_result['dataset_path']}")
    else:
        print(f"[ERROR] Векторизация не удалась")
        exit(1)

except Exception as e:
    print(f"[ERROR] Ошибка векторизации: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Тест 3: Проверка созданных файлов
print("\n" + "-" * 60)
print("Тест 3: Проверка созданных файлов")
print("-" * 60)

index_path = Path(test_output_dir) / "vector_db" / "index.faiss"
dataset_path = Path(test_output_dir) / "vector_db" / "dataset.json"
metadata_path = Path(test_output_dir) / "vector_db" / "metadata.json"

files_to_check = [
    ("Индекс FAISS", index_path),
    ("Датасет JSON", dataset_path),
    ("Метаданные", metadata_path)
]

all_files_exist = True
for name, path in files_to_check:
    if path.exists():
        size_kb = path.stat().st_size / 1024
        print(f"[OK] {name}: {path} ({size_kb:.2f} KB)")
    else:
        print(f"[ERROR] {name}: {path} - файл не найден")
        all_files_exist = False

# Тест 4: Проверка загрузки индекса FAISS
print("\n" + "-" * 60)
print("Тест 4: Проверка загрузки индекса FAISS")
print("-" * 60)

try:
    import faiss
    import json

    # Загрузка индекса
    index = faiss.read_index(str(index_path))
    print(f"[OK] Индекс FAISS загружен")
    print(f"  Размерность: {index.d}")
    print(f"  Количество векторов: {index.ntotal}")

    # Загрузка датасета
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    print(f"[OK] Датасет загружен")
    print(f"  Количество чанков: {len(dataset)}")

    # Загрузка метаданных
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    print(f"[OK] Метаданные загружены")
    print(f"  Модель: {metadata['model_name']}")
    print(f"  Дата создания: {metadata['created_at']}")

except Exception as e:
    print(f"[ERROR] Ошибка загрузки файлов: {e}")
    import traceback
    traceback.print_exc()

# Тест 5: Тестирование поиска
print("\n" + "-" * 60)
print("Тест 5: Тестирование поиска в FAISS")
print("-" * 60)

try:
    import numpy as np
    import openai

    # Генерация эмбеддинга для запроса
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE", "https://openai.api.proxyapi.ru/v1")

    client = openai.OpenAI(api_key=api_key, base_url=api_base)
    query_response = client.embeddings.create(
        model="text-embedding-3-small",
        input="тестовый запрос"
    )
    query_embedding = query_response.data[0].embedding

    # Поиск ближайших векторов
    query_vector = np.array([query_embedding], dtype='float32')
    k = 2  # Количество результатов
    distances, indices = index.search(query_vector, k)

    print(f"[OK] Поиск выполнен")
    print(f"  Запрос: 'тестовый запрос'")
    print(f"  Количество результатов: {k}")

    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        chunk = dataset[idx]
        print(f"\n  Результат #{i+1}:")
        print(f"    Расстояние: {dist:.4f}")
        print(f"    Текст: {chunk['text'][:50]}...")
        print(f"    ID: {chunk['metadata']['chunk_id']}")

except Exception as e:
    print(f"[ERROR] Ошибка поиска: {e}")
    import traceback
    traceback.print_exc()

# Тест 6: Генерация отчёта
print("\n" + "-" * 60)
print("Тест 6: Генерация отчёта")
print("-" * 60)

try:
    report_path = generate_vectorization_report(
        validation_result,
        vectorization_result,
        model_name="text-embedding-3-small",
        db_type="faiss",
        output_dir="test_output_module_4"
    )

    print(f"[OK] Отчёт сгенерирован")
    print(f"  Путь: {report_path}")

    # Проверка содержимого отчёта
    with open(report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    print(f"  Размер: {len(report_content)} символов")

except Exception as e:
    print(f"[ERROR] Ошибка генерации отчёта: {e}")

# Итог
print("\n" + "=" * 60)
print("[OK] Все тесты пройдены успешно!")
print("=" * 60)

# Очистка тестовых файлов (опционально)
print("\n[INFO] Тестовые файлы сохранены в:")
print(f"  - {test_output_dir}/vector_db/")
print(f"  - test_output_module_4/")
print("\nДля удаления выполните:")
print(f"  rmdir /s /q {test_output_dir}")
print(f"  rmdir /s /q test_output_module_4")
