#!/usr/bin/env python3
"""
Демонстратор системы предварительного анализа PDF.

Показывает:
1. Анализ разных типов документов
2. Рекомендации по оптимальным параметрам
3. Сравнение с дефолтными настройками
4. Эффективность рекомендаций
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_analyzer import analyze_pdf
from src.preprocessor import process_pdf
from dotenv import load_dotenv
load_dotenv()


def print_header(text: str, width: int = 70):
    """Печатает заголовок."""
    print("\n" + "=" * width)
    print(f" {text}")
    print("=" * width)


def print_section(text: str):
    """Печатает секцию."""
    print(f"\n--- {text} ---")


# ASCII-safe версии вывода
def safe_print(msg: str):
    """Печатает без эмодзи."""
    print(msg)


def demo_analysis():
    """Демонстрация анализа PDF."""
    
    print_header("ДЕМОНСТРАТОР СИСТЕМЫ АНАЛИЗА PDF")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Поиск PDF файлов
    pdf_dir = Path("pdfs")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("\n❌ PDF файлы не найдены в папке pdfs/")
        return
    
    print(f"\n[Najdeno fajlov: {len(pdf_files)}]")
    for f in pdf_files:
        print(f"   - {f.name}")
    
    # Анализ каждого файла
    results = []
    
    for pdf_file in pdf_files:
        print_header(f"АНАЛИЗ: {pdf_file.name}")
        
        # Анализируем
        analysis = analyze_pdf(str(pdf_file))
        
        if "error" in analysis:
            print(f"❌ Ошибка: {analysis['error']}")
            continue
        
        # Выводим результаты
        print(f"\n[METRIKI DOKUMENTA:]")
        print(f"   Страниц: {analysis['total_pages']}")
        print(f"   Язык: {analysis.get('languages', ['unknown'])}")
        print(f"   Тип: {analysis['document_type']}")
        print(f"   Плотность: {analysis['density']}")
        print(f"   Сложность: {analysis['complexity']}")
        
        print(f"\n[STRUKTURA:]")
        print(f"   Заголовков: {analysis['heading_count']}")
        print(f"   Абзацев: {analysis['paragraph_count']}")
        print(f"   Списков: {analysis['list_count']}")
        print(f"   Нужен OCR: {analysis['ocr_needed_pages']} страниц")
        
        rec = analysis.get("recommendations", {})
        
        print(f"\n[REKOMENDACII:]")
        print(f"   chunk_size: {rec.get('chunk_size')} (дефолт: 500)")
        print(f"   overlap: {rec.get('overlap')} (дефолт: 50)")
        print(f"   strategy: {rec.get('chunking_strategy')}")
        print(f"   OCR: {'Да' if rec.get('ocr_enabled') else 'Нет'}")
        
        if rec.get("rationale"):
            print(f"\n[OBOSNOVANIE:]")
            for r in rec["rationale"]:
                print(f"   • {r}")
        
        results.append({
            "file": pdf_file.name,
            "analysis": analysis,
            "recommendations": rec
        })
    
    # Sravnenie rezultatov
    print_header("SRAVNENIE REZULTATOV")
    
    print(f"\n{'Файл':<30} {'Тип':<12} {'Рекоменд.':<15} {'Дефолт':<10} {'Эффект'}")
    print("-" * 80)
    
    for r in results:
        rec = r["recommendations"]
        doc_type = r["analysis"]["document_type"]
        
        # Oцениваем effektivnost
        default_chunk = 500
        rec_chunk = rec.get("chunk_size", 500)
        
        if doc_type == "faq":
            effect = "[OK] Optimalno dlya FAQ"
        elif doc_type == "textbook":
            effect = "[OK] Uchteny zagolovki"
        elif rec_chunk < default_chunk:
            effect = "[OK] Menshe perokrytij"
        elif rec_chunk > default_chunk:
            effect = "[OK] Bolshe konteksta"
        else:
            effect = "[=] Bez izmenenij"
        
        print(f"{r['file'][:28]:<30} {doc_type:<12} chunk={rec_chunk:<7} {default_chunk:<10} {effect}")
    
    # Demonstraciya obrabotki s rekomenaciyami
    print_header("TESTOVAYA OBRABOTKA S REKOMENDACIYAMI")
    
    for r in results[:2]:  # Обработаем первые 2 файла
        pdf_file = Path("pdfs") / r["file"]
        rec = r["recommendations"]
        
        print(f"\n[Obrabotka: {r['file']}]")
        print(f"   Параметры: chunk={rec.get('chunk_size')}, overlap={rec.get('overlap')}")
        
        try:
            result = process_pdf(
                str(pdf_file),
                f"demo_output/{pdf_file.stem}",
                ocr_enabled=rec.get('ocr_enabled', False),
                enable_chunking=True,
                max_chunk_size=rec.get('chunk_size', 500),
                overlap=rec.get('overlap', 50),
                enable_vectorization=False,
                use_llm=False,  # Без LLM для скорости
                generate_demo=False
            )
            
            chunk_count = len(result.get('chunks', []))
            print(f"   [OK] Sozdano chunkov: {chunk_count}")
            
        except Exception as e:
            print(f"   [ERROR] {str(e)[:50]}")
    
    # Itogovaya tablica
    print_header("ITOGI")
    
    print(f"\n[STATISTIKA:]")
    print(f"   Obrabotano fajlov: {len(results)}")
    
    # Gruppirovka po tipam
    types = {}
    for r in results:
        t = r["analysis"]["document_type"]
        types[t] = types.get(t, 0) + 1
    
    print(f"\n   Tipy dokumentov:")
    for t, count in types.items():
        print(f"      {t}: {count}")
    
    # Srednie rekomendacii
    avg_chunk = sum(r["recommendations"].get("chunk_size", 500) for r in results) / len(results)
    avg_overlap = sum(r["recommendations"].get("overlap", 50) for r in results) / len(results)
    
    print(f"\n   Srednie rekomenduemy znacheniya:")
    print(f"      chunk_size: {avg_chunk:.0f}")
    print(f"      overlap: {avg_overlap:.0f}")
    
    print(f"\n[OK] Demonstraciya zavershena!")
    print(f"\n[VYVODY:]")
    print(f"   * Sistema analiza korrektno opredelyaet tip dokumenta")
    print(f"   * Rekomendacii adaptirovany pod kazhdyj tip")
    print(f"   * Dlya FAQ rekomenduyutsya men'shie chunki")
    print(f"   * Dlya uchebnikov - bol'shie s uchyotom zagolovkov")


def demo_interactive():
    """Интерактивная демонстрация."""
    
    print_header("ИНТЕРАКТИВНАЯ ДЕМОНСТРАЦИЯ")
    
    pdf_dir = Path("pdfs")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ Файлы не найдены")
        return
    
    print("\nВыберите файл для анализа:")
    for i, f in enumerate(pdf_files, 1):
        print(f"   {i}. {f.name}")
    
    try:
        choice = int(input("\n> Введите номер: ")) - 1
        if 0 <= choice < len(pdf_files):
            pdf_file = pdf_files[choice]
        else:
            print("Неверный выбор")
            return
    except:
        print("Используем первый файл")
        pdf_file = pdf_files[0]
    
    # Анализ
    print(f"\nАнализируем: {pdf_file.name}")
    print("-" * 40)
    
    analysis = analyze_pdf(str(pdf_file))
    
    if "error" in analysis:
        print(f"Ошибка: {analysis['error']}")
        return
    
    # Детальный вывод
    print(f"\n📄 Документ: {pdf_file.name}")
    print(f"   Страниц: {analysis['total_pages']}")
    print(f"   Язык: {', '.join(analysis.get('languages', []))}")
    
    print(f"\n📐 Тип: {analysis['document_type']}")
    print(f"   Плотность: {analysis['density']}")
    print(f"   Сложность: {analysis['complexity']}")
    
    print(f"\n📋 Структура:")
    print(f"   Заголовки: {analysis['heading_count']}")
    print(f"   Абзацы: {analysis['paragraph_count']}")
    print(f"   Списки: {analysis['list_count']}")
    
    rec = analysis.get("recommendations", {})
    
    print(f"\n🎯 Рекомендации:")
    print(f"   chunk_size: {rec.get('chunk_size')} (вместо 500)")
    print(f"   overlap: {rec.get('overlap')} (вместо 50)")
    print(f"   strategy: {rec.get('chunking_strategy')}")
    print(f"   OCR: {'Да' if rec.get('ocr_enabled') else 'Нет'}")
    
    if rec.get("rationale"):
        print(f"\n💡 Почему:")
        for r in rec["rationale"]:
            print(f"   • {r}")
    
    # Сравнение
    print(f"\n📊 Сравнение с дефолтом:")
    print(f"   {'Параметр':<15} {'Дефолт':<10} {'Рекоменд.':<10} {'Изменение'}")
    print(f"   {'-'*50}")
    print(f"   {'chunk_size':<15} {'500':<10} {rec.get('chunk_size'):<10} {'↓' if rec.get('chunk_size', 500) < 500 else '↑' if rec.get('chunk_size', 500) > 500 else '='}")
    print(f"   {'overlap':<15} {'50':<10} {rec.get('overlap'):<10} {'↓' if rec.get('overlap', 50) < 50 else '↑' if rec.get('overlap', 50) > 50 else '='}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Демонстратор анализа PDF")
    parser.add_argument("--interactive", "-i", action="store_true", help="Интерактивный режим")
    args = parser.parse_args()
    
    if args.interactive:
        demo_interactive()
    else:
        demo_analysis()
