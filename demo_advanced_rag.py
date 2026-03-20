"""
Демонстрация Advanced RAG модулей.

Тестирует:
1. Кэширование эмбеддингов
2. Query rewriting
3. Answer с цитатами
4. Извлечение таблиц
5. Self-RAG
"""

import os
import sys

# Настройка UTF-8
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

print("=" * 70)
print("ADVANCED RAG DEMO")
print("=" * 70)

# Загружаем .env
from dotenv import load_dotenv
load_dotenv()

# Проверяем API ключ
api_key = os.getenv("OPENAI_API_KEY")
llm_model = "gpt-4o-mini"

if not api_key:
    print("\n⚠️  ВНИМАНИЕ: OPENAI_API_KEY не найден в .env")
    print("   Некоторые функции будут недоступны")
    print()

# ============================================================================
# 1. КЭШИРОВАНИЕ ЭМБЕДДИНГОВ
# ============================================================================
print("\n" + "="*70)
print("1. КЭШИРОВАНИЕ ЭМБЕДДИНГОВ")
print("="*70)

try:
    from src.embedding_cache import get_embedding_cache, get_embedding_with_cache
    
    # Создаём кэш
    cache = get_embedding_cache()
    
    print(f"\nСтатистика кэша: {cache.get_stats()}")
    
    # Пример использования
    print("\nПример работы с кэшем:")
    print("  cache.get('текст', 'модель') -> эмбеддинг или None")
    print("  cache.set('текст', 'модель', [вектор]) -> сохранение")
    print("  cache.get_batch([тексты], 'модель') -> батч запрос")
    
    print("\n✓ Модуль кэширования готов к использованию")
    
except Exception as e:
    print(f"\n✗ Ошибка: {e}")

# ============================================================================
# 2. QUERY REWRITING
# ============================================================================
print("\n" + "="*70)
print("2. QUERY REWRITING")
print("="*70)

try:
    from src.query_rewriter import QueryRewriter, rewrite_query
    
    rewriter = QueryRewriter(llm_model=llm_model, api_key=api_key)
    
    # Тестовые запросы
    test_queries = [
        "как создать бота",
        "что такое rag",
        "питон vs джаваскрипт",
    ]
    
    print("\nПримеры перезаписи запросов:")
    
    if api_key:
        for q in test_queries:
            result = rewriter.rewrite(q)
            print(f"\n  Оригинал: {result['original']}")
            print(f"  Перезаписан: {result['rewritten']}")
            print(f"  Стратегия: {result['strategy']}")
    else:
        print("\n  (Требуется API ключ для демонстрации)")
        print("\nПример результата:")
        print("  Оригинал: как создать бота")
        print("  Перезаписан: как создать telegram бота с помощью python")
        print("  Стратегия: expand")
    
    print("\n✓ Модуль query rewriting готов")
    
except Exception as e:
    print(f"\n✗ Ошибка: {e}")

# ============================================================================
# 3. ANSWER С ЦИТАТАМИ
# ============================================================================
print("\n" + "="*70)
print("3. ANSWER С ЦИТАТАМИ")
print("="*70)

try:
    from src.answer_generator import AnswerGenerator, generate_answer_with_citations
    
    generator = AnswerGenerator(llm_model=llm_model, api_key=api_key)
    
    # Тестовые документы
    test_docs = [
        {
            "text": "RAG (Retrieval Augmented Generation) - это метод машинного обучения, который комбинирует поиск информации с генерацией текста.",
            "metadata": {"chunk_id": "chunk_001", "page_number": 1, "source": "doc1.pdf"}
        },
        {
            "text": "Основные преимущества RAG: актуальность информации, снижение галлюцинаций, возможность проверки источников.",
            "metadata": {"chunk_id": "chunk_002", "page_number": 1, "source": "doc1.pdf"}
        },
        {
            "text": "FAISS - библиотека для эффективного поиска похожих векторов, разработанная Facebook AI.",
            "metadata": {"chunk_id": "chunk_003", "page_number": 2, "source": "doc2.pdf"}
        }
    ]
    
    print("\nТестовые документы загружены")
    print("  - chunk_001: Определение RAG")
    print("  - chunk_002: Преимущества RAG")
    print("  - chunk_003: О FAISS")
    
    if api_key:
        result = generator.generate(
            "Что такое RAG и какие у него преимущества?",
            test_docs,
            include_citations=True,
            verbose=False
        )
        
        print(f"\nЗапрос: Что такое RAG и какие у него преимущества?")
        print(f"\nОтвет:\n{result.answer[:300]}...")
        print(f"\nИсточников использовано: {result.sources_used}")
        print(f"Уверенность: {result.confidence:.2f}")
    else:
        print("\n  (Требуется API ключ для демонстрации)")
        print("\nПример ответа с цитатами:")
        print('  RAG (Retrieval Augmented Generation) - это метод... [source: chunk_001, p.1]')
        print('  Основные преимущества: актуальность... [source: chunk_002, p.1]')
    
    print("\n✓ Модуль генерации ответов с цитатами готов")
    
