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
                "has_code": False,
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
                text_len = len(text.strip())
                
                # Логируем страницы с малым текстом
                if text_len < 100:
                    logger.info(f"Страница {i+1}: {text_len} символов текста")
                
                # OCR нужен если:
                # 1. Совсем нет текста (< 10 символов)
                # 2. И на странице есть изображения (признак скана)
                if text_len < 10:
                    # Проверяем наличие изображений через pypdf
                    try:
                        # pypdf 3.0+ имеет атрибут images
                        if hasattr(page, 'images') and len(page.images) > 0:
                            metrics["ocr_needed_pages"] += 1
                            logger.info(f"🔍 OCR нужен для страницы {i+1}: {len(page.images)} изображений, {text_len} символов")
                        else:
                            # Альтернативный способ через ресурсы страницы
                            if '/XObject' in page.get('/Resources', {}):
                                xobjects = page['/Resources']['/XObject']
                                if hasattr(xobjects, 'get_object'):
                                    xobjects = xobjects.get_object()
                                # Считаем количество изображений
                                img_count = 0
                                for key in xobjects:
                                    obj = xobjects[key]
                                    if hasattr(obj, 'get_object'):
                                        obj = obj.get_object()
                                    if obj.get('/Subtype') == '/Image':
                                        img_count += 1
                                if img_count > 0:
                                    metrics["ocr_needed_pages"] += 1
                                    logger.info(f"🔍 OCR нужен для страницы {i+1}: {img_count} изображений (XObject), {text_len} символов")
                    except Exception as e:
                        logger.debug(f"Не удалось проверить изображения на странице {i+1}: {e}")
            
                # Анализируем контент
                text_lower = text.lower()
                
                # Таблицы
                if re.search(r'[│┌┐└┘├┤|]{3,}', text) or re.search(r'\t{2,}', text):
                    metrics["has_tables"] = True
                
                # Уравнения
                if re.search(r'[∑∏∫√∞≈≠≤≥±×÷]', text):
                    metrics["has_equations"] = True
                
                # Код (ключевые слова языков программирования)
                code_patterns = [
                    r'\bdef\s+\w+\s*\(',  # Python
                    r'\bfunction\s+\w+\s*\(',  # JavaScript
                    r'\bclass\s+\w+\s*[:\{]',  # Class definition
                    r'\bif\s*\(.+\)\s*\{',  # If statement
                    r'\bfor\s*\(.+\)\s*\{',  # For loop
                    r'\bimport\s+\w+',  # Import
                    r'\bfrom\s+\w+\s+import',  # Python import
                    r'\breturn\s+',  # Return
                    r'```[\s\S]*?```',  # Markdown code blocks
                    r'\bprint\s*\(',  # Print
                ]
                for pattern in code_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        metrics["has_code"] = True
                        break
                
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
            
            # Логируем результат OCR
            ocr_pages = metrics.get("ocr_needed_pages", 0)
            if ocr_pages > 0:
                logger.info(f"🔍 Всего страниц с OCR: {ocr_pages}")
            
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
            
            # Определяем сложность по нескольким факторам
            # 1. Средняя длина предложений
            avg_sentence_len = all_chars / max(all_sentences, 1)
            
            # 2. Наличие специальных элементов
            has_special = metrics.get("has_equations") or metrics.get("has_tables")
            
            # 3. Плотность текста
            density = metrics.get("density", "medium")
            
            # Комплексная оценка сложности
            complexity_score = 0
            
            # Длина предложений
            if avg_sentence_len > 120:
                complexity_score += 2  # Очень длинные предложения
            elif avg_sentence_len > 80:
                complexity_score += 1  # Средние
            
            # Специальные элементы
            if has_special:
                complexity_score += 1
            
            # Плотность
            if density == "high":
                complexity_score += 1
            
            # Итоговая сложность
            if complexity_score >= 3:
                metrics["complexity"] = "complex"
            elif complexity_score >= 1:
                metrics["complexity"] = "medium"
            else:
                metrics["complexity"] = "simple"
            
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
    
    total_pages = metrics.get("total_pages", 1)
    heading_count = metrics.get("heading_count", 0)
    paragraph_count = metrics.get("paragraph_count", 0)
    list_count = metrics.get("list_count", 0)
    
    # FAQ: очень много заголовков относительно страниц
    if heading_count > 0:
        heading_ratio = heading_count / max(total_pages, 1)
        if heading_ratio > 3 and paragraph_count < heading_count * 2:
            return "faq"
    
    # Статья: много абзацев, мало заголовков (типичная структура)
    if paragraph_count > 0 and heading_count < paragraph_count * 0.5:
        return "article"
    
    # Отчёт: много таблиц
    if metrics.get("has_tables"):
        return "report"
    
    # Учебник: структурированный документ с заголовками и абзацами
    # Но не просто "много заголовков", а сбалансированная структура
    if heading_count > 3 and paragraph_count > heading_count:
        # Есть и заголовки, и абзацы - скорее учебник
        return "textbook"
    
    # Книга: высокая плотность И много страниц
    if metrics.get("density") == "high" and total_pages > 30:
        return "book"
    
    # Если есть заголовки но мало абзацев - документ с разметкой
    if heading_count > 0 and paragraph_count < heading_count:
        return "document"
    
    return "document"


