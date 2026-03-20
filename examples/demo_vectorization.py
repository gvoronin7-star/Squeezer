"""
Демонстрационный скрипт для создания данных в output_module_4.
Создаёт тестовый PDF и обрабатывает его с векторизацией.
"""

import sys
from pathlib import Path

# Настройка кодировки вывода для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("Демонстрация: Создание данных в output_module_4")
print("=" * 60)

# Проверка API ключа
import os
api_key = os.getenv("OPENAI_API_KEY")

if not api_key or api_key == 'your-api-key-here':
    print("\n[ERROR] API ключ не установлен в файле .env")
    print("Пожалуйста, заполните OPENAI_API_KEY в файле .env")
    exit(1)

# Создание тестовых чанков
test_chunks = [
    {
        "text": "Это первый тестовый чанк для демонстрации работы Модуля 4. Он содержит некоторый текст для проверки векторизации и создания отчёта.",
        "type": "paragraph",
        "context": {},
        "metadata": {
            "source": "demo_document.pdf",
            "page_number": 1,
            "chunk_id": "chunk_000",
            "timestamp": "2026-02-18T12:00:00",
            "chunk_type": "paragraph",
            "char_count": 145,
            "word_count": 24
        }
    },
    {
        "text": "Второй чанк с другим содержимым. Этот текст демонстрирует правильность генерации эмбеддингов через OpenAI API.",
        "type": "paragraph",
        "context": {},
        "metadata": {
            "source": "demo_document.pdf",
            "page_number": 1,
            "chunk_id": "chunk_001",
            "timestamp": "2026-02-18T12:00:00",
            "chunk_type": "paragraph",
            "char_count": 139,
            "word_count": 21
        }
    },
    {
        "text": "Третий чанк для проверки корректности работы всей системы векторизации и создания отчёта в output_module_4.",
        "type": "paragraph",
        "context": {},
        "metadata": {
            "source": "demo_document.pdf",
            "page_number": 2,
            "chunk_id": "chunk_002",
            "timestamp": "2026-02-18T12:00:00",
            "chunk_type": "paragraph",
            "char_count": 136,
            "word_count": 20
        }
    },
    {
        "text": "Четвертый чанк с заголовком. Тестирование разных типов контента.",
        "type": "heading",
        "context": {},
        "metadata": {
            "source": "demo_document.pdf",
            "page_number": 2,
            "chunk_id": "chunk_003",
            "timestamp": "2026-02-18T12:00:00",
            "chunk_type": "heading",
            "char_count": 76,
            "word_count": 12
        }
    },
    {
        "text": "Пятый чанк в виде списка. Проверка обработки списковых элементов. Третий пункт списка.",
        "type": "list",
        "context": {},
        "metadata": {
            "source": "demo_document.pdf",
            "page_number": 3,
            "chunk_id": "chunk_004",
            "timestamp": "2026-02-18T12:00:00",
            "chunk_type": "list",
            "char_count": 96,
            "word_count": 17
        }
    }
]

print(f"\n[INFO] Создано {len(test_chunks)} тестовых чанков")

# Выполнение векторизации
from src.vectorizer import process_vectorization

print("\n" + "-" * 60)
print("Выполнение векторизации...")
print("-" * 60)

try:
    result = process_vectorization(
        test_chunks,
        output_dir="output",
        model_name="text-embedding-3-small",
        db_type="faiss"
    )

    print("\n[OK] Векторизация завершена")
    print(f"\nРезультаты:")
    print(f"  Валидация: {result['validation']['stats']['total_chunks']} чанков")
    print(f"  Векторизация: {result['vectorization']['total_vectors']} векторов")
    print(f"  Размерность: {result['vectorization']['embedding_dim']}")
    print(f"\n  Отчёт: {result['report_path']}")

    # Проверка созданных файлов
    print("\n" + "-" * 60)
    print("Созданные файлы:")
    print("-" * 60)

    report_path = Path(result['report_path'])
    if report_path.exists():
        size_kb = report_path.stat().st_size / 1024
        print(f"[OK] {report_path} ({size_kb:.2f} KB)")
    else:
        print(f"[ERROR] {report_path} - файл не найден")

    vector_db_dir = Path("output/vector_db")
    if vector_db_dir.exists():
        for file in vector_db_dir.iterdir():
            if file.is_file():
                size_kb = file.stat().st_size / 1024
                print(f"[OK] {file} ({size_kb:.2f} KB)")
    else:
        print(f"[ERROR] {vector_db_dir} - директория не найдена")

    print("\n" + "=" * 60)
    print("[OK] Демонстрация завершена!")
    print("=" * 60)
    print("\nТеперь в папке output_module_4 находится отчёт по векторизации.")
    print("В папке output/vector_db находятся файлы векторной БД.")

except Exception as e:
    print(f"\n[ERROR] Ошибка: {e}")
    import traceback
    traceback.print_exc()
