"""
Модуль предобработки текста из PDF-файлов для RAG-пайплайна.

Реализует этапы: извлечение, очистка, нормализация, структурирование текста.
"""

import logging
import re
import os
from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Библиотеки для работы с PDF
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from pdf2image import convert_from_path
    import pytesseract
except ImportError:
    convert_from_path = None
    pytesseract = None

# Библиотеки для обработки текста
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

try:
    from unidecode import unidecode
except ImportError:
    unidecode = None

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы
ABBREVIATIONS = {
    "т.е.": "то есть",
    "и т.д.": "и так далее",
    "и т.п.": "и тому подобное",
    "т.к.": "так как",
    "т.обр.": "таким образом",
    "др.": "другие",
    "пр.": "пример",
    "см.": "смотри",
    "стр.": "страница",
    "гг.": "годы",
    "г.": "год",
    "вв.": "века",
    "в.": "век",
}

DATE_PATTERNS = [
    r'\d{1,2}\.\d{1,2}\.\d{2,4}',  # DD.MM.YYYY
    r'\d{2,4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
    r'\d{1,2}\s+[а-яА-ЯёЁ]+\s+\d{2,4}',  # DD Месяц YYYY
]


def extract_text_from_pdf(
    pdf_path: str,
    ocr_enabled: bool = False,
    ocr_lang: str = 'rus+eng'
) -> List[Dict[str, Any]]:
    """
    Извлекает текст из PDF-файла постранично.

    Args:
        pdf_path: Путь к PDF-файлу.
        ocr_enabled: Включить OCR для сканированных страниц.
        ocr_lang: Языки для OCR (по умолчанию 'rus+eng').

    Returns:
        Список словарей с текстом по страницам:
        [{"page_number": int, "text": str, "metadata": dict}]

    Raises:
        FileNotFoundError: Если файл не существует.
        ValueError: Если файл не является PDF.
        Exception: При ошибках извлечения текста.
    """
    logger.info(f"[Этап 1] Начало извлечения текста из: {pdf_path}")

    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"Файл не найден: {pdf_path}")

    if pdf_path_obj.suffix.lower() != '.pdf':
        raise ValueError(f"Файл не является PDF: {pdf_path}")

    pages_data: List[Dict[str, Any]] = []
    ocr_pages: List[int] = []

    # Проверяем наличие pypdf
    if pypdf is None:
        logger.error("Библиотека pypdf не установлена. Выполните: pip install pypdf")
        raise ImportError("Библиотека pypdf не установлена")

    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            logger.info(f"Всего страниц в PDF: {num_pages}")

            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()

                metadata = {
                    "source": pdf_path,
                    "page_number": page_num + 1,
                    "ocr_applied": False
                }

                # Если текст не извлечён или пустой, пробуем OCR
                if not text or len(text.strip()) < 10:
                    if ocr_enabled:
                        logger.warning(f"Текст на странице {page_num + 1} не найден, применяем OCR")
                        text = _apply_ocr(pdf_path, page_num, ocr_lang)
                        metadata["ocr_applied"] = True
                        ocr_pages.append(page_num + 1)
                    else:
                        logger.warning(f"Текст на странице {page_num + 1} не найден, OCR отключён")
                        text = ""

                pages_data.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "metadata": metadata
                })

        logger.info(f"[Этап 1] Успешно извлечено страниц: {len(pages_data)}")
        if ocr_pages:
            logger.info(f"[Этап 1] OCR применён на страницах: {ocr_pages}")

        return pages_data

    except Exception as e:
        logger.error(f"Ошибка при извлечении текста из PDF: {e}")
        raise


def _apply_ocr(pdf_path: str, page_num: int, ocr_lang: str) -> str:
    """
    Применяет OCR к указанной странице PDF.

    Args:
        pdf_path: Путь к PDF-файлу.
        page_num: Номер страницы (0-based).
        ocr_lang: Языки для OCR.

    Returns:
        Извлечённый текст.

    Raises:
        ImportError: Если необходимые библиотеки не установлены.
    """
    if convert_from_path is None or pytesseract is None:
        raise ImportError(
            "Для OCR необходимы библиотеки pdf2image и pytesseract. "
            "Выполните: pip install pdf2image pytesseract"
        )

    try:
        # Конвертируем страницу в изображение
        images = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1)
        if not images:
            logger.warning(f"Не удалось конвертировать страницу {page_num + 1} в изображение")
            return ""

        # Применяем OCR
        text = pytesseract.image_to_string(images[0], lang=ocr_lang)
        logger.debug(f"OCR на странице {page_num + 1}: извлечено {len(text)} символов")

        return text

    except Exception as e:
        logger.error(f"Ошибка при применении OCR на странице {page_num + 1}: {e}")
        return ""


