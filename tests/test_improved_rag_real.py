# -*- coding: utf-8 -*-
"""
Real test of Improved RAG on PDF files.
"""

import os
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print('='*60)
print('REAL TEST: Improved RAG on PDF files')
print('='*60)
print()

# Step 1: Process PDF and create vector DB
print('[STEP 1] Processing PDF...')
from src.preprocessor import process_pdf

pdf_path = 'pdfs/test_document.pdf'
output_dir = 'test_rag_output'

result = process_pdf(
    pdf_path=pdf_path,
    output_dir=output_dir,
    enable_chunking=True,
    max_chunk_size=500,
    overlap=50,
    enable_vectorization=True,
    use_llm=False  # Для быстрого теста без LLM
)

print(f'Processed: {result.get("total_chunks", 0)} chunks')
print()

# Check output
index_path = os.path.join(output_dir, 'vector_db', 'index.faiss')
dataset_path = os.path.join(output_dir, 'vector_db', 'dataset.json')

print(f'Index exists: {os.path.exists(index_path)}')
print(f'Dataset exists: {os.path.exists(dataset_path)}')
print()

# Step 2: Test Improved RAG
print('='*60)
print('[STEP 2] Testing Improved RAG')
print('='*60)
print()

from src.improved_rag import ImprovedRAG

# Test query
query = "What is RAG and how does it work?"

print(f'Query: {query}')
print()

# Test 1: Basic RAG (no improvements)
print('[TEST 1] Basic RAG (no improvements)')
rag_basic = ImprovedRAG(
    use_reranking=False,
    use_hyde=False,
    use_fusion=False,
    top_k=5,
    final_top_k=3
)

result_basic = rag_basic.query(
    query=query,
    index_path=index_path,
    dataset_path=dataset_path,
    verbose=False
)

print(f'Answer: {result_basic.answer[:200]}...')
print(f'Sources: {len(result_basic.sources)}')
print()

# Test 2: RAG with Re-ranking
print('[TEST 2] RAG + Re-ranking')
rag_rerank = ImprovedRAG(
    use_reranking=True,
    use_hyde=False,
    use_fusion=False,
    top_k=5,
    final_top_k=3
)

result_rerank = rag_rerank.query(
    query=query,
    index_path=index_path,
    dataset_path=dataset_path,
    verbose=True
)

print(f'Answer: {result_rerank.answer[:200]}...')
print(f'Sources: {len(result_rerank.sources)}')
print()

# Show source details
print('Sources with scores:')
for i, src in enumerate(result_rerank.sources):
    text_preview = src.get('text', '')[:80].replace('\n', ' ')
    score = src.get('score', 0)
    print(f'  {i+1}. [score: {score:.2f}] {text_preview}...')
print()

print('='*60)
print('TESTS COMPLETED')
print('='*60)
