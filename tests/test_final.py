#!/usr/bin/env python3
"""Финальный тест системы Squeezer с LLM моделями."""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Загружаем .env
from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("SQUEEZER FINAL SYSTEM TEST")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# Результаты
results = {
    "timestamp": datetime.now().isoformat(),
    "tests": {},
    "models": {},
    "summary": {}
}

# ========================================
# TEST 1: Environment Check
# ========================================
print("\n[1] ENVIRONMENT CHECK")
print("-" * 40)

api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE", "https://api.proxyapi.ru/openai/v1")

if api_key:
    print(f"  [OK] API Key: {api_key[:15]}...{api_key[-4:]}")
    print(f"  [OK] API Base: {api_base}")
    results["tests"]["environment"] = "OK"
else:
    print("  [FAIL] OPENAI_API_KEY not found")
    results["tests"]["environment"] = "FAIL"
    sys.exit(1)

# ========================================
# TEST 2: Module Imports
# ========================================
print("\n[2] MODULE IMPORTS")
print("-" * 40)

modules = [
    ("src.chunker", "Chunker"),
    ("src.llm_chunker", "LLM Chunker"),
    ("src.vectorizer", "Vectorizer"),
    ("src.preprocessor", "Preprocessor"),
    ("gui_app", "GUI App"),
]

for mod, name in modules:
    try:
        __import__(mod)
        print(f"  [OK] {name}")
        results["tests"][f"import_{name}"] = "OK"
    except Exception as e:
        print(f"  [FAIL] {name}: {str(e)[:40]}")
        results["tests"][f"import_{name}"] = "FAIL"

# ========================================
# TEST 3: LLM Models API Test
# ========================================
print("\n[3] LLM MODELS API TEST")
print("-" * 40)

from src.llm_chunker import LLMChunker, LLM_MODELS

# Тестируем ключевые модели
test_models = [
    ("gpt-4o-mini", "openai", "Быстрая/дешевая"),
    ("gpt-4o", "openai", "Баланс"),
    ("claude-sonnet-4-6", "anthropic", "Рекомендуемая (1M)"),
    ("claude-haiku-4-5", "anthropic", "Быстрая Claude"),
    ("gemini-2.5-flash", "google", "Быстрый Gemini"),
]

print(f"\n{'Model':<25} {'Provider':<10} {'Status':>8} {'Time':>8} {'Response':<25}")
print("-" * 80)

for model, provider, desc in test_models:
    try:
        chunker = LLMChunker(api_key=api_key, model=model)
        
        if not chunker.is_available():
            print(f"{model:<25} {provider:<10} {'FAIL':>8} {'-':>8} {'Client unavailable':<25}")
            results["models"][model] = {"status": "FAIL", "error": "Client unavailable"}
            continue
        
        start = time.time()
        response = chunker.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'OK' in Russian"}],
            max_tokens=20,
            temperature=0
        )
        elapsed = time.time() - start
        
        text = response.choices[0].message.content[:20]
        tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0
        
        print(f"{model:<25} {provider:<10} {'OK':>8} {elapsed:>7.2f}s {text:<25}")
        results["models"][model] = {
            "status": "OK",
            "time": elapsed,
            "tokens": tokens,
            "response": text
        }
        
    except Exception as e:
        err = str(e)[:50]
        print(f"{model:<25} {provider:<10} {'ERROR':>8} {'-':>8} {err:<25}")
        results["models"][model] = {"status": "ERROR", "error": err}

# ========================================
# TEST 4: Embedding Test
# ========================================
print("\n[4] EMBEDDING TEST")
print("-" * 40)

try:
    from src.vectorizer import EmbeddingEngine
    
    engine = EmbeddingEngine(
        api_key=api_key,
        model_name="text-embedding-3-small",
        api_base=api_base
    )
    
    test_texts = [
        "Тестовый текст для эмбеддинга",
        "Второй тестовый текст"
    ]
    
    start = time.time()
    embeddings = engine.generate_embeddings(test_texts)
    elapsed = time.time() - start
    
    dim = len(embeddings[0]) if embeddings else 0
    
    print(f"  Embeddings: {len(embeddings)}")
    print(f"  Dimension: {dim}")
    print(f"  Time: {elapsed:.2f}s")
    
    results["tests"]["embedding"] = {
        "status": "OK",
        "count": len(embeddings),
        "dimension": dim,
        "time": elapsed
    }
    
except Exception as e:
    print(f"  [ERROR] {str(e)[:60]}")
    results["tests"]["embedding"] = {"status": "ERROR", "error": str(e)[:60]}

# ========================================
# TEST 5: Chunker Test
# ========================================
print("\n[5] CHUNKER TEST")
print("-" * 40)