def clean_text(
    raw_text: str,
    remove_html: bool = True,
    normalize_whitespace: bool = True,
    preserve_structure: bool = False,
    return_stats: bool = False
) -> str | tuple:
    """
    Очищает текст от HTML-тегов, навигационных элементов и лишних пробелов.

    Args:
        raw_text: Исходный текст для очистки.
        remove_html: Удалять HTML-теги.
        normalize_whitespace: Нормализовать пробелы.
        preserve_structure: Сохранять структуру (переносы строк) для последующего структурирования.
        return_stats: Возвращать статистику очистки вместе с текстом.

    Returns:
        Очищенный текст или кортеж (текст, статистика).
    """
    if not raw_text:
        if return_stats:
            return "", {"tags_removed": 0, "whitespace_collapsed": 0, "control_chars_removed": 0, "duplicates_removed": 0}
        return ""

    logger.debug("[Этап 2] Начало очистки текста")

    cleaned = raw_text
    stats = {"tags_removed": 0, "whitespace_collapsed": 0, "control_chars_removed": 0, "duplicates_removed": 0}

    # 1. Удаление HTML-тегов (используем regex для подсчёта)
    if remove_html:
        # Сначала считаем количество HTML тегов через regex
        html_tags = re.findall(r'<[^>]+>', cleaned)
        stats["tags_removed"] = len(html_tags)

        # Теперь удаляем теги
        if BeautifulSoup:
            soup = BeautifulSoup(cleaned, 'html.parser')
            cleaned = soup.get_text(separator=' ')
        else:
            # Если BeautifulSoup недоступен, используем regex
            cleaned = re.sub(r'<[^>]+>', ' ', cleaned)

    # 2. Удаление навигационных элементов (повторяющиеся строки)
    lines = cleaned.split('\n')
    line_counts = {}
    for line in lines:
        line_stripped = line.strip()
        if line_stripped:
            line_counts[line_stripped] = line_counts.get(line_stripped, 0) + 1

    # Если строка повторяется много раз, удаляем её
    filtered_lines = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_counts.get(line_stripped, 0) > 3:
            # Пропускаем слишком часто повторяющиеся строки
            stats["duplicates_removed"] += 1
            continue
        filtered_lines.append(line)

    cleaned = '\n'.join(filtered_lines)

    # 3. Удаление пустых строк и лишних переносов
    # Считаем количество схлопнутых пробелов и табуляций
    spaces_before = len(re.findall(r'[ \t]+', cleaned))
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Табы и множественные пробелы
    spaces_after = len(re.findall(r'[ \t]+', cleaned))
    stats["whitespace_collapsed"] += spaces_before - spaces_after

    # Считаем количество схлопнутых пустых строк
    empty_lines_before = len(re.findall(r'\n\s*\n', cleaned))
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)  # Множественные пустые строки
    empty_lines_after = len(re.findall(r'\n\s*\n', cleaned))
    stats["whitespace_collapsed"] += empty_lines_before - empty_lines_after

    # 4. Нормализация пробелов (только если не нужно сохранять структуру)
    if normalize_whitespace and not preserve_structure:
        before_len = len(cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        stats["whitespace_collapsed"] += before_len - len(cleaned)

    # 5. Удаление ASCII control chars (кроме \n, \r, \t)
    control_chars_before = len(re.findall(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', cleaned))
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
    control_chars_after = len(re.findall(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', cleaned))
    stats["control_chars_removed"] = control_chars_before - control_chars_after

    logger.debug(f"[Этап 2] Удалено тегов: {stats['tags_removed']}, схлопнуто пробелов: {stats['whitespace_collapsed']}, "
                 f"удалено управляющих символов: {stats['control_chars_removed']}, удалено дубликатов: {stats['duplicates_removed']}")

    if return_stats:
        return cleaned, stats
    return cleaned


def normalize_text(
    cleaned_text: str,
    lower: bool = True,
    expand_abbr: bool = True,
    standardize_dates: bool = True,
    preserve_structure: bool = True,
    return_stats: bool = False
) -> str | tuple:
    """
    Нормализует текст: регистр, сокращения, даты.

    Args:
        cleaned_text: Очищенный текст.
        lower: Привести к нижнему регистру.
        expand_abbr: Расширять сокращения.
        standardize_dates: Стандартизировать даты в ISO формат.
        preserve_structure: Сохранять структуру (переносы строк).
        return_stats: Возвращать статистику нормализации вместе с текстом.

    Returns:
        Нормализованный текст или кортеж (текст, статистика).
    """
    if not cleaned_text:
        if return_stats:
            return cleaned_text, {"abbr_expanded": 0, "dates_standardized": 0}
        return cleaned_text

    logger.debug("[Этап 3] Начало нормализации текста")

    normalized = cleaned_text
    stats = {"abbr_expanded": 0, "dates_standardized": 0}

    # Если нужно сохранить структуру, разбиваем на строки
    if preserve_structure:
        lines = normalized.split('\n')
        normalized_lines = []

        for line in lines:
            normalized_line = line

            # 1. Приведение к нижнему регистру (по строкам)
            if lower:
                normalized_line = normalized_line.lower()

            # 2. Замена сокращений (по строкам)
            if expand_abbr:
                for abbr, expansion in ABBREVIATIONS.items():
                    count = normalized_line.count(abbr)
                    if count > 0:
                        normalized_line = normalized_line.replace(abbr, expansion)
                        stats["abbr_expanded"] += count

            # 3. Стандартизация дат (по строкам)
            if standardize_dates and date_parser:
                for pattern in DATE_PATTERNS:
                    matches = re.finditer(pattern, normalized_line)
                    for match in matches:
                        date_str = match.group()
                        try:
                            parsed_date = date_parser.parse(date_str, fuzzy=True, dayfirst=True)
                            iso_date = parsed_date.strftime('%Y-%m-%d')
                            normalized_line = normalized_line.replace(date_str, iso_date, 1)
                            stats["dates_standardized"] += 1
                        except:
                            pass

            # 4. Удаление множественных точек и дефисов
            normalized_line = re.sub(r'\.{2,}', '...', normalized_line)
            normalized_line = re.sub(r'-{2,}', '—', normalized_line)

            normalized_lines.append(normalized_line)

        normalized = '\n'.join(normalized_lines)
    else:
        # Обработка как одного блока текста (старый вариант)
        if lower:
            normalized = normalized.lower()

        if expand_abbr:
            for abbr, expansion in ABBREVIATIONS.items():
                count = normalized.count(abbr)
                if count > 0:
                    normalized = normalized.replace(abbr, expansion)
                    stats["abbr_expanded"] += count

        if standardize_dates and date_parser:
            for pattern in DATE_PATTERNS:
                matches = re.finditer(pattern, normalized)
                for match in matches:
                    date_str = match.group()
                    try:
                        parsed_date = date_parser.parse(date_str, fuzzy=True, dayfirst=True)
                        iso_date = parsed_date.strftime('%Y-%m-%d')
                        normalized = normalized.replace(date_str, iso_date, 1)
                        stats["dates_standardized"] += 1
                    except:
                        pass

        normalized = re.sub(r'\.{2,}', '...', normalized)
        normalized = re.sub(r'-{2,}', '—', normalized)

    logger.debug(f"[Этап 3] Заменено сокращений: {stats['abbr_expanded']}, стандартизировано дат: {stats['dates_standardized']}")

    if return_stats:
        return normalized, stats
    return normalized


def structure_text(normalized_text: str) -> Dict[str, Any]:
    """
    Структурирует текст: выделяет заголовки, абзацы, списки, FAQ.

    Args:
        normalized_text: Нормализованный текст.

    Returns:
        Словарь со структурой текста.
    """
    logger.debug("[Этап 4] Начало структурирования текста")

    result: Dict[str, Any] = {
        "title": None,
        "headings": [],
        "paragraphs": [],
        "lists": [],
        "metadata": {
            "has_questions": False,
            "structure_type": "article"
        }
    }

    # Разбиваем текст на строки
    lines = normalized_text.split('\n')

    # Паттерны для распознавания
    heading_patterns = [
        r'^#{1,6}\s+.+',  # Markdown заголовки
        r'^[А-ЯA-Z][^.]+:$',  # Строка с двоеточием в конце
        r'^[А-ЯЁA-Z][а-яёa-z\s]{5,50}$',  # Короткие строки без точки
    ]

    list_patterns = [
        r'^[-*•]\s+.+',  # Маркированный список
        r'^\d+[.)]\s+.+',  # Нумерованный список
    ]

    faq_patterns = [
        r'^(вопрос|quest|q)[:\s]+.*\?',
        r'^(ответ|answer|a)[:\s]+',
    ]

    current_paragraph: List[str] = []
    current_list: List[str] = []
    in_list = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Проверяем на заголовок
        is_heading = False
        for pattern in heading_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                # Сохраняем текущий абзац если есть
                if current_paragraph:
                    result["paragraphs"].append(' '.join(current_paragraph))
                    current_paragraph = []

                # Сохраняем список если был
                if in_list and current_list:
                    result["lists"].append(current_list)
                    current_list = []
                    in_list = False

                # Сохраняем заголовок
                if not result["title"]:
                    result["title"] = line
                result["headings"].append(line)
                is_heading = True
                break

        if is_heading:
            continue

        # Проверяем на FAQ маркеры
        for pattern in faq_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                result["metadata"]["has_questions"] = True
                result["metadata"]["structure_type"] = "faq"
                break

        # Проверяем на список
        is_list_item = False
        for pattern in list_patterns:
            if re.match(pattern, line):
                is_list_item = True
                # Сохраняем текущий абзац если есть
                if current_paragraph:
                    result["paragraphs"].append(' '.join(current_paragraph))
                    current_paragraph = []

                # Добавляем в текущий список
                current_list.append(line)
                in_list = True
                break

        if is_list_item:
            continue

        # Если это не список, сохраняем список если был
        if in_list and current_list:
            result["lists"].append(current_list)
            current_list = []
            in_list = False

        # Добавляем в абзац
        current_paragraph.append(line)

    # Сохраняем последние данные
    if current_paragraph:
        result["paragraphs"].append(' '.join(current_paragraph))
    if in_list and current_list:
        result["lists"].append(current_list)

    # Определяем тип структуры
    if result["lists"] and not result["headings"]:
        result["metadata"]["structure_type"] = "list"
    elif result["headings"] and result["paragraphs"]:
        result["metadata"]["structure_type"] = "article"
    elif result["metadata"]["has_questions"]:
        result["metadata"]["structure_type"] = "faq"
    elif result["headings"] and result["lists"]:
        result["metadata"]["structure_type"] = "mixed"

    logger.debug(f"[Этап 4] Найдено заголовков: {len(result['headings'])}, "
                 f"абзацев: {len(result['paragraphs'])}, списков: {len(result['lists'])}")

    return result


def generate_transformation_demo(
    processed_pages: List[Dict],
    output_file: str = "output_module_2/transformation_demo.txt"
) -> str:
    """
    Генерирует демонстрацию трансформации текста на каждом этапе обработки.

    Args:
        processed_pages: Обработанные страницы с результатами всех этапов.
        output_file: Путь к файлу с демонстрацией.

    Returns:
        Путь к созданному файлу.
    """
    logger.info("Генерация демонстрации трансформации текста")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write("# Демонстрация трансформации текста\n\n")
        f.write(f"**Дата генерации:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Обработано страниц:** {len(processed_pages)}\n\n")
        f.write("=" * 80 + "\n\n")

        for page in processed_pages:
            page_num = page["page_number"]
            f.write(f"## Страница {page_num}\n\n")

            # Этап 1: Исходный текст (извлечённый из PDF)
            f.write("### Этап 1: Извлечение текста из PDF\n\n")
            raw_text = page.get("raw_text", page.get("cleaned_text", ""))
            preview = raw_text[:1000] if raw_text else ""
            f.write(f"**Длина текста:** {len(raw_text)} символов\n\n")
            f.write("**Первые 1000 символов:**\n")
            f.write("```\n")
            f.write(preview)
            f.write("\n```\n\n")

            # Этап 2: Очистка
            f.write("### Этап 2: Очистка текста\n\n")
            cleaned_text = page.get("cleaned_text", "")
            preview_cleaned = cleaned_text[:1000] if cleaned_text else ""
            f.write(f"**Длина после очистки:** {len(cleaned_text)} символов\n")
            f.write(f"**Изменение длины:** {len(cleaned_text) - len(raw_text)} символов\n\n")
            f.write("**Первые 1000 символов:**\n")
            f.write("```\n")
            f.write(preview_cleaned)
            f.write("\n```\n\n")

            # Этап 3: Нормализация
            f.write("### Этап 3: Нормализация текста\n\n")
            normalized_text = page.get("normalized_text", "")
            preview_normalized = normalized_text[:1000] if normalized_text else ""
            f.write(f"**Длина после нормализации:** {len(normalized_text)} символов\n")
            f.write(f"**Изменение длины:** {len(normalized_text) - len(cleaned_text)} символов\n\n")
            f.write("**Первые 1000 символов:**\n")
            f.write("```\n")
            f.write(preview_normalized)
            f.write("\n```\n\n")

            # Этап 4: Структурирование
            f.write("### Этап 4: Структурирование текста\n\n")
            structure = page.get("structure", {})
            f.write(f"**Тип структуры:** {structure.get('metadata', {}).get('structure_type', 'unknown')}\n")
            f.write(f"**Найдено заголовков:** {len(structure.get('headings', []))}\n")
            f.write(f"**Найдено абзацев:** {len(structure.get('paragraphs', []))}\n")
            f.write(f"**Найдено списков:** {len(structure.get('lists', []))}\n")
            f.write(f"**Найдено FAQ-блоков:** {structure.get('metadata', {}).get('has_questions', False)}\n\n")

            # Заголовки
            if structure.get('headings'):
                f.write("**Заголовки:**\n")
                for i, heading in enumerate(structure['headings'][:10], 1):
                    f.write(f"{i}. {heading}\n")
                if len(structure['headings']) > 10:
                    f.write(f"... и ещё {len(structure['headings']) - 10}\n")
                f.write("\n")

            # Абзацы
            if structure.get('paragraphs'):
                f.write("**Абзацы (первые 3):**\n")
                for i, para in enumerate(structure['paragraphs'][:3], 1):
                    f.write(f"{i}. {para[:100]}...\n")
                f.write("\n")

            # Списки
            if structure.get('lists'):
                f.write("**Списки:**\n")
                for i, lst in enumerate(structure['lists'], 1):
                    f.write(f"Список {i} ({len(lst)} элементов):\n")
                    for item in lst[:5]:
                        f.write(f"  - {item}\n")
                    if len(lst) > 5:
                        f.write(f"  ... и ещё {len(lst) - 5}\n")
                    f.write("\n")

            f.write("-" * 80 + "\n\n")

    logger.info(f"Демонстрация трансформации сохранена в: {output_file}")
    return str(output_path)


def generate_report(
    pages_data: List[Dict],
    output_file: str = "output_module_2/report.txt",
    processed_pages: List[Dict] = None,
    cleaning_stats: Dict = None,
    normalization_stats: Dict = None
) -> Dict[str, Any]:
    """
    Генерирует отчёт по этапам обработки.

    Args:
        pages_data: Данные по страницам с результатами обработки (извлечённые).
        output_file: Путь к файлу отчёта.
        processed_pages: Обработанные страницы с результатами структурирования (опционально).
        cleaning_stats: Статистика по очистке (опционально).
        normalization_stats: Статистика по нормализации (опционально).

    Returns:
        Словарь со статистикой обработки.
    """
    logger.info("Генерация отчёта по обработке")

    stats = {
        "extraction": {
            "source": "",
            "total_pages": len(pages_data),
            "ocr_pages": [],
            "sample_text": ""
        },
        "cleaning": {
            "tags_removed": 0,
            "whitespace_collapsed": 0,
            "control_chars_removed": 0,
            "duplicates_removed": 0
        },
        "normalization": {
            "abbr_expanded": 0,
            "dates_standardized": 0
        },
        "structuring": {
            "headings": 0,
            "paragraphs": 0,
            "lists": 0,
            "faq_blocks": 0
        }
    }

    # Собираем статистику извлечения
    if pages_data:
        stats["extraction"]["source"] = pages_data[0]["metadata"]["source"]
        stats["extraction"]["ocr_pages"] = [
            p["page_number"] for p in pages_data
            if p["metadata"].get("ocr_applied", False)
        ]
        # Пример текста с первой страницы
        first_page_text = pages_data[0].get("text", "")
        if first_page_text:
            stats["extraction"]["sample_text"] = first_page_text[:100] + "..."

    # Обновляем статистику очистки
    if cleaning_stats:
        stats["cleaning"]["tags_removed"] = cleaning_stats.get("tags_removed", 0)
        stats["cleaning"]["whitespace_collapsed"] = cleaning_stats.get("whitespace_collapsed", 0)
        stats["cleaning"]["control_chars_removed"] = cleaning_stats.get("control_chars_removed", 0)
        stats["cleaning"]["duplicates_removed"] = cleaning_stats.get("duplicates_removed", 0)

    # Обновляем статистику нормализации
    if normalization_stats:
        stats["normalization"]["abbr_expanded"] = normalization_stats.get("abbr_expanded", 0)
        stats["normalization"]["dates_standardized"] = normalization_stats.get("dates_standardized", 0)

    # Собираем статистику структурирования из обработанных страниц
    if processed_pages:
        for page in processed_pages:
            structure = page.get("structure", {})
            stats["structuring"]["headings"] += len(structure.get("headings", []))
            stats["structuring"]["paragraphs"] += len(structure.get("paragraphs", []))
            stats["structuring"]["lists"] += len(structure.get("lists", []))
            if structure.get("metadata", {}).get("has_questions", False):
                stats["structuring"]["faq_blocks"] += 1

    # Вывод в консоль (с обработкой ошибок кодировки)
    try:
        print("\n" + "=" * 60)
        print("[Этап 1: Извлечение текста]")
        print(f"Источник: {stats['extraction']['source']}")
        print(f"Извлечено страниц: {stats['extraction']['total_pages']}")
        if stats['extraction']['ocr_pages']:
            print(f"OCR применялся: Да (страницы {', '.join(map(str, stats['extraction']['ocr_pages']))})")
        else:
            print(f"OCR применялся: Нет")
        if stats['extraction']['sample_text']:
            print(f"Пример текста (стр 1): \"{stats['extraction']['sample_text']}\"")

        print("\n[Этап 2: Очистка]")
        print(f"Удалено тегов: {stats['cleaning']['tags_removed']}")
        print(f"Схлопнуто пробелов: {stats['cleaning']['whitespace_collapsed']}")
        print(f"Удалено управляющих символов: {stats['cleaning']['control_chars_removed']}")
        print(f"Удалено дубликатов строк: {stats['cleaning']['duplicates_removed']}")

        print("\n[Этап 3: Нормализация]")
        print(f"Заменено сокращений: {stats['normalization']['abbr_expanded']}")
        print(f"Стандартизировано дат: {stats['normalization']['dates_standardized']}")

        print("\n[Этап 4: Структурирование]")
        print(f"Найдено заголовков: {stats['structuring']['headings']}")
        print(f"Абзацев: {stats['structuring']['paragraphs']}")
        print(f"Списков: {stats['structuring']['lists']}")
        print(f"FAQ-блоков: {stats['structuring']['faq_blocks']}")
        print("=" * 60 + "\n")
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        # Если возникла ошибка кодировки, выводим через логгер
        logger.warning(f"Не удалось вывести отчёт в консоль из-за ошибки кодировки: {e}")
        logger.info("=" * 60)
        logger.info("[Этап 1: Извлечение текста]")
        logger.info(f"Источник: {stats['extraction']['source']}")
        logger.info(f"Извлечено страниц: {stats['extraction']['total_pages']}")
        logger.info(f"OCR: {'Да' if stats['extraction']['ocr_pages'] else 'Нет'}")
        logger.info("[Этап 2: Очистка]")
        logger.info(f"Удалено тегов: {stats['cleaning']['tags_removed']}")
        logger.info(f"Схлопнуто пробелов: {stats['cleaning']['whitespace_collapsed']}")
        logger.info(f"Удалено управляющих символов: {stats['cleaning']['control_chars_removed']}")
        logger.info(f"Удалено дубликатов строк: {stats['cleaning']['duplicates_removed']}")
        logger.info("[Этап 3: Нормализация]")
        logger.info(f"Заменено сокращений: {stats['normalization']['abbr_expanded']}")
        logger.info(f"Стандартизировано дат: {stats['normalization']['dates_standardized']}")
        logger.info("[Этап 4: Структурирование]")
        logger.info(f"Найдено заголовков: {stats['structuring']['headings']}")
        logger.info(f"Абзацев: {stats['structuring']['paragraphs']}")
        logger.info(f"Списков: {stats['structuring']['lists']}")
        logger.info(f"FAQ-блоков: {stats['structuring']['faq_blocks']}")
        logger.info("=" * 60)

    # Запись в файл (Markdown)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write("# Отчёт по обработке PDF\n\n")
        f.write(f"**Дата генерации:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Этап 1: Извлечение текста\n\n")
        f.write(f"- **Источник:** `{stats['extraction']['source']}`\n")
        f.write(f"- **Извлечено страниц:** {stats['extraction']['total_pages']}\n")
        if stats['extraction']['ocr_pages']:
            f.write(f"- **OCR:** страницы {', '.join(map(str, stats['extraction']['ocr_pages']))}\n")
        else:
            f.write(f"- **OCR:** не применялся\n")
        if stats['extraction']['sample_text']:
            f.write(f"- **Фрагмент:** `{stats['extraction']['sample_text']}`\n")

        f.write("\n## Этап 2: Очистка\n\n")
        f.write(f"- Удалено тегов: {stats['cleaning']['tags_removed']}\n")
        f.write(f"- Схлопнуто пробелов: {stats['cleaning']['whitespace_collapsed']}\n")
        f.write(f"- Удалено управляющих символов: {stats['cleaning']['control_chars_removed']}\n")
        f.write(f"- Удалено дубликатов строк: {stats['cleaning']['duplicates_removed']}\n")

        f.write("\n## Этап 3: Нормализация\n\n")
        f.write(f"- Заменено сокращений: {stats['normalization']['abbr_expanded']}\n")
        f.write(f"- Стандартизировано дат: {stats['normalization']['dates_standardized']}\n")

        f.write("\n## Этап 4: Структурирование\n\n")
        f.write(f"- Найдено заголовков: {stats['structuring']['headings']}\n")
        f.write(f"- Абзацев: {stats['structuring']['paragraphs']}\n")
        f.write(f"- Списков: {stats['structuring']['lists']}\n")
        f.write(f"- FAQ-блоков: {stats['structuring']['faq_blocks']}\n")

    logger.info(f"Отчёт сохранён в: {output_file}")

    return stats


def process_pdf(
    pdf_path: str,
    output_dir: str,
    ocr_enabled: bool = False,
    ocr_lang: str = 'rus+eng',
    generate_demo: bool = True,
    enable_chunking: bool = False,
    max_chunk_size: int = 500,
    overlap: int = 50,
    enable_vectorization: bool = False,
    embedding_model: str = "text-embedding-3-small",
    vector_db_type: str = "faiss",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    use_llm: bool = True,
    llm_model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Полный цикл обработки PDF-файла.

    Args:
        pdf_path: Путь к PDF-файлу.
        output_dir: Директория для сохранения результатов.
        ocr_enabled: Включить OCR.
        ocr_lang: Языки для OCR.
        generate_demo: Генерировать файл с демонстрацией трансформации.
        enable_chunking: Включить этапы 5-6 (чанкинг и метаданные).
        max_chunk_size: Максимальный размер чанка (если enable_chunking=True).
        overlap: Перекрытие между чанками (если enable_chunking=True).
        enable_vectorization: Включить этапы 7-8 (векторизация и БД).
        embedding_model: Модель эмбеддингов (если enable_vectorization=True).
        vector_db_type: Тип векторной БД (если enable_vectorization=True).
        api_key: API ключ OpenAI (также используется для LLM если не задан отдельно).
        api_base: Базовый URL API.
        use_llm: Использовать LLM для обогащения метаданных чанков (по умолчанию True).
        llm_model: Модель LLM для обогащения (по умолчанию: gpt-4o-mini).

    Returns:
        Словарь с результатами обработки.
    """
    logger.info(f"Начало обработки файла: {pdf_path}")

    # Этап 1: Извлечение
    pages_data = extract_text_from_pdf(pdf_path, ocr_enabled, ocr_lang)

    # Обрабатываем каждую страницу
    processed_pages = []
    all_structures = []
    cleaning_stats = {"tags_removed": 0, "whitespace_collapsed": 0, "control_chars_removed": 0, "duplicates_removed": 0}
    normalization_stats = {"abbr_expanded": 0, "dates_standardized": 0}

    for page_data in pages_data:
        # Сохраняем исходный текст для демонстрации
        raw_text = page_data["text"]

        # Этап 2: Очистка (сохраняем структуру для последующего структурирования)
        cleaned, clean_stats = clean_text(page_data["text"], preserve_structure=True, return_stats=True)
        cleaning_stats["tags_removed"] += clean_stats["tags_removed"]
        cleaning_stats["whitespace_collapsed"] += clean_stats["whitespace_collapsed"]
        cleaning_stats["control_chars_removed"] += clean_stats["control_chars_removed"]
        cleaning_stats["duplicates_removed"] += clean_stats["duplicates_removed"]

        # Этап 3: Нормализация (сохраняем структуру для структурирования)
        normalized, norm_stats = normalize_text(cleaned, preserve_structure=True, return_stats=True)
        normalization_stats["abbr_expanded"] += norm_stats["abbr_expanded"]
        normalization_stats["dates_standardized"] += norm_stats["dates_standardized"]

        # Этап 4: Структурирование
        structure = structure_text(normalized)

        processed_pages.append({
            "page_number": page_data["page_number"],
            "raw_text": raw_text,  # Сохраняем исходный текст
            "cleaned_text": cleaned,
            "normalized_text": normalized,
            "structure": structure
        })
        all_structures.append(structure)

    # Генерация отчёта
    report_path = Path(output_dir) / "report.txt"
    stats = generate_report(
        pages_data,
        str(report_path),
        processed_pages,
        cleaning_stats,
        normalization_stats
    )

    # Генерация демонстрации трансформации
    demo_path = None
    if generate_demo:
        demo_path = generate_transformation_demo(processed_pages, str(Path(output_dir) / "transformation_demo.txt"))

    # Этапы 5-6: Чанкинг и метаданные (если включено)
    chunking_result = None
    chunks = []

    if enable_chunking:
        try:
            if use_llm:
                # Используем LLM-усиленный чанкер
                from src.llm_chunker import process_chunks_with_llm
                chunking_result = process_chunks_with_llm(
                    processed_pages,
                    pdf_path,
                    output_dir,
                    max_chunk_size,
                    overlap,
                    use_llm=True,
                    llm_api_key=api_key,
                    llm_model=llm_model,
                    llm_api_base=api_base,
                    generate_demo=generate_demo
                )
                logger.info(f"LLM-усиленный чанкинг ({llm_model}) завершён: {len(chunking_result.get('chunks', []))} чанков")
            else:
                # Используем классический чанкер
                from src.chunker import process_chunks
                chunking_result = process_chunks(
                    processed_pages,
                    pdf_path,
                    output_dir,
                    max_chunk_size,
                    overlap,
                    generate_demo=generate_demo
                )
                logger.info(f"Классический чанкинг завершён: {len(chunking_result.get('chunks', []))} чанков")
            
            chunks = chunking_result.get("chunks", [])
            
        except ImportError as e:
            logger.warning(f"Модуль чанкера не найден: {e}, чанкинг пропущен")
        except Exception as e:
            logger.error(f"Ошибка при чанкинге: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Этапы 7-8: Векторизация и БД (если включено)
    vectorization_result = None

    if enable_vectorization:
        if not chunks:
            logger.warning("Векторизация включена, но чанки не созданы. Векторизация пропущена.")
        else:
            try:
                from src.vectorizer import process_vectorization
                vectorization_result = process_vectorization(
                    chunks,
                    output_dir=output_dir,
                    model_name=embedding_model,
                    db_type=vector_db_type,
                    api_key=api_key,
                    api_base=api_base
                )
                logger.info("Векторизация завершена")
            except ImportError:
                logger.warning("Модуль vectorizer не найден, векторизация пропущена")
            except Exception as e:
                logger.error(f"Ошибка при векторизации: {e}")
                import traceback
                logger.error(traceback.format_exc())

    logger.info(f"Обработка файла завершена: {pdf_path}")

    result = {
        "pages": processed_pages,
        "stats": stats,
        "report_path": str(report_path),
        "demo_path": demo_path
    }

    if chunking_result:
        result["chunks"] = chunking_result["chunks"]
        result["chunking_validation"] = chunking_result["validation"]
        result["chunking_report_path"] = chunking_result["report_path"]
        if "demo_path" in chunking_result:
            result["chunking_demo_path"] = chunking_result["demo_path"]

    if vectorization_result:
        result["vectorization"] = vectorization_result

    return result
