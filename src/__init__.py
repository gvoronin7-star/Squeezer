"""
Пакет src для модулей проекта "Соковыжималка".
"""

from .preprocessor import (
    extract_text_from_pdf,
    clean_text,
    normalize_text,
    structure_text,
    generate_report,
    generate_transformation_demo,
    process_pdf
)

from .ui.pdf_loader import PDFLoader, PDFLoaderUI

__all__ = [
    # Модуль 2: Извлечение и предобработка текста
    'extract_text_from_pdf',
    'clean_text',
    'normalize_text',
    'structure_text',
    'generate_report',
    'generate_transformation_demo',
    'process_pdf',
    # Модуль 2.1: Пользовательский интерфейс для загрузки PDF
    'PDFLoader',
    'PDFLoaderUI'
]
