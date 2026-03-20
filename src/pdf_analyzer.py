"""
Модуль предварительного анализа PDF для рекомендаций по обработке.

Анализирует документ и даёт рекомендации по:
- Размеру чанков
- Overlap
- Нужно ли OCR
- Типу чанкинга
- Параметрам LLM
"""

import logging
import re
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

# Загружаем .env
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Попытка импортировать langdetect
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


def analyze_pdf(
    pdf_path: str, 
    sample_pages: int = 5,
    use_llm: bool = True,
    llm_model: str = "gpt-4o",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> Dict[str, Any]:
    """
    Анализирует PDF и возвращает метрики и рекомендации.
    
    Args:
        pdf_path: Путь к PDF файлу.
        sample_pages: Количество страниц для анализа (0 = все).
        use_llm: Использовать LLM для углублённого анализа.
        llm_model: Модель LLM для анализа.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Словарь с метриками и рекомендациями.
    """
    logger.info(f"Анализ PDF: {pdf_path}")
    
    # Импортируем pypdf
    try:
        import pypdf
    except ImportError:
        return {"error": "pypdf не установлен"}
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            
            # Анализируем страницы
            pages_to_analyze = min(sample_pages, total_pages) if sample_pages > 0 else total_pages
            
            metrics = {
                "total_pages": total_pages,
                "pages_analyzed": pages_to_analyze,
                "languages": [],
                "structure_types": [],
                "avg_chars_per_page": 0,
                "avg_sentences_per_page": 0,
                "has_tables": False,
                "has_equations": False,
                "has_images_placeholder": False,
                "heading_count": 0,
                "list_count": 0,
                "paragraph_count": 0,
                "ocr_needed_pages": 0,
                "density": "unknown",  # low, medium, high
                "complexity": "unknown",  # simple, medium, complex
            }
            
            all_chars = 0
            all_sentences = 0
            
            for i in range(pages_to_analyze):
                page = pdf_reader.pages[i]
                text = page.extract_text() or ""
                
                # Проверяем, нужен ли OCR
                if not text or len(text.strip()) < 20:
                    metrics["ocr_needed_pages"] += 1
                
                # Анализируем контент
                text_lower = text.lower()
                
                # Таблицы
                if re.search(r'[│┌┐└┘├┤|]{3,}', text) or re.search(r'\t{2,}', text):
                    metrics["has_tables"] = True
                
                # Уравнения
                if re.search(r'[∑∏∫√∞≈≠≤≥±×÷]', text):
                    metrics["has_equations"] = True
                
                # Изображения (маркеры)
                if '/image' in text_lower or 'рис.' in text_lower or 'image' in text_lower:
                    metrics["has_images_placeholder"] = True
                
                # Заголовки (короткие строки без точки в конце)
                headings = re.findall(r'^[А-ЯA-ZЁЁ][^\.]{3,40}$', text, re.MULTILINE)
                metrics["heading_count"] += len(headings)
                
                # Списки
                lists = re.findall(r'^[\-\*•]\s+|^[0-9]+[.)]\s+', text, re.MULTILINE)
                metrics["list_count"] += len(lists)
                
                # Абзацы (блоки текста)
                paragraphs = [p for p in text.split('\n\n') if len(p.strip()) > 50]
                metrics["paragraph_count"] += len(paragraphs)
                
                # Предложения
                sentences = re.split(r'[.!?]+', text)
                all_sentences += len([s for s in sentences if s.strip()])
                
                # Символы
                all_chars += len(text)
                
                # Язык
                if len(text.strip()) > 50:
                    try:
                        if LANGDETECT_AVAILABLE:
                            lang = detect(text[:500])
                            if lang not in metrics["languages"]:
                                metrics["languages"].append(lang)
                    except LangDetectException:
                        pass
            
            # Вычисляем средние
            if pages_to_analyze > 0:
                metrics["avg_chars_per_page"] = all_chars // pages_to_analyze
                metrics["avg_sentences_per_page"] = all_sentences // pages_to_analyze
            
            # Определяем плотность
            if metrics["avg_chars_per_page"] < 1000:
                metrics["density"] = "low"
            elif metrics["avg_chars_per_page"] < 3000:
                metrics["density"] = "medium"
            else:
                metrics["density"] = "high"
            
            # Определяем сложность по средней длине предложений
            avg_sentence_len = all_chars / max(all_sentences, 1)
            if avg_sentence_len < 50:
                metrics["complexity"] = "simple"
            elif avg_sentence_len < 100:
                metrics["complexity"] = "medium"
            else:
                metrics["complexity"] = "complex"
            
            # Определяем тип документа
            metrics["document_type"] = _determine_document_type(metrics)
            
            # Генерируем рекомендации
            recommendations = _generate_recommendations(metrics)
            metrics["recommendations"] = recommendations
            
            # LLM-анализ (опционально)
            llm_analysis = None
            if use_llm:
                llm_analysis = _analyze_with_llm(
                    pdf_path, 
                    llm_model=llm_model,
                    api_key=api_key,
                    api_base=api_base
                )
                if llm_analysis:
                    # Обновляем рекомендации на основе LLM
                    metrics["llm_analysis"] = llm_analysis
                    recommendations = _merge_llm_recommendations(recommendations, llm_analysis)
                    metrics["recommendations"] = recommendations
            
            logger.info(f"Анализ завершён: {metrics['document_type']}, плотность: {metrics['density']}")
            
            return metrics
            
    except Exception as e:
        logger.error(f"Ошибка анализа PDF: {e}")
        return {"error": str(e)}


def _determine_document_type(metrics: Dict) -> str:
    """Определяет тип документа по метрикам."""
    
    # FAQ: много вопросов-ответов
    if metrics["heading_count"] > 0:
        heading_ratio = metrics["heading_count"] / max(metrics["total_pages"], 1)
        if heading_ratio > 3:
            return "faq"
    
    # Учебник: много заголовков, средняя плотность
    if metrics["heading_count"] > metrics["paragraph_count"] * 0.3:
        return "textbook"
    
    # Статья: много абзацев, мало заголовков
    if metrics["paragraph_count"] > metrics["heading_count"] * 2:
        return "article"
    
    # Отчёт: много таблиц
    if metrics["has_tables"]:
        return "report"
    
    # Книга: высокая плотность
    if metrics["density"] == "high" and metrics["total_pages"] > 20:
        return "book"
    
    return "document"


def _generate_recommendations(metrics: Dict) -> Dict[str, Any]:
    """Генерирует рекомендации по обработке."""
    
    doc_type = metrics.get("document_type", "document")
    density = metrics.get("density", "medium")
    complexity = metrics.get("complexity", "medium")
    
    rec = {
        "chunk_size": 500,
        "overlap": 50,
        "ocr_enabled": False,
        "llm_enabled": True,
        "chunking_strategy": "hybrid",
        "rationale": []
    }
    
    # Рекомендации по размеру чанка
    if doc_type == "textbook":
        rec["chunk_size"] = 600
        rec["overlap"] = 80
        rec["chunking_strategy"] = "by_headings"
        rec["rationale"].append("Учебник: larger chunks для сохранения контекста глав")
        
    elif doc_type == "faq":
        rec["chunk_size"] = 250
        rec["overlap"] = 30
        rec["chunking_strategy"] = "by_questions"
        rec["rationale"].append("FAQ: smaller chunks для точных ответов")
        
    elif doc_type == "article":
        rec["chunk_size"] = 400
        rec["overlap"] = 50
        rec["chunking_strategy"] = "by_paragraphs"
        rec["rationale"].append("Статья: средние чанки по абзацам")
        
    elif doc_type == "report":
        rec["chunk_size"] = 450
        rec["overlap"] = 60
        rec["chunking_strategy"] = "hybrid"
        rec["rationale"].append("Отчёт: учитываем таблицы")
        
    elif doc_type == "book":
        rec["chunk_size"] = 700
        rec["overlap"] = 100
        rec["chunking_strategy"] = "hybrid"
        rec["rationale"].append("Книга: larger chunks для длинных глав")
    
    # Корректировка по плотности
    if density == "low":
        rec["chunk_size"] = min(rec["chunk_size"], 300)
        rec["rationale"].append("Низкая плотность: уменьшаем чанки")
    elif density == "high":
        rec["chunk_size"] = max(rec["chunk_size"], 500)
        rec["rationale"].append("Высокая плотность: увеличиваем чанки")
    
    # OCR
    if metrics.get("ocr_needed_pages", 0) > 0:
        rec["ocr_enabled"] = True
        rec["rationale"].append(f"OCR нужен для {metrics['ocr_needed_pages']} страниц")
    
    # LLM для сложных документов
    if complexity == "complex" or doc_type in ["textbook", "book"]:
        rec["llm_enabled"] = True
        rec["rationale"].append("Сложный документ: LLM для качественных метаданных")
    
    # Таблицы
    if metrics.get("has_tables"):
        rec["rationale"].append("Документ содержит таблицы - рекомендуется preserve_tables=True")
    
    return rec


def print_analysis(analysis: Dict) -> None:
    """Выводит результаты анализа в читаемом виде."""
    
    if "error" in analysis:
        print(f"Error: {analysis['error']}")
        return
    
    print("\n" + "=" * 60)
    print("ANALIZ DOKUMENTA")
    print("=" * 60)
    
    print(f"\nStranic: {analysis['total_pages']}")
    print(f"Yaziki: {analysis.get('languages', ['unknown'])}")
    print(f"Tip dokumenta: {analysis.get('document_type', 'unknown')}")
    
    print(f"\nMetriki:")
    print(f"   Srednee simvolov/stranica: {analysis['avg_chars_per_page']}")
    print(f"   Srednee predlozheniy/stranica: {analysis['avg_sentences_per_page']}")
    print(f"   Plotnost: {analysis['density']}")
    print(f"   Slozhnost: {analysis['complexity']}")
    
    print(f"\nStruktura:")
    print(f"   Zagolovkov: {analysis['heading_count']}")
    print(f"   Abzacev: {analysis['paragraph_count']}")
    print(f"   Spiskov: {analysis['list_count']}")
    print(f"   Stranic s OCR: {analysis['ocr_needed_pages']}")
    print(f"   Tablicy: {'Da' if analysis['has_tables'] else 'Net'}")
    print(f"   Uravneniya: {'Da' if analysis['has_equations'] else 'Net'}")
    
    rec = analysis.get("recommendations", {})
    print(f"\nREKOMENDACII:")
    print(f"   Razmer chanka: {rec.get('chunk_size', 'N/A')}")
    print(f"   Overlap: {rec.get('overlap', 'N/A')}")
    print(f"   Strategiya: {rec.get('chunking_strategy', 'N/A')}")
    print(f"   OCR: {'Da' if rec.get('ocr_enabled') else 'Net'}")
    print(f"   LLM: {'Da' if rec.get('llm_enabled') else 'Net'}")
    
    if rec.get("rationale"):
        print(f"\nObosnovanie:")
        for r in rec["rationale"]:
            print(f"   - {r}")
    
    print("=" * 60 + "\n")


def _analyze_with_llm(
    pdf_path: str,
    llm_model: str = "gpt-4o",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> Optional[Dict[str, Any]]:
    """
    Анализирует PDF с помощью LLM.
    
    Args:
        pdf_path: Путь к PDF файлу.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Словарь с LLM-анализом.
    """
    import pypdf
    
    try:
        # Читаем текст из PDF
        with open(pdf_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            
            # Берём первые 3 страницы для анализа
            sample_text = ""
            for i in range(min(3, len(pdf_reader.pages))):
                text = pdf_reader.pages[i].extract_text()
                if text:
                    sample_text += text + "\n"
        
        # Ограничиваем текст
        sample_text = sample_text[:3000]
        
        if not sample_text.strip():
            return None
        
        # Промпт для LLM
        prompt = f"""Проанализируй этот текст документа и ответь в JSON формате:

{{
  "document_type": "учебник/статья/гайд/договор/отчёт/книга/другое",
  "description": "Краткое описание (1-2 предложения)",
  "topics": ["тема1", "тема2", "тема3"],
  "language_style": "академический/технический/публицистический/художественный/деловой",
  "complexity": "простой/средний/сложный",
  "has_code": true/false,
  "has_tables": true/false,
  "has_lists": true/false,
  "recommended_chunk_size": число,
  "recommended_overlap": число,
  "reasoning": "Краткое обоснование рекомендаций"
}}

Текст документа:
{sample_text}

Ответь ТОЛЬКО в JSON формате, без дополнительного текста."""

        # Вызываем LLM через llm_chunker
        try:
            from src.llm_chunker import call_llm
            
            response = call_llm(
                prompt=prompt,
                model=llm_model,
                api_key=api_key,
                api_base=api_base,
                temperature=0.3,
                max_tokens=500
            )
            
            if response:
                # Парсим JSON из ответа
                import json
                import re
                
                # Ищем JSON в ответе
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    llm_result = json.loads(json_match.group())
                    logger.info(f"LLM анализ: {llm_result.get('document_type', 'unknown')}")
                    return llm_result
                    
        except Exception as e:
            logger.warning(f"LLM анализ недоступен: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка LLM анализа: {e}")
    
    return None


def _merge_llm_recommendations(
    base_rec: Dict[str, Any],
    llm_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Объединяет базовые рекомендации с LLM-анализом.
    
    Args:
        base_rec: Базовые рекомендации.
        llm_analysis: Результат LLM-анализа.
    
    Returns:
        Объединённые рекомендации.
    """
    merged = base_rec.copy()
    
    if not llm_analysis:
        return merged
    
    # Обновляем на основе LLM
    if llm_analysis.get("recommended_chunk_size"):
        chunk_size = llm_analysis["recommended_chunk_size"]
        if 100 <= chunk_size <= 2000:
            merged["chunk_size"] = chunk_size
            merged["rationale"].append(f"LLM рекомендует chunk_size={chunk_size}")
    
    if llm_analysis.get("recommended_overlap"):
        overlap = llm_analysis["recommended_overlap"]
        if 0 <= overlap <= 200:
            merged["overlap"] = overlap
            merged["rationale"].append(f"LLM рекомендует overlap={overlap}")
    
    # Обновляем описание
    if llm_analysis.get("description"):
        merged["description"] = llm_analysis["description"]
    
    if llm_analysis.get("topics"):
        merged["topics"] = llm_analysis["topics"]
    
    if llm_analysis.get("language_style"):
        merged["language_style"] = llm_analysis["language_style"]
    
    # Добавляем флаги
    if llm_analysis.get("has_code"):
        merged["has_code"] = True
        merged["rationale"].append("Документ содержит код - рекомендуется special handling")
    
    if llm_analysis.get("has_tables"):
        merged["has_tables"] = True
    
    # Обновляем сложность
    if llm_analysis.get("complexity"):
        merged["complexity"] = llm_analysis["complexity"]
    
    return merged


# CLI для тестирования
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python pdf_analyzer.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    analysis = analyze_pdf(pdf_path)
    print_analysis(analysis)
