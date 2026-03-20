"""
Модуль 4: Векторизация и сохранение в векторную БД.

Реализует этапы 7–8 (проверка качества, эмбеддинги, векторная БД).
"""

import json
import logging
import os
from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path

# Загрузка переменных окружения из .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv не установлен, используем переменные окружения напрямую

# Библиотеки для векторизации
try:
    import openai
except ImportError:
    openai = None

try:
    import faiss
    import numpy as np
except ImportError:
    faiss = None
    np = None

# Настройка логирования
logger = logging.getLogger(__name__)


def validate_data(final_dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Проверяет качество данных перед векторизацией.

    Args:
        final_dataset: Список чанков с текстом и метаданными.

    Returns:
        Словарь с результатами валидации.
    """
    logger.info("[Этап 7] Проверка качества данных")

    if not final_dataset:
        logger.warning("Датасет пуст")
        return {
            "total_chunks": 0,
            "empty_chunks": 0,
            "avg_length": 0,
            "stats": {
                "total_chunks": 0,
                "empty_chunks": 0,
                "total_chars": 0,
                "avg_char_count": 0,
                "min_char_count": 0,
                "max_char_count": 0
            }
        }

    total_chunks = len(final_dataset)
    empty_chunks = []
    total_chars = 0
    min_char_count = float('inf')
    max_char_count = 0

    for idx, chunk in enumerate(final_dataset):
        text = chunk.get("text", "")
        char_count = len(text.strip())
        total_chars += char_count

        if not text.strip():
            empty_chunks.append(idx)

        if char_count > 0:
            if char_count < min_char_count:
                min_char_count = char_count
            if char_count > max_char_count:
                max_char_count = char_count

    avg_length = total_chars / total_chunks if total_chunks > 0 else 0

    # Вывод в консоль
    print("\n" + "=" * 60)
    print("[Этап 7: Проверка качества]")
    print(f"Всего чанков: {total_chunks}")
    print(f"Пустых чанков: {len(empty_chunks)}")
    print(f"Средняя длина: {avg_length:.0f} символов")
    print(f"Мин/Макс длина: {min_char_count}/{max_char_count}")
    print("=" * 60 + "\n")

    logger.info(f"[Этап 7] Всего чанков: {total_chunks}, Пустых: {len(empty_chunks)}, Средняя длина: {avg_length:.2f}")

    return {
        "total_chunks": total_chunks,
        "empty_chunks": empty_chunks,
        "avg_length": avg_length,
        "stats": {
            "total_chunks": total_chunks,
            "empty_chunks": len(empty_chunks),
            "total_chars": total_chars,
            "avg_char_count": avg_length,
            "min_char_count": min_char_count,
            "max_char_count": max_char_count
        }
    }


def save_to_vector_db(
    final_dataset: List[Dict[str, Any]],
    db_type: str = "faiss",
    model_name: str = "text-embedding-3-small",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    output_dir: str = "output",
    use_cache: bool = True,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Dict[str, Any]:
    """
    Генерирует эмбеддинги и сохраняет в векторную БД.

    Args:
        final_dataset: Список чанков с текстом и метаданными.
        db_type: Тип векторной БД (по умолчанию "faiss").
        model_name: Название модели эмбеддингов OpenAI.
        api_key: API ключ OpenAI (если None, использует переменную окружения).
        api_base: Базовый URL API (по умолчанию прокси).
        output_dir: Директория для сохранения результатов.

    Returns:
        Словарь с результатами векторизации.
    """
    logger.info(f"[Этап 8] Начало векторизации (модель: {model_name})")

    # Проверка зависимостей
    if openai is None:
        raise ImportError(
            "Библиотека openai не установлена. "
            "Выполните: pip install openai"
        )

    if faiss is None or np is None:
        raise ImportError(
            "Библиотеки faiss или numpy не установлены. "
            "Выполните: pip install faiss-cpu numpy"
        )

    # Проверка данных
    if not final_dataset:
        logger.warning("Датасет пуст, векторизация пропущена")
        return {
            "success": False,
            "embeddings": [],
            "embedding_dim": 0,
            "vector_db_path": None,
            "dataset_path": None
        }

    # Настройка клиента OpenAI
    # Если api_key не передан, используем переменную окружения
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError(
                "API ключ OpenAI не указан. "
                "Передайте его в параметре api_key или установите переменную окружения OPENAI_API_KEY в файле .env"
            )

    # Если api_base не передан, используем переменную окружения или значение по умолчанию
    if api_base is None:
        api_base = os.getenv("OPENAI_API_BASE", "https://openai.api.proxyapi.ru/v1")

    client = openai.OpenAI(
        api_key=api_key,
        base_url=api_base
    )

    # Извлекаем тексты для векторизации
    texts = [chunk["text"] for chunk in final_dataset]

    logger.info(f"[Этап 8] Генерация эмбеддингов для {len(texts)} чанков...")

    # Инициализация кэша (если включено)
    cache = None
    cached_count = 0
    
    if use_cache:
        try:
            from src.embedding_cache import get_embedding_cache
            cache = get_embedding_cache()
            logger.info(f"[Этап 8] Кэш эмбеддингов включён")
        except ImportError:
            logger.warning("[Этап 8] Модуль кэша не найден, кэширование отключено")
            use_cache = False

    # Функция для генерации эмбеддингов с retry
    def generate_with_retry(client, texts: list, model: str) -> list:
        """Генерирует эмбеддинги с автоматическим retry."""
        import time
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    model=model,
                    input=texts
                )
                return [item.embedding for item in response.data]
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"[Этап 8] Попытка {attempt + 1} неудачна: {e}. Повтор через {wait_time}с...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[Этап 8] Все {max_retries} попыток исчерпаны")
        
        raise last_error
    
    try:
        # Проверяем кэш
        if use_cache and cache:
            # Разделяем на кэшированные и новые
            cached_embeddings = cache.get_batch(texts, model_name)
            new_indices = [i for i in range(len(texts)) if i not in cached_embeddings]
            cached_count = len(cached_embeddings)
            
            if new_indices:
                # Получаем только новые эмбеддинги с retry
                new_texts = [texts[i] for i in new_indices]
                new_embeddings = generate_with_retry(client, new_texts, model_name)
                
                # Сохраняем новые в кэш
                cache.set_batch(new_texts, model_name, new_embeddings)
                
                # Объединяем
                embeddings = []
                new_idx = 0
                for i in range(len(texts)):
                    if i in cached_embeddings:
                        embeddings.append(cached_embeddings[i])
                    else:
                        embeddings.append(new_embeddings[new_idx])
                        new_idx += 1
            else:
                # Все в кэше
                embeddings = [cached_embeddings[i] for i in range(len(texts))]
        else:
            # Стандартный вызов без кэша
            embeddings = generate_with_retry(client, texts, model_name)

        embedding_dim = len(embeddings[0]) if embeddings else 0

        logger.info(f"[Этап 8] Сгенерировано {len(embeddings)} эмбеддингов (из кэша: {cached_count}) размерности {embedding_dim}")

    except Exception as e:
        logger.error(f"[Этап 8] Ошибка при генерации эмбеддингов после {max_retries} попыток: {e}")
        raise

    # Создание индекса FAISS
    logger.info(f"[Этап 8] Создание индекса FAISS (тип: {db_type})")

    embeddings_array = np.array(embeddings, dtype='float32')

    if db_type == "faiss":
        # IndexFlatL2 - базовый L2 индекс
        index = faiss.IndexFlatL2(embedding_dim)
        index.add(embeddings_array)
    else:
        logger.warning(f"Тип БД {db_type} не поддерживается, используется FAISS")
        index = faiss.IndexFlatL2(embedding_dim)
        index.add(embeddings_array)

    # Сохранение индекса
    vector_db_dir = Path(output_dir) / "vector_db"
    vector_db_dir.mkdir(parents=True, exist_ok=True)

    index_path = vector_db_dir / "index.faiss"
    faiss.write_index(index, str(index_path))

    logger.info(f"[Этап 8] Индекс FAISS сохранён: {index_path}")

    # Сохранение датасета в JSON
    dataset_path = vector_db_dir / "dataset.json"
    with open(dataset_path, 'w', encoding='utf-8') as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)

    logger.info(f"[Этап 8] Датасет сохранён: {dataset_path}")

    # Сохранение метаданных индекса
    metadata = {
        "model_name": model_name,
        "embedding_dim": embedding_dim,
        "total_vectors": len(embeddings),
        "db_type": db_type,
        "created_at": datetime.now().isoformat(),
        "index_path": str(index_path),
        "dataset_path": str(dataset_path)
    }

    metadata_path = vector_db_dir / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"[Этап 8] Метаданные сохранены: {metadata_path}")

    return {
        "success": True,
        "embeddings": embeddings,
        "embedding_dim": embedding_dim,
        "vector_db_path": str(index_path),
        "dataset_path": str(dataset_path),
        "metadata_path": str(metadata_path),
        "total_vectors": len(embeddings)
    }


def generate_vectorization_report(
    validation_result: Dict[str, Any],
    vectorization_result: Dict[str, Any],
    model_name: str,
    db_type: str,
    output_dir: str = "output_module_4"
) -> str:
    """
    Генерирует отчёт по этапам 7–8 (проверка качества и векторизация).

    Args:
        validation_result: Результаты валидации данных.
        vectorization_result: Результаты векторизации.
        model_name: Название модели эмбеддингов.
        db_type: Тип векторной БД.
        output_dir: Директория для сохранения отчёта.

    Returns:
        Путь к созданному файлу отчёта.
    """
    logger.info("Генерация отчёта по векторизации")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report_path = output_path / "vectorization_report.txt"

    with open(report_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write("# Отчёт по векторизации и векторной БД\n\n")
        f.write(f"**Дата генерации:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Этап 7: Проверка качества
        f.write("## Этап 7: Проверка качества данных\n\n")

        stats = validation_result.get("stats", {})
        f.write("**Статистика:**\n")
        f.write("| Параметр | Значение |\n")
        f.write("|----------|----------|\n")
        f.write(f"| Всего чанков | {stats.get('total_chunks', 0)} |\n")
        f.write(f"| Пустых чанков | {stats.get('empty_chunks', 0)} |\n")
        f.write(f"| Всего символов | {stats.get('total_chars', 0)} |\n")
        f.write(f"| Средняя длина (символы) | {stats.get('avg_char_count', 0):.2f} |\n")
        f.write(f"| Минимальная длина (символы) | {stats.get('min_char_count', 0)} |\n")
        f.write(f"| Максимальная длина (символы) | {stats.get('max_char_count', 0)} |\n\n")

        # Статус валидации
        f.write("**Статус валидации:** ")
        if stats.get('empty_chunks', 0) == 0 and stats.get('total_chunks', 0) > 0:
            f.write("✅ Данные прошли валидацию\n\n")
        else:
            f.write("⚠️ Обнаружены проблемы с данными\n\n")

        # Этап 8: Векторизация и БД
        f.write("## Этап 8: Векторизация и векторная БД\n\n")
        f.write("**Параметры:**\n")
        f.write(f"- **Модель:** {model_name}\n")
        f.write(f"- **Тип БД:** {db_type}\n")
        f.write(f"- **Векторов:** {vectorization_result.get('total_vectors', 0)}\n")
        f.write(f"- **Размерность:** {vectorization_result.get('embedding_dim', 0)}\n")
        f.write(f"- **Путь к индексу:** `{vectorization_result.get('vector_db_path', 'N/A')}`\n")
        f.write(f"- **Путь к датасету:** `{vectorization_result.get('dataset_path', 'N/A')}`\n\n")

        # Статус векторизации
        f.write("**Статус векторизации:** ")
        if vectorization_result.get('success', False):
            f.write("✅ Векторизация успешно завершена\n\n")
        else:
            f.write("❌ Векторизация завершилась с ошибкой\n\n")

        # Итоговый статус
        f.write("---\n\n")
        f.write("**Итоговый статус:** ")
        if (stats.get('empty_chunks', 0) == 0 and
            stats.get('total_chunks', 0) > 0 and
            vectorization_result.get('success', False)):
            f.write("✅ Все этапы успешно завершены\n\n")
        else:
            f.write("⚠️ Обнаружены проблемы на этапах обработки\n\n")

        f.write("---\n\n")
        f.write(f"**Конец отчёта**\n")

    # Вывод в консоль
    print("\n" + "=" * 60)
    print("[Этап 8: Векторизация и БД]")
    print(f"Модель: {model_name}")
    print(f"Тип БД: {db_type}")
    print(f"Векторов: {vectorization_result.get('total_vectors', 0)}")
    print(f"Размерность: {vectorization_result.get('embedding_dim', 0)}")
    print(f"Путь: {output_dir}/vector_db/")
    print("=" * 60 + "\n")

    logger.info(f"Отчёт по векторизации сохранён: {report_path}")
    return str(report_path)


def process_vectorization(
    final_dataset: List[Dict[str, Any]],
    output_dir: str = "output",
    model_name: str = "text-embedding-3-small",
    db_type: str = "faiss",
    api_key: str = None,
    api_base: str = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Полный цикл векторизации и сохранения в БД.

    Args:
        final_dataset: Список чанков с текстом и метаданными.
        output_dir: Директория для сохранения результатов.
        model_name: Название модели эмбеддингов.
        db_type: Тип векторной БД.
        api_key: API ключ OpenAI (если None, используется переменная окружения OPENAI_API_KEY).
        api_base: Базовый URL API (если None, используется переменная окружения OPENAI_API_BASE).

    Returns:
        Словарь с результатами обработки.
    """
    logger.info("Начало векторизации датасета")

    # Этап 7: Проверка качества
    validation_result = validate_data(final_dataset)

    # Этап 8: Векторизация и сохранение в БД
    vectorization_result = save_to_vector_db(
        final_dataset,
        db_type=db_type,
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        output_dir=output_dir,
        use_cache=use_cache
    )

    # Генерация отчёта
    report_path = generate_vectorization_report(
        validation_result,
        vectorization_result,
        model_name,
        db_type,
        output_dir="output_module_4"
    )

    logger.info("Векторизация завершена")

    return {
        "validation": validation_result,
        "vectorization": vectorization_result,
        "report_path": report_path
    }
