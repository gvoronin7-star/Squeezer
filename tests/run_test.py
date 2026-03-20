#!/usr/bin/env python3
"""Тестовый запуск полного цикла обработки PDF"""

import sys
sys.path.insert(0, '.')

from src.preprocessor import process_pdf

result = process_pdf(
    'pdfs/test_document.pdf',
    'output_full/',
    ocr_enabled=True,
    ocr_lang='rus+eng',
    enable_chunking=True,
    max_chunk_size=500,
    overlap=50,
    generate_demo=True
)

print('=' * 60)
print('Обработка завершена!')
print(f'Страниц обработано: {len(result["pages"])}')

if 'chunks' in result:
    print(f'Создано чанков: {len(result["chunks"])}')
    
print(f'Отчёт: {result["report_path"]}')
if result.get('chunking_report_path'):
    print(f'Отчёт по чанкингу: {result["chunking_report_path"]}')
print('=' * 60)