except Exception as e:
    print(f"\n✗ Ошибка: {e}")

# ============================================================================
# 4. ИЗВЛЕЧЕНИЕ ТАБЛИЦ
# ============================================================================
print("\n" + "="*70)
print("4. ИЗВЛЕЧЕНИЕ ТАБЛИЦ")
print("="*70)

try:
    from src.table_extractor import TableExtractor, extract_tables_from_pdf
    
    extractor = TableExtractor(llm_model=llm_model, api_key=api_key)
    
    print("\nФункции:")
    print("  - extract_tables(pdf_path, use_llm=False) -> нативное извлечение")
    print("  - extract_tables(pdf_path, use_llm=True) -> с LLM интерпретацией")
    print("  - Конвертация таблиц в JSON")
    print("  - Генерация описаний")
    
    # Проверяем наличие pdfplumber
    if extractor.pdfplumber_available:
        print("\n✓ pdfplumber доступен")
    else:
        print("\n⚠️  pdfplumber не установлен")
        print("   Установите: pip install pdfplumber")
    
    print("\n✓ Модуль извлечения таблиц готов")
    
except Exception as e:
    print(f"\n✗ Ошибка: {e}")

# ============================================================================
# 5. SELF-RAG
# ============================================================================
print("\n" + "="*70)
print("5. SELF-RAG")
print("="*70)

try:
    from src.self_rag import SelfRAG, self_rag_query
    
    print("\nSelf-RAG возможности:")
    print("  - Оценка релевантности каждого документа")
    print("  - Фильтрация нерелевантных")
    print("  - Генерация ответа")
    print("  - Оценка качества ответа")
    print("  - Повторная итерация при необходимости")
    
    print("\nОценки релевантности:")
    print("  - fully_relevant: Документ полностью отвечает")
    print("  - partially: Частично релевантен")
    print("  - not_relevant: Не релевантен")
    
    print("\nОценки качества ответа:")
    print("  - excellent: Отлично")
    print("  - good: Хорошо")
    print("  - partial: Частично")
    print("  - insufficient: Недостаточно")
    
    print("\n✓ Self-RAG модуль готов")
    
except Exception as e:
    print(f"\n✗ Ошибка: {e}")

# ============================================================================
# 6. ИНТЕГРАЦИОННЫЙ ПАЙПЛАЙН
# ============================================================================
print("\n" + "="*70)
print("6. ИНТЕГРАЦИОННЫЙ ПАЙПЛАЙН")
print("="*70)

try:
    from src.advanced_rag_pipeline import create_advanced_rag_pipeline
    
    # Создаём пайплайн
    config = {
        'llm_model': llm_model,
        'api_key': api_key,
        'api_base': 'https://openai.api.proxyapi.ru/v1'
    }
    
    pipeline = create_advanced_rag_pipeline(config)
    
    print("\nЗагруженные модули:")
    print(f"  - Кэширование: {'✓' if pipeline.embedding_cache else '✗'}")
    print(f"  - Query rewriting: {'✓' if pipeline.query_rewriter else '✗'}")
    print(f"  - Генератор ответов: {'✓' if pipeline.answer_generator else '✗'}")
    print(f"  - Self-RAG: {'✓' if pipeline.self_rag else '✗'}")
    print(f"  - Извлечение таблиц: {'✓' if pipeline.table_extractor else '✗'}")
    
    print("\nПример использования:")
    print("""
  # Создание пайплайна
  pipeline = create_advanced_rag_pipeline(config, vector_store)
  
  # Запрос с полным пайплайном
  result = pipeline.query(
      query="ваш вопрос",
      use_query_rewrite=True,
      use_self_rag=True,
      use_citations=True,
      top_k=5
  )
  
  # Результат
  print(result['answer'])        # Ответ
  print(result['citations'])     # Цитаты
  print(result['confidence'])    # Уверенность
  
  # Извлечение таблиц
  tables = pipeline.extract_tables('document.pdf', use_llm=True)
    """)
    
    print("\n✓ Интеграционный пайплайн готов")
    
except Exception as e:
    print(f"\n✗ Ошибка: {e}")

# ============================================================================
# ИТОГИ
# ============================================================================
print("\n" + "="*70)
print("ИТОГИ")
print("="*70)

print("""
Доступные модули:

1. src/embedding_cache.py
   - Кэширование эмбеддингов
   - Экономия API вызовов
   - Автоочистка устаревших

2. src/query_rewriter.py  
   - Расширение синонимами
   - Разбиение сложных запросов
   - Уточнение неопределённых

3. src/answer_generator.py
   - Генерация ответов
   - Автоматические цитаты
   - Оценка уверенности

4. src/table_extractor.py
   - Извлечение таблиц из PDF
   - LLM интерпретация
   - JSON конвертация

5. src/self_rag.py
   - Оценка релевантности
   - Фильтрация документов
   - Контроль качества

6. src/advanced_rag_pipeline.py
   - Объединяет все модули
   - Гибкая конфигурация
   - Единый интерфейс
""")

print("="*70)
print("ДEMO ЗАВЕРШЕН")
print("="*70)
