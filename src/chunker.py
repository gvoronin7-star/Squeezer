"""
Модуль 3: Гибридный чанкинг и метаданные.

Реализует этапы 5–6 (гибридное разбиение и добавление метаданных).
"""

import logging
from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path

# Настройка логирования
logger = logging.getLogger(__name__)


def hybrid_chunking(
    structured_text: Dict[str, Any],
    max_chunk_size: int = 500,
    overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Выполняет гибридное разбиение структурированного текста на чанки.

    Сначала разбивает на семантические блоки (абзацы, списки, заголовки).
    Если блок > max_chunk_size, применяет фиксированное разбиение с перекрытием.

    Args:
        structured_text: Структурированный текст (результат structure_text).
        max_chunk_size: Максимальный размер чанка в символах.
        overlap: Перекрытие между чанками в символах.

    Returns:
        Список чанков с текстом и типом блока.
    """
    logger.info(f"[Этап 5] Начало гибридного чанкинга (max_chunk_size={max_chunk_size}, overlap={overlap})")

    chunks: List[Dict[str, Any]] = []

    # 1. Разбиваем на семантические блоки
    semantic_blocks = _extract_semantic_blocks(structured_text)
    logger.debug(f"Извлечено семантических блоков: {len(semantic_blocks)}")

    # 2. Обрабатываем каждый блок
    for block in semantic_blocks:
        block_text = block["text"]
        block_type = block["type"]
        block_context = block.get("context", {})

        if len(block_text) <= max_chunk_size:
            # Блок подходит целиком
            chunks.append({
                "text": block_text,
                "type": block_type,
                "context": block_context
            })
        else:
            # Блок слишком большой, разбиваем с перекрытием
            sub_chunks = _split_large_block(block_text, max_chunk_size, overlap, block_type, block_context)
            chunks.extend(sub_chunks)

    logger.info(f"[Этап 5] Создано чанков: {len(chunks)}")
    return chunks


def _extract_semantic_blocks(structured_text: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Извлекает семантические блоки из структурированного текста.

    Args:
        structured_text: Структурированный текст.

    Returns:
        Список семантических блоков.
    """
    blocks = []

    # Добавляем заголовки как отдельные блоки
    for heading in structured_text.get("headings", []):
        blocks.append({
            "text": heading,
            "type": "heading",
            "context": {}
        })

    # Добавляем абзацы
    for paragraph in structured_text.get("paragraphs", []):
        blocks.append({
            "text": paragraph,
            "type": "paragraph",
            "context": {}
        })

    # Добавляем списки (каждый элемент как отдельный блок или весь список)
    for lst in structured_text.get("lists", []):
        # Если список короткий, добавляем целиком
        list_text = " ".join(lst)
        if len(list_text) < 300:
            blocks.append({
                "text": list_text,
                "type": "list",
                "context": {"items": len(lst)}
            })
        else:
            # Длинный список разбиваем на элементы
            for item in lst:
                blocks.append({
                    "text": item,
                    "type": "list_item",
                    "context": {}
                })

    # Добавляем FAQ-блоки (если есть)
    if structured_text.get("metadata", {}).get("has_questions", False):
        # FAQ уже должны быть в заголовках и абзацах
        pass

    return blocks


def _split_large_block(
    text: str,
    max_chunk_size: int,
    overlap: int,
    block_type: str,
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Разбивает большой блок на чанки с перекрытием.

    Args:
        text: Текст блока.
        max_chunk_size: Максимальный размер чанка.
        overlap: Перекрытие между чанками.
        block_type: Тип блока.
        context: Контекст блока.

    Returns:
        Список чанков.
    """
    chunks = []
    step = max_chunk_size - overlap

    # Разбиваем на предложения для более естественного разбиения
    sentences = _split_into_sentences(text)

    # Собираем чанки из предложений
    current_chunk = ""
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if current_length + sentence_len <= max_chunk_size:
            # Предложение помещается в текущий чанк
            current_chunk += sentence + " "
            current_length += sentence_len + 1
        else:
            # Сохраняем текущий чанк если он не пуст
            if current_chunk.strip():
                chunks.append({
                    "text": current_chunk.strip(),
                    "type": block_type,
                    "context": context
                })

            # Начинаем новый чанк с перекрытием
            # Для перекрытия берем последние N символов из предыдущего чанка
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-overlap:] if len(current_chunk) >= overlap else current_chunk
                current_chunk = overlap_text + " " + sentence + " "
                current_length = len(overlap_text) + sentence_len + 1
            else:
                current_chunk = sentence + " "
                current_length = sentence_len + 1

    # Добавляем последний чанк
    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "type": block_type,
            "context": context
        })

    # Если после разбиения на предложения получилось слишком длинно,
    # используем простое разбиение по символам
    if len(chunks) == 0 or any(len(c["text"]) > max_chunk_size * 1.5 for c in chunks):
        chunks = []
        for i in range(0, len(text), step):
            chunk_text = text[i:i + max_chunk_size]
            chunks.append({
                "text": chunk_text,
                "type": block_type,
                "context": context
            })

    return chunks


def _split_into_sentences(text: str) -> List[str]:
    """
    Разбивает текст на предложения.

    Args:
        text: Текст для разбиения.

    Returns:
        Список предложений.
    """
    import re

    # Простое разбиение по знакам конца предложения
    # Учитываем точки, восклицательные и вопросительные знаки
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Фильтруем пустые предложения
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def add_metadata(
    chunks: List[Dict[str, Any]],
    pdf_path: str,
    page_number: int = 1
) -> List[Dict[str, Any]]:
    """
    Добавляет метаданные к каждому чанку.

    Args:
        chunks: Список чанков.
        pdf_path: Путь к исходному PDF-файлу.
        page_number: Номер страницы (по умолчанию 1).

    Returns:
        Список чанков с добавленными метаданными.
    """
    logger.info(f"[Этап 6] Добавление метаданных к {len(chunks)} чанкам")

    timestamp = datetime.now().isoformat()

    for idx, chunk in enumerate(chunks):
        chunk["metadata"] = {
            "source": pdf_path,
            "page_number": page_number,
            "chunk_id": f"chunk_{idx:03d}",
            "timestamp": timestamp,
            "chunk_type": chunk.get("type", "unknown"),
            "char_count": len(chunk["text"]),
            "word_count": len(chunk["text"].split())
        }

    logger.info(f"[Этап 6] Метаданные добавлены")
    return chunks


def validate_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Валидирует чанки и вычисляет статистику.

    Args:
        chunks: Список чанков для валидации.

    Returns:
        Словарь с результатами валидации и статистикой.
    """
    logger.info("[Этап 5-6] Валидация чанков")

    validation_result = {
        "total_chunks": len(chunks),
        "empty_chunks": [],
        "too_short_chunks": [],
        "too_long_chunks": [],
        "stats": {
            "total_chunks": len(chunks),
            "total_chars": 0,
            "total_words": 0,
            "avg_char_count": 0,
            "min_char_count": float('inf'),
            "max_char_count": 0,
            "avg_word_count": 0,
            "min_word_count": float('inf'),
            "max_word_count": 0
        },
        "chunk_types": {}
    }

    if not chunks:
        logger.warning("Список чанков пуст")
        return validation_result

    for idx, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        char_count = len(text.strip())
        word_count = len(text.split())

        # Проверка на пустоту
        if not text.strip():
            validation_result["empty_chunks"].append(idx)
            logger.warning(f"Чанк {idx} пустой")

        # Проверка на слишком короткие чанки (меньше 10 символов)
        if char_count > 0 and char_count < 10:
            validation_result["too_short_chunks"].append(idx)
            logger.debug(f"Чанк {idx} слишком короткий: {char_count} символов")

        # Собираем статистику
        validation_result["stats"]["total_chars"] += char_count
        validation_result["stats"]["total_words"] += word_count

        if char_count > 0:
            if char_count < validation_result["stats"]["min_char_count"]:
                validation_result["stats"]["min_char_count"] = char_count
            if char_count > validation_result["stats"]["max_char_count"]:
                validation_result["stats"]["max_char_count"] = char_count

        if word_count > 0:
            if word_count < validation_result["stats"]["min_word_count"]:
                validation_result["stats"]["min_word_count"] = word_count
            if word_count > validation_result["stats"]["max_word_count"]:
                validation_result["stats"]["max_word_count"] = word_count

        # Статистика по типам чанков
        chunk_type = chunk.get("type", "unknown")
        if chunk_type not in validation_result["chunk_types"]:
            validation_result["chunk_types"][chunk_type] = 0
        validation_result["chunk_types"][chunk_type] += 1

    # Вычисляем средние значения
    if validation_result["stats"]["total_chunks"] > 0:
        validation_result["stats"]["avg_char_count"] = (
            validation_result["stats"]["total_chars"] / validation_result["stats"]["total_chunks"]
        )
        validation_result["stats"]["avg_word_count"] = (
            validation_result["stats"]["total_words"] / validation_result["stats"]["total_chunks"]
        )

    # Логируем результаты валидации
    logger.info(f"[Валидация] Всего чанков: {validation_result['stats']['total_chunks']}")
    logger.info(f"[Валидация] Пустых чанков: {len(validation_result['empty_chunks'])}")
    logger.info(f"[Валидация] Слишком коротких: {len(validation_result['too_short_chunks'])}")
    logger.info(f"[Валидация] Средняя длина: {validation_result['stats']['avg_char_count']:.2f} символов")
    logger.info(f"[Валидация] Мин/Макс длина: {validation_result['stats']['min_char_count']}/{validation_result['stats']['max_char_count']}")

    return validation_result


def generate_chunking_report(
    validation_result: Dict[str, Any],
    max_chunk_size: int,
    overlap: int,
    output_file: str = "output_module_3/chunking_report.txt"
) -> str:
    """
    Генерирует отчёт по чанкингу.

    Args:
        validation_result: Результаты валидации чанков.
        max_chunk_size: Максимальный размер чанка.
        overlap: Перекрытие между чанками.
        output_file: Путь к файлу отчёта.

    Returns:
        Путь к созданному файлу.
    """
    logger.info("Генерация отчёта по чанкингу")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stats = validation_result["stats"]

    with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write("# Отчёт по чанкингу\n\n")
        f.write(f"**Дата генерации:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Этап 5: Гибридный чанкинг\n\n")
        f.write("**Параметры:**\n")
        f.write(f"- Максимальный размер: {max_chunk_size} символов\n")
        f.write(f"- Перекрытие: {overlap} символов\n\n")

        f.write("**Статистика:**\n")
        f.write("| Параметр | Значение |\n")
        f.write("|----------|----------|\n")
        f.write(f"| Всего чанков | {stats['total_chunks']} |\n")
        f.write(f"| Всего символов | {stats['total_chars']} |\n")
        f.write(f"| Всего слов | {stats['total_words']} |\n")
        f.write(f"| Средняя длина (символы) | {stats['avg_char_count']:.2f} |\n")
        f.write(f"| Минимальная длина (символы) | {stats['min_char_count']} |\n")
        f.write(f"| Максимальная длина (символы) | {stats['max_char_count']} |\n")
        f.write(f"| Средняя длина (слова) | {stats['avg_word_count']:.2f} |\n")
        f.write(f"| Минимальная длина (слова) | {stats['min_word_count']} |\n")
        f.write(f"| Максимальная длина (слова) | {stats['max_word_count']} |\n\n")

        # Типы чанков
        if validation_result["chunk_types"]:
            f.write("**Распределение по типам:**\n")
            f.write("| Тип | Количество |\n")
            f.write("|-----|-----------|\n")
            for chunk_type, count in sorted(validation_result["chunk_types"].items()):
                f.write(f"| {chunk_type} | {count} |\n")
            f.write("\n")

        # Проблемы
        f.write("## Валидация\n\n")
        f.write(f"- Пустых чанков: {len(validation_result['empty_chunks'])}\n")
        if validation_result["empty_chunks"]:
            f.write(f"  Индексы: {', '.join(map(str, validation_result['empty_chunks']))}\n")

        f.write(f"- Слишком коротких чанков (< 10 символов): {len(validation_result['too_short_chunks'])}\n")
        if validation_result["too_short_chunks"]:
            f.write(f"  Индексы: {', '.join(map(str, validation_result['too_short_chunks']))}\n")

        # Статус
        f.write("\n**Статус:** ")
        if (not validation_result["empty_chunks"] and
            not validation_result["too_short_chunks"] and
            stats["total_chunks"] > 0):
            f.write("✅ Все чанки прошли валидацию\n")
        else:
            f.write("⚠️ Обнаружены проблемы с чанками\n")

    # Вывод в консоль
    print("\n" + "=" * 60)
    print("[Этап 5: Гибридный чанкинг]")
    print(f"Всего чанков: {stats['total_chunks']}")
    print(f"Средняя длина: {stats['avg_char_count']:.2f} символов")
    print(f"Мин/Макс длина: {stats['min_char_count']}/{stats['max_char_count']}")
    print(f"Пустых чанков: {len(validation_result['empty_chunks'])}")
    print(f"Слишком коротких: {len(validation_result['too_short_chunks'])}")
    print("=" * 60 + "\n")

    logger.info(f"Отчёт по чанкингу сохранён в: {output_file}")
    return str(output_path)


def generate_chunking_demo(
    chunks: List[Dict[str, Any]],
    processed_pages: List[Dict[str, Any]],
    output_file: str = "output_module_3/content_demonstrator.txt"
) -> str:
    """
    Генерирует демонстрационный файл с результатами чанкинга.

    Args:
        chunks: Список чанков с метаданными.
        processed_pages: Обработанные страницы с исходным текстом.
        output_file: Путь к файлу демонстрации.

    Returns:
        Путь к созданному файлу.
    """
    logger.info("Генерация демонстрации чанкинга")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write("# Демонстрация результатов Модуля 3: Гибридный чанкинг и метаданные\n\n")
        f.write(f"**Дата генерации:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # Часть 1: Исходный структурированный текст
        f.write("## Часть 1: Исходный структурированный текст\n\n")
        f.write("Текст после этапов 1-4 (извлечение, очистка, нормализация, структурирование):\n\n")

        for page in processed_pages:
            f.write(f"### Страница {page['page_number']}\n\n")

            structure = page["structure"]

            if structure.get("headings"):
                f.write("**Заголовки:**\n")
                for heading in structure["headings"]:
                    f.write(f"  - {heading}\n")
                f.write("\n")

            if structure.get("paragraphs"):
                f.write("**Абзацы:**\n")
                for i, paragraph in enumerate(structure["paragraphs"][:3], 1):
                    f.write(f"  {i}. {paragraph[:200]}{'...' if len(paragraph) > 200 else ''}\n")
                if len(structure["paragraphs"]) > 3:
                    f.write(f"  ... и ещё {len(structure['paragraphs']) - 3} абзац(ов)\n")
                f.write("\n")

            if structure.get("lists"):
                f.write("**Списки:**\n")
                for lst in structure["lists"]:
                    f.write(f"  - {len(lst)} элементов: {lst[0][:100]}{'...' if len(lst[0]) > 100 else ''}\n")
                f.write("\n")

            f.write("---\n\n")

        # Часть 2: Результаты чанкинга
        f.write("## Часть 2: Результаты чанкинга (Этапы 5-6)\n\n")
        f.write(f"Всего создано чанков: {len(chunks)}\n\n")
        f.write("---\n\n")

        # Группируем чанки по типам
        chunks_by_type = {}
        for chunk in chunks:
            chunk_type = chunk.get("type", "unknown")
            if chunk_type not in chunks_by_type:
                chunks_by_type[chunk_type] = []
            chunks_by_type[chunk_type].append(chunk)

        # Выводим чанки по типам
        for chunk_type in ["heading", "paragraph", "list", "list_item"]:
            if chunk_type in chunks_by_type:
                type_chunks = chunks_by_type[chunk_type]
                f.write(f"### Чанки типа: {chunk_type.upper()}\n\n")
                f.write(f"Количество: {len(type_chunks)}\n\n")

                for i, chunk in enumerate(type_chunks[:5], 1):  # Показываем первые 5
                    metadata = chunk.get("metadata", {})

                    f.write(f"#### Чанк {i}: {metadata.get('chunk_id', 'unknown')}\n\n")
                    f.write(f"**Метаданные:**\n")
                    f.write(f"- ID: {metadata.get('chunk_id', 'N/A')}\n")
                    f.write(f"- Тип: {metadata.get('chunk_type', 'N/A')}\n")
                    f.write(f"- Страница: {metadata.get('page_number', 'N/A')}\n")
                    f.write(f"- Символов: {metadata.get('char_count', 0)}\n")
                    f.write(f"- Слов: {metadata.get('word_count', 0)}\n")
                    f.write(f"- Время: {metadata.get('timestamp', 'N/A')}\n\n")

                    f.write(f"**Текст чанка:**\n")
                    f.write(f"```\n{chunk['text']}\n```\n\n")

                    f.write("---\n\n")

                if len(type_chunks) > 5:
                    f.write(f"... и ещё {len(type_chunks) - 5} чанк(ов) типа {chunk_type}\n\n")
                    f.write("---\n\n")

        # Часть 3: Примеры полных метаданных
        f.write("## Часть 3: Примеры полных метаданных\n\n")

        if chunks:
            # Показываем метаданные для первого чанка каждого типа
            for chunk_type in ["heading", "paragraph", "list"]:
                type_chunks = chunks_by_type.get(chunk_type)
                if type_chunks:
                    chunk = type_chunks[0]
                    metadata = chunk.get("metadata", {})

                    f.write(f"### Метаданные для чанка типа {chunk_type.upper()}\n\n")
                    f.write(f"**Текст:** {chunk['text'][:100]}{'...' if len(chunk['text']) > 100 else ''}\n\n")
                    f.write(f"**Метаданные:**\n")
                    f.write("```json\n")
                    f.write("{\n")
                    for key, value in metadata.items():
                        if isinstance(value, str):
                            f.write(f'  "{key}": "{value}",\n')
                        else:
                            f.write(f'  "{key}": {value},\n')
                    f.write("}\n")
                    f.write("```\n\n")
                    f.write("---\n\n")

        # Часть 4: Статистика
        f.write("## Часть 4: Статистика по чанкам\n\n")

        char_counts = [c.get("metadata", {}).get("char_count", 0) for c in chunks]
        word_counts = [c.get("metadata", {}).get("word_count", 0) for c in chunks]

        f.write("| Метрика | Значение |\n")
        f.write("|---------|----------|\n")
        f.write(f"| Всего чанков | {len(chunks)} |\n")
        f.write(f"| Всего символов | {sum(char_counts)} |\n")
        f.write(f"| Всего слов | {sum(word_counts)} |\n")
        f.write(f"| Средняя длина (символы) | {sum(char_counts) / len(char_counts) if char_counts else 0:.2f} |\n")
        f.write(f"| Минимальная длина (символы) | {min(char_counts) if char_counts else 0} |\n")
        f.write(f"| Максимальная длина (символы) | {max(char_counts) if char_counts else 0} |\n")
        f.write(f"| Средняя длина (слова) | {sum(word_counts) / len(word_counts) if word_counts else 0:.2f} |\n")
        f.write(f"| Минимальная длина (слова) | {min(word_counts) if word_counts else 0} |\n")
        f.write(f"| Максимальная длина (слова) | {max(word_counts) if word_counts else 0} |\n\n")

        f.write("---\n\n")

        # Часть 5: Распределение по типам
        f.write("## Часть 5: Распределение чанков по типам\n\n")

        f.write("| Тип | Количество | Процент |\n")
        f.write("|-----|-----------|----------|\n")
        for chunk_type, type_chunks in sorted(chunks_by_type.items()):
            count = len(type_chunks)
            percentage = (count / len(chunks) * 100) if chunks else 0
            f.write(f"| {chunk_type} | {count} | {percentage:.1f}% |\n")

        f.write("\n---\n\n")

        # Заключение
        f.write("## Заключение\n\n")
        f.write("Этот файл демонстрирует результаты работы Модуля 3 (гибридный чанкинг и метаданные).\n\n")
        f.write("**Этап 5:** Текст разбит на чанки с учётом семантической структуры и перекрытия.\n")
        f.write("**Этап 6:** Каждому чанку присвоены метаданные для использования в RAG-системах.\n\n")
        f.write("---\n\n")
        f.write(f"**Конец демонстрации**\n")

    logger.info(f"Демонстрация чанкинга сохранена в: {output_file}")
    return str(output_path)


def process_chunks(
    processed_pages: List[Dict[str, Any]],
    pdf_path: str,
    output_dir: str,
    max_chunk_size: int = 500,
    overlap: int = 50,
    generate_demo: bool = True
) -> Dict[str, Any]:
    """
    Полный цикл обработки чанков для всех страниц.

    Args:
        processed_pages: Обработанные страницы с результатами структурирования.
        pdf_path: Путь к исходному PDF-файлу.
        output_dir: Директория для сохранения результатов.
        max_chunk_size: Максимальный размер чанка.
        overlap: Перекрытие между чанками.
        generate_demo: Генерировать демонстрационный файл.

    Returns:
        Словарь с результатами обработки чанков.
    """
    logger.info("Начало обработки чанков для всех страниц")

    all_chunks = []
    all_validation_results = []

    for page in processed_pages:
        page_number = page["page_number"]
        structure = page["structure"]

        # Этап 5: Гибридный чанкинг
        chunks = hybrid_chunking(structure, max_chunk_size, overlap)

        # Этап 6: Добавление метаданных
        chunks_with_metadata = add_metadata(chunks, pdf_path, page_number)

        # Валидация
        validation = validate_chunks(chunks_with_metadata)

        all_chunks.extend(chunks_with_metadata)
        all_validation_results.append({
            "page_number": page_number,
            "validation": validation
        })

    # Агрегируем статистику по всем страницам
    aggregated_validation = {
        "stats": {
            "total_chunks": len(all_chunks),
            "total_chars": sum(v["validation"]["stats"]["total_chars"] for v in all_validation_results),
            "total_words": sum(v["validation"]["stats"]["total_words"] for v in all_validation_results),
            "avg_char_count": 0,
            "min_char_count": float('inf'),
            "max_char_count": 0,
            "avg_word_count": 0,
            "min_word_count": float('inf'),
            "max_word_count": 0
        },
        "empty_chunks": [],
        "too_short_chunks": [],
        "chunk_types": {}
    }

    # Агрегируем минимумы и максимумы
    for v in all_validation_results:
        stats = v["validation"]["stats"]
        if stats["min_char_count"] < aggregated_validation["stats"]["min_char_count"]:
            aggregated_validation["stats"]["min_char_count"] = stats["min_char_count"]
        if stats["max_char_count"] > aggregated_validation["stats"]["max_char_count"]:
            aggregated_validation["stats"]["max_char_count"] = stats["max_char_count"]
        if stats["min_word_count"] < aggregated_validation["stats"]["min_word_count"]:
            aggregated_validation["stats"]["min_word_count"] = stats["min_word_count"]
        if stats["max_word_count"] > aggregated_validation["stats"]["max_word_count"]:
            aggregated_validation["stats"]["max_word_count"] = stats["max_word_count"]

        # Собираем пустые и короткие чанки
        for idx in v["validation"]["empty_chunks"]:
            aggregated_validation["empty_chunks"].append(idx)
        for idx in v["validation"]["too_short_chunks"]:
            aggregated_validation["too_short_chunks"].append(idx)

        # Агрегируем типы чанков
        for chunk_type, count in v["validation"]["chunk_types"].items():
            if chunk_type not in aggregated_validation["chunk_types"]:
                aggregated_validation["chunk_types"][chunk_type] = 0
            aggregated_validation["chunk_types"][chunk_type] += count

    # Вычисляем средние значения
    if aggregated_validation["stats"]["total_chunks"] > 0:
        aggregated_validation["stats"]["avg_char_count"] = (
            aggregated_validation["stats"]["total_chars"] / aggregated_validation["stats"]["total_chunks"]
        )
        aggregated_validation["stats"]["avg_word_count"] = (
            aggregated_validation["stats"]["total_words"] / aggregated_validation["stats"]["total_chunks"]
        )

    # Генерация отчёта в output_module_3/
    report_path = Path("output_module_3") / "chunking_report.txt"
    generate_chunking_report(
        aggregated_validation,
        max_chunk_size,
        overlap,
        str(report_path)
    )

    # Генерация демонстрационного файла
    demo_path = None
    if generate_demo:
        demo_path = generate_chunking_demo(
            all_chunks,
            processed_pages,
            str(Path("output_module_3") / "content_demonstrator.txt")
        )

    logger.info("Обработка чанков завершена")

    result = {
        "chunks": all_chunks,
        "validation": all_validation_results,
        "report_path": str(report_path)
    }

    if demo_path:
        result["demo_path"] = demo_path

    return result
