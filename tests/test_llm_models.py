#!/usr/bin/env python3
"""Тест LLM моделей через proxyAPI."""

import os
import sys
import time
from pathlib import Path

print("=" * 70)
print("LLM MODELS DETAILED TEST")
print("=" * 70)

from src.llm_chunker import LLM_MODELS, LLMChunker

# ========================================
# PART 1: Model Configuration
# ========================================
print("\n[1] AVAILABLE MODELS")
print("-" * 70)

providers = {}
for model, info in LLM_MODELS.items():
    p = info['provider']
    if p not in providers:
        providers[p] = []
    ctx = info['context']
    ctx_str = f"{ctx//1000}K" if ctx < 1000000 else f"{ctx//1000000}M"
    providers[p].append({
        'name': model,
        'context': ctx_str,
        'context_num': ctx,
        'quality': info.get('quality', 0),
        'speed': info.get('speed', 0),
        'cost': info.get('cost', 0)
    })

for provider, models in providers.items():
    print(f"\n{provider.upper()} ({len(models)} models):")
    print(f"{'Model':<35} {'Context':>8} {'Q':>4} {'S':>4} {'C':>4}")
    print("-" * 55)
    for m in sorted(models, key=lambda x: -x['quality']):
        print(f"{m['name']:<35} {m['context']:>8} {m['quality']:>4} {m['speed']:>4} {m['cost']:>4}")

# ========================================
# PART 2: API Connection Test
# ========================================
print("\n" + "=" * 70)
print("[2] API CONNECTION TEST")
print("=" * 70)

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("\n[SKIP] OPENAI_API_KEY not set")
    print("Set the environment variable to test API connections")
else:
    print(f"\nAPI Key: {api_key[:15]}...{api_key[-4:]}")
    
    # Тестовые модели (по одной от каждого провайдера)
    test_models = [
        ("gpt-4o-mini", "openai"),
        ("gpt-4o", "openai"),
        ("claude-sonnet-4-6", "anthropic"),
        ("claude-haiku-4-5", "anthropic"),
        ("gemini-2.5-flash", "google"),
    ]
    
    results = []
    
    for model, provider in test_models:
        print(f"\nTesting {model} ({provider})...")
        try:
            chunker = LLMChunker(api_key=api_key, model=model)
            
            if not chunker.is_available():
                print(f"  [FAIL] Client not available")
                results.append((model, provider, "FAIL", 0, "Client unavailable"))
                continue
            
            # Тестовый вызов
            start_time = time.time()
            response = chunker.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say 'OK' in Russian"}],
                max_tokens=20,
                temperature=0
            )
            elapsed = time.time() - start_time
            
            result_text = response.choices[0].message.content
            tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0
            
            print(f"  [OK] Response: {result_text[:30]}")
            print(f"  Time: {elapsed:.2f}s, Tokens: {tokens}")
            
            results.append((model, provider, "OK", elapsed, result_text[:30]))
            
        except Exception as e:
            err_msg = str(e)[:60]
            print(f"  [ERROR] {err_msg}")
            results.append((model, provider, "ERROR", 0, err_msg))
    
    # Итоговая таблица
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Model':<30} {'Provider':<10} {'Status':>8} {'Time':>8} {'Response':<20}")
    print("-" * 80)
    for model, provider, status, elapsed, response in results:
        print(f"{model:<30} {provider:<10} {status:>8} {elapsed:>7.2f}s {response[:20]:<20}")

# ========================================
# PART 3: Recommendations
# ========================================
print("\n" + "=" * 70)
print("MODEL RECOMMENDATIONS")
print("=" * 70)

recommendations = """
+------------------+---------------------+------------------+
| Use Case         | Recommended Model   | Reason           |
+------------------+---------------------+------------------+
| Best Quality     | claude-opus-4-6     | Highest quality  |
| Best Balance     | claude-sonnet-4-6   | Quality + 1M ctx |
| Best Speed       | gpt-4o-mini         | Fast + cheap     |
| Best Cost        | gemini-2.5-flash    | Very cheap       |
| Large Documents  | claude-sonnet-4-6   | 1M context       |
| Russian Text     | claude-sonnet-4-6   | Good RU support  |
+------------------+---------------------+------------------+

DEFAULT: claude-sonnet-4-6 (best balance, 1M context window)
"""
print(recommendations)

print("=" * 70)