def _generate_recommendations(metrics: Dict) -> Dict[str, Any]:
    """Генерирует рекомендации по обработке."""
    
    doc_type = metrics.get("document_type", "document")
    density = metrics.get("density", "medium")
    complexity = metrics.get("complexity", "medium")
    total_pages = metrics.get("total_pages", 1)
    
    rec = {
        "chunk_size": 500,
        "overlap": 50,
        "ocr_enabled": False,
        "llm_enabled": True,
        "recommended_llm_model": "gpt-4o-mini",
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
    
    # OCR - только если реально нужен
    ocr_pages = metrics.get("ocr_needed_pages", 0)
    if ocr_pages > 0:
        rec["ocr_enabled"] = True
        rec["rationale"].append(f"🔍 OCR нужен для {ocr_pages} страниц (сканы/изображения)")
    else:
        rec["ocr_enabled"] = False
    
    # Рекомендация по LLM модели
    # ========================================
    # Доступные модели (5 вариантов):
    # - gpt-4o-mini: $0.15/$0.60 - самая дешёвая, быстрая (OpenAI)
    # - claude-haiku-4-5: $0.25/$1.25 - быстрый Claude, дешёвый
    # - gpt-4o: $2.50/$10.00 - качественная OpenAI
    # - claude-sonnet-4-6: $3.00/$15.00 - лучший баланс, 1M контекст
    # - claude-opus-4-6: $15.00/$75.00 - максимальное качество
    # ========================================
    
    # Определяем характеристики документа
    has_code = metrics.get("has_code", False)
    has_equations = metrics.get("has_equations", False)
    is_large_doc = total_pages > 50
    is_very_large_doc = total_pages > 100
    
    # Формируем 4 варианта рекомендаций
    # ========================================
    
    # Вариант 1: ЭКОНОМИЧНЫЙ (OpenAI - самый дешёвый)
    economy_model = "gpt-4o-mini"
    economy_reason = "Самый дешёвый и быстрый (OpenAI)"
    
    # Вариант 2: БЮДЖЕТНЫЙ (Claude Haiku - дешёвый Claude)
    budget_model = "claude-haiku-4-5"
    budget_reason = "Дешёвый Claude, хорошее качество"
    
    # Вариант 3: ОПТИМАЛЬНЫЙ (зависит от типа документа)
    if has_code:
        optimal_model = "claude-sonnet-4-6"
        optimal_reason = "Claude лучше работает с кодом"
    elif has_equations and complexity == "complex":
        optimal_model = "claude-sonnet-4-6"
        optimal_reason = "Claude точнее анализирует формулы"
    elif is_large_doc:
        optimal_model = "claude-sonnet-4-6"
        optimal_reason = "Контекст 1M токенов для больших документов"
    elif complexity == "complex":
        optimal_model = "claude-sonnet-4-6"
        optimal_reason = "Лучшее качество для сложных документов"
    else:
        optimal_model = "gpt-4o"
        optimal_reason = "Баланс качества и скорости (OpenAI)"
    
    # Вариант 4: ПРЕМИУМ (максимальное качество)
    premium_model = "claude-opus-4-6"
    if has_code:
        premium_reason = "Максимальное качество анализа кода"
    elif has_equations:
        premium_reason = "Лучшее понимание математики"
    elif complexity == "complex":
        premium_reason = "Глубокий анализ сложного контента"
    else:
        premium_reason = "Максимальное качество метаданных"
    
    # Выбираем рекомендованную модель (по умолчанию - оптимальная)
    # Но для простых документов - экономичная или бюджетная
    if doc_type in ["faq", "article", "report"] and complexity != "complex":
        rec["recommended_llm_model"] = economy_model
        rec["rationale"].append(f"Рекомендуется: {economy_model} ({economy_reason})")
    else:
        rec["recommended_llm_model"] = optimal_model
        rec["rationale"].append(f"Рекомендуется: {optimal_model} ({optimal_reason})")
    
    # Добавляем все 4 варианта в рекомендации
    rec["llm_options"] = {
        "economy": {
            "model": economy_model,
            "reason": economy_reason,
            "price_per_1m": "$0.15 / $0.60"
        },
        "budget": {
            "model": budget_model,
            "reason": budget_reason,
            "price_per_1m": "$0.25 / $1.25"
        },
        "optimal": {
            "model": optimal_model,
            "reason": optimal_reason,
            "price_per_1m": "$3.00 / $15.00" if "sonnet" in optimal_model else "$2.50 / $10.00"
        },
        "premium": {
            "model": premium_model,
            "reason": premium_reason,
            "price_per_1m": "$15.00 / $75.00"
        }
    }
    
    # Добавляем обоснование для типа документа
    if doc_type == "faq":
        rec["rationale"].append("FAQ: короткие ответы, достаточно простой модели")
    elif doc_type == "article":
        rec["rationale"].append("Статья: стандартная обработка")
    elif doc_type == "report":
        rec["rationale"].append("Отчёт: табличные данные")
    elif doc_type in ["textbook", "book"]:
        rec["rationale"].append(f"{'Сложный' if complexity == 'complex' else 'Стандартный'} учебник/книга")
    
    # Дополнительные факторы
    if has_code:
        rec["rationale"].append("💡 Код: Claude лучше анализирует программный код")
    if has_equations:
        rec["rationale"].append("💡 Формулы: Claude точнее работает с математикой")
    if is_large_doc:
        rec["rationale"].append("💡 Большой документ: Claude Sonnet имеет контекст 1M токенов")
    
    # Таблицы
    if metrics.get("has_tables"):
        rec["rationale"].append("Документ содержит таблицы - рекомендуется preserve_tables=True")
    
    # Прогноз количества чанков
    avg_chars_per_chunk = rec["chunk_size"]
    total_chars = metrics.get("avg_chars_per_page", 2000) * total_pages
    estimated_chunks = int(total_chars / avg_chars_per_chunk * 1.1)  # +10% запас
    rec["estimated_chunks"] = max(estimated_chunks, 10)
    
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


# Цены API (за 1M токенов, приблизительные для proxyAPI)
API_PRICES = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "embedding": 0.02},
    "gpt-4o": {"input": 2.50, "output": 10.00, "embedding": 0.02},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "embedding": 0.02},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00, "embedding": 0.02},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00, "embedding": 0.02},  # Добавлено
    "claude-opus-4-6": {"input": 15.00, "output": 75.00, "embedding": 0.02},
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25, "embedding": 0.02},
}


