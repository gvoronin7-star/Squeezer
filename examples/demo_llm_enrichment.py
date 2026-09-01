"""
Ручной demo-скрипт: LLM-обогащение метаданных чанков (модель gpt-4o).

ВНИМАНИЕ: делает настоящий платный вызов LLM на уровне модуля (при
простом импорте, если найден рабочий API-ключ) — не при явном
вызове функции. Не pytest-тест — раньше лежал в tests/ как
test_llm_enrichment.py и совпадал с паттерном сбора pytest'а. См.
decisions/decision-log.md.
"""
from dotenv import load_dotenv
load_dotenv()

from src.chunker import hybrid_chunking, add_metadata
from src.llm_chunker import LLMChunker
import os

# Тестовый текст
test_structure = {
    'paragraphs': ['RAG (Retrieval-Augmented Generation) — это подход к обработке информации. RAG используется для улучшения качества ответов больших языковых моделей. Этот метод особенно полезен для работы с большими объёмами данных.'],
    'headings': [],
    'lists': []
}

# Создаём чанки
chunks = hybrid_chunking(test_structure, max_chunk_size=200, overlap=20)
chunks_with_meta = add_metadata(chunks, 'test.pdf', 1)

print('=== До LLM ===')
for i, c in enumerate(chunks_with_meta):
    print(f'Chunk {i}: {c["text"][:80]}...')
    print(f'  Metadata: {c.get("metadata", {})}')
    print()

# Теперь обогатим через LLM
llm = LLMChunker(model='gpt-4o')
if llm.is_available():
    print('=== LLM обогащение ===')
    enhanced = llm.enhance_metadata(chunks_with_meta)
    
    for i, c in enumerate(enhanced):
        print(f'Chunk {i}: {c["text"][:80]}...')
        print(f'  Metadata: {c.get("metadata", {})}')
        print()
else:
    print('LLM недоступен - проверьте OPENAI_API_KEY')
