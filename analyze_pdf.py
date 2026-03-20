#!/usr/bin/env python3
"""
CLI утилита для анализа PDF перед обработкой.

Usage:
    python analyze_pdf.py <pdf_file>
    python analyze_pdf.py <pdf_file> --sample 10
    python analyze_pdf.py <pdf_file> --recommend-only
"""

import sys
import argparse
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_analyzer import analyze_pdf, print_analysis


def main():
    parser = argparse.ArgumentParser(
        description="Анализ PDF и рекомендации по обработке"
    )
    parser.add_argument("pdf_file", help="Путь к PDF файлу")
    parser.add_argument(
        "--sample", 
        type=int, 
        default=5,
        help="Количество страниц для анализа (0 = все)"
    )
    parser.add_argument(
        "--recommend-only",
        action="store_true",
        help="Показать только рекомендации"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вывод в JSON формате"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Отключить LLM-анализ"
    )
    
    args = parser.parse_args()
    
    # Проверяем файл
    if not Path(args.pdf_file).exists():
        print(f"Error: File not found: {args.pdf_file}")
        sys.exit(1)
    
    # Анализируем
    use_llm = not args.no_llm
    analysis = analyze_pdf(
        args.pdf_file, 
        sample_pages=args.sample,
        use_llm=use_llm
    )
    
    # Выводим
    if args.json:
        import json
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    else:
        if args.recommend_only:
            rec = analysis.get("recommendations", {})
            print("REKOMENDACII:")
            print(f"  chunk_size: {rec.get('chunk_size')}")
            print(f"  overlap: {rec.get('overlap')}")
            print(f"  chunking_strategy: {rec.get('chunking_strategy')}")
            print(f"  ocr_enabled: {rec.get('ocr_enabled')}")
            print(f"  llm_enabled: {rec.get('llm_enabled')}")
        else:
            print_analysis(analysis)


if __name__ == "__main__":
    main()