def estimate_processing_cost(
    estimated_chunks: int,
    llm_model: str = "gpt-4o-mini",
    enable_llm: bool = True,
    enable_vectorization: bool = True
) -> Dict[str, float]:
    """
    Оценивает стоимость обработки в долларах.
    
    Args:
        estimated_chunks: Прогнозируемое количество чанков.
        llm_model: Модель LLM.
        enable_llm: Использовать LLM.
        enable_vectorization: Использовать векторизацию.
    
    Returns:
        Словарь с оценками стоимости.
    """
    result = {
        "llm_cost": 0.0,
        "embedding_cost": 0.0,
        "total_cost": 0.0,
        "llm_tokens_input": 0,
        "llm_tokens_output": 0,
        "embedding_tokens": 0
    }
    
    # LLM стоимость (батчи по 10 чанков)
    if enable_llm:
        # ~500 токенов на чанк (вход) + ~100 токенов на чанк (выход)
        # Батчи по 10 чанков
        batches = (estimated_chunks + 9) // 10
        
        tokens_input = batches * 10 * 500  # ~500 токенов на чанк
        tokens_output = batches * 10 * 100  # ~100 токенов на чанк
        
        # Проверяем, есть ли модель в справочнике
        if llm_model not in API_PRICES:
            logger.warning(f"Модель {llm_model} не найдена в API_PRICES, используется gpt-4o-mini")
            llm_model = "gpt-4o-mini"
        
        prices = API_PRICES.get(llm_model, API_PRICES["gpt-4o-mini"])
        
        llm_cost = (tokens_input / 1_000_000 * prices["input"] +
                    tokens_output / 1_000_000 * prices["output"])
        
        result["llm_cost"] = round(llm_cost, 4)
        result["llm_tokens_input"] = tokens_input
        result["llm_tokens_output"] = tokens_output
    
    # Эмбеддинги
    if enable_vectorization:
        # ~150 токенов на чанк (короткий текст)
        embedding_tokens = estimated_chunks * 150
        embedding_cost = embedding_tokens / 1_000_000 * 0.02  # text-embedding-3-small
        
        result["embedding_cost"] = round(embedding_cost, 4)
        result["embedding_tokens"] = embedding_tokens
    
    result["total_cost"] = round(result["llm_cost"] + result["embedding_cost"], 4)
    
    return result


