#!/usr/bin/env python3
"""Комплексное тестирование системы Squeezer."""

import os
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("SQUEEZER SYSTEM TEST")
print("=" * 60)

# Test 1: Imports
print("\n[TEST 1] Module imports")
try:
    from src.preprocessor import process_pdf
    from src.chunker import hybrid_chunking
    from src.llm_chunker import LLMChunker, call_llm
    from src.vectorizer import process_vectorization
    from src.pdf_analyzer import analyze_pdf
    print("  [OK] All modules imported")
except Exception as e:
    print(f"  [ERROR] {e}")
    sys.exit(1)

# Test 2: PDF Analysis without LLM
print("\n[TEST 2] PDF Analysis (no LLM)")
try:
    result = analyze_pdf("pdfs/test_document.pdf", use_llm=False)
    print(f"  Type: {result.get('document_type')}")
    print(f"  Pages: {result.get('total_pages')}")
    print(f"  Rec chunk: {result['recommendations'].get('chunk_size')}")
    print("  [OK]")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 3: PDF Analysis with LLM
print("\n[TEST 3] PDF Analysis (with LLM)")
try:
    result = analyze_pdf("pdfs/test_document.pdf", use_llm=True)
    print(f"  Type: {result.get('document_type')}")
    print(f"  Has LLM: {bool(result.get('llm_analysis'))}")
    if result.get('llm_analysis'):
        print(f"  LLM desc: {result['llm_analysis'].get('description', 'N/A')[:50]}...")
    print(f"  Rec chunk: {result['recommendations'].get('chunk_size')}")
    print("  [OK]")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 4: Full pipeline (without vectorization)
print("\n[TEST 4] Full pipeline (chunks only)")
try:
    result = process_pdf(
        "pdfs/test_document.pdf",
        "test_quick_output",
        ocr_enabled=False,
        enable_chunking=True,
        max_chunk_size=300,
        overlap=30,
        enable_vectorization=False,
        use_llm=False
    )
    print(f"  Chunks: {len(result.get('chunks', []))}")
    print(f"  Report: {result.get('report_path')}")
    print("  [OK]")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 5: Batch analysis
print("\n[TEST 5] Batch PDF analysis")
try:
    pdfs = [f for f in os.listdir("pdfs") if f.endswith(".pdf")]
    print(f"  Found {len(pdfs)} PDFs")
    
    results = []
    for pdf in pdfs[:5]:
        r = analyze_pdf(f"pdfs/{pdf}", use_llm=False)
        results.append({
            "file": pdf,
            "type": r.get("document_type"),
            "pages": r.get("total_pages"),
            "rec_chunk": r["recommendations"].get("chunk_size")
        })
    
    print("  Results:")
    for res in results:
        print(f"    - {res['file'][:30]}: {res['type']} ({res['pages']}p) chunk={res['rec_chunk']}")
    print("  [OK]")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 6: Check output files
print("\n[TEST 6] Output files check")
try:
    output_dirs = ["test_quick_output", "test_pipeline_output", "test_full_pipeline"]
    for d in output_dirs:
        if Path(d).exists():
            files = list(Path(d).rglob("*"))
            print(f"  {d}/: {len(files)} files")
    print("  [OK]")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED")
print("=" * 60)