try:
    from src.chunker import hybrid_chunking, add_metadata, validate_chunks
    
    # Тестовая структура
    structure = {
        "headings": [{"level": 1, "text": "Тест", "position": 0}],
        "paragraphs": [{"text": "Тестовый абзац " * 50, "position": 0}],
        "lists": []
    }
    
    chunks = hybrid_chunking(structure, max_size=500, overlap=50)
    chunks_meta = add_metadata(chunks, "test.pdf", 1)
    validation = validate_chunks(chunks_meta)
    
    print(f"  Chunks: {len(chunks_meta)}")
    print(f"  Validation: {validation['status']}")
    
    results["tests"]["chunker"] = {
        "status": "OK",
        "chunks": len(chunks_meta)
    }
    
except Exception as e:
    print(f"  [ERROR] {str(e)[:60]}")
    results["tests"]["chunker"] = {"status": "ERROR", "error": str(e)[:60]}

# ========================================
# TEST 6: Full Pipeline Test
# ========================================
print("\n[6] FULL PIPELINE TEST")
print("-" * 40)

test_pdfs = list(Path(".").glob("*.pdf"))

if test_pdfs:
    test_pdf = test_pdfs[0]
    print(f"  PDF: {test_pdf.name}")
    
    try:
        from src.preprocessor import process_pdf
        
        start = time.time()
        result = process_pdf(
            str(test_pdf),
            "./test_output_final",
            ocr_enabled=False,
            enable_chunking=True,
            max_chunk_size=500,
            overlap=50,
            enable_vectorization=False,
            use_llm=False,
            api_key=api_key
        )
        elapsed = time.time() - start
        
        chunks = result.get("chunks", [])
        print(f"  Chunks: {len(chunks)}")
        print(f"  Time: {elapsed:.2f}s")
        
        results["tests"]["pipeline"] = {
            "status": "OK",
            "chunks": len(chunks),
            "time": elapsed
        }
        
    except Exception as e:
        print(f"  [ERROR] {str(e)[:60]}")
        results["tests"]["pipeline"] = {"status": "ERROR", "error": str(e)[:60]}
else:
    print("  [SKIP] No test PDF found")
    results["tests"]["pipeline"] = {"status": "SKIPPED"}

# ========================================
# SUMMARY
# ========================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

# Подсчёт
total = 0
passed = 0
failed = 0

for test, data in results["tests"].items():
    total += 1
    if isinstance(data, dict) and data.get("status") == "OK":
        passed += 1
    elif data == "OK":
        passed += 1
    else:
        failed += 1

for model, data in results["models"].items():
    total += 1
    if data.get("status") == "OK":
        passed += 1
    else:
        failed += 1

success_rate = (passed / total * 100) if total > 0 else 0

print(f"\n  Total tests: {total}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"  Success rate: {success_rate:.1f}%")

results["summary"] = {
    "total": total,
    "passed": passed,
    "failed": failed,
    "success_rate": success_rate
}

# Сохраняем
with open("test_results_final.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n  Results saved: test_results_final.json")
print("=" * 80)

# ========================================
# MODEL COMPARISON TABLE
# ========================================
print("\n" + "=" * 80)
print("MODEL COMPARISON TABLE")
print("=" * 80)

print(f"\n{'Model':<25} {'Provider':<10} {'Context':>8} {'Quality':>8} {'Speed':>8} {'Cost':>8} {'Test':>8}")
print("-" * 85)

for model, info in LLM_MODELS.items():
    ctx = info['context']
    ctx_str = f"{ctx//1000}K" if ctx < 1000000 else f"{ctx//1000000}M"
    q = info.get('quality', 0)
    s = info.get('speed', 0)
    c = info.get('cost', 0)
    
    # Статус теста
    test_status = results["models"].get(model, {}).get("status", "-")
    test_str = "OK" if test_status == "OK" else ("ERR" if test_status == "ERROR" else "-")
    
    print(f"{model:<25} {info['provider']:<10} {ctx_str:>8} {q:>8} {s:>8} {c:>8} {test_str:>8}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print("""
+-------------------+--------------------+-------------------------+
| Use Case          | Model              | Reason                  |
+-------------------+--------------------+-------------------------+
| Best Quality      | claude-opus-4-6    | Highest quality         |
| Best Balance      | claude-sonnet-4-6  | Quality + 1M context    |
| Best Speed/Cost   | gpt-4o-mini        | Fast + cheap            |
| Large Documents   | claude-sonnet-4-6  | 1M context window       |
| Russian Text      | claude-sonnet-4-6  | Good Russian support    |
+-------------------+--------------------+-------------------------+

DEFAULT: claude-sonnet-4-6
""")
print("=" * 80)