def estimate_processing_time(
    total_pages: int,
    enable_llm: bool = True,
    enable_vectorization: bool = True,
    llm_model: str = "gpt-4o-mini",
    has_cache: bool = False
) -> Dict[str, float]:
    """
    Оценивает время обработки в секундах.
    
    Args:
        total_pages: Количество страниц.
        enable_llm: Использовать LLM.
        enable_vectorization: Использовать векторизацию.
        llm_model: Модель LLM.
        has_cache: Есть ли кэш эмбеддингов.
    
    Returns:
        Словарь с оценками времени.
    """
    result = {
        "extraction_time": 0.0,
        "llm_time": 0.0,
        "vectorization_time": 0.0,
        "total_time": 0.0
    }
    
    # Извлечение текста: ~0.1 сек/страница
    result["extraction_time"] = total_pages * 0.1
    
    # LLM: ~12-15 сек/страница (gpt-4o-mini), ~15-20 сек/страница (gpt-4o)
    if enable_llm:
        if "mini" in llm_model or "haiku" in llm_model:
            result["llm_time"] = total_pages * 12
        else:
            result["llm_time"] = total_pages * 18
    
    # Векторизация: ~18 сек/страница без кэша, ~0.3 сек/страница с кэшем
    if enable_vectorization:
        if has_cache:
            result["vectorization_time"] = total_pages * 0.3
        else:
            result["vectorization_time"] = total_pages * 18
    
    result["total_time"] = (result["extraction_time"] + 
                            result["llm_time"] + 
                            result["vectorization_time"])
    
    return result


def format_time(seconds: float) -> str:
    """Форматирует время в читаемый вид."""
    if seconds < 60:
        return f"{int(seconds)} сек"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}м {secs}с"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}ч {mins}м"


def format_cost(cost: float) -> str:
    """Форматирует стоимость в читаемый вид."""
    if cost < 0.01:
        # Меньше 1 цента - показываем как "~1¢"
        return "~1¢"
    elif cost < 0.10:
        # Меньше 10 центов - показываем в центах
        cents = cost * 100
        return f"{cents:.1f}¢"
    elif cost < 1.0:
        # Меньше $1 - показываем в центах
        cents = cost * 100
        return f"{cents:.0f}¢"
    else:
        # Больше $1 - показываем в долларах
        return f"${cost:.2f}"
