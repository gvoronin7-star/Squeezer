#!/usr/bin/env python3
"""Проверка доступных моделей в proxyAPI."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

print("=" * 60)
print("CHECKING AVAILABLE MODELS IN PROXYAPI")
print("=" * 60)
print()

headers = {'Authorization': f'Bearer {api_key}'}

# Check OpenAI models
print("[1] OpenAI models:")
url = 'https://api.proxyapi.ru/openai/v1/models'
try:
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        data = r.json()
        models = data.get('data', [])
        print(f"    Total: {len(models)} models")
        
        # Filter by provider
        openai_models = [m['id'] for m in models if 'gpt' in m['id'].lower()]
        claude_models = [m['id'] for m in models if 'claude' in m['id'].lower()]
        gemini_models = [m['id'] for m in models if 'gemini' in m['id'].lower()]
        
        print(f"\n    OpenAI (gpt-*): {len(openai_models)}")
        for m in openai_models[:10]:
            print(f"      - {m}")
        
        print(f"\n    Claude: {len(claude_models)}")
        for m in claude_models[:10]:
            print(f"      - {m}")
        
        print(f"\n    Gemini: {len(gemini_models)}")
        for m in gemini_models[:10]:
            print(f"      - {m}")
    else:
        print(f"    Error: {r.status_code} - {r.text[:100]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Test specific models
print("[2] Testing specific models:")

# Test OpenAI models
from openai import OpenAI
client_openai = OpenAI(api_key=api_key, base_url='https://api.proxyapi.ru/openai/v1')

openai_models = ['gpt-4o-mini', 'gpt-4o']
for model in openai_models:
    try:
        r = client_openai.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'Say OK'}],
            max_tokens=10
        )
        print(f"    [OK] {model} (OpenAI)")
    except Exception as e:
        print(f"    [FAIL] {model} (OpenAI) - {str(e)[:50]}")

# Test Claude models with Anthropic SDK
try:
    import anthropic
    client_claude = anthropic.Anthropic(api_key=api_key, base_url='https://api.proxyapi.ru/anthropic')
    
    claude_models = ['claude-sonnet-4-6', 'claude-haiku-4-5', 'claude-opus-4-6']
    for model in claude_models:
        try:
            r = client_claude.messages.create(
                model=model,
                max_tokens=10,
                messages=[{'role': 'user', 'content': 'Say OK'}]
            )
            print(f"    [OK] {model} (Claude)")
        except Exception as e:
            print(f"    [FAIL] {model} (Claude) - {str(e)[:50]}")
            
except ImportError:
    print("    [SKIP] Claude models (anthropic package not installed)")

print()
print("=" * 60)
print("CONCLUSION")
print("=" * 60)
