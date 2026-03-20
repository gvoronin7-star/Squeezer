"""
Генератор резюме документа с использованием LLM.

Создаёт краткое резюме документа для быстрого обзора
и добавляет его в метаданные.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def generate_document_summary(
    pages: List[Dict[str, Any]],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    summary_type: str = "brief"  # "brief" | "detailed" | "bullet"
) -> Dict[str, Any]:
    """
    Генерирует краткое резюме документа.
    
    Args:
        pages: Список страниц с текстом (из process_pdf).
        llm_model: Модель LLM (по умолчанию gpt-4o-mini).
        api_key: API ключ (из env если не указан).
        api_base: Базовый URL API.
        summary_type: Тип резюме:
            - "brief": 2-3 предложения
            - "detailed": абзац
            - "bullet": маркированный список
    
    Returns:
        Словарь с резюме и метаданными.
    """
    from src.llm_chunker import call_llm
    
    logger.info(f"[Summarizer] Генерация резюме документа (тип: {summary_type}, модель: {llm_model})")
    
    # Собираем текст из страниц (первые 3 страницы для экономии)
    texts = []
    total_chars = 0
    for page in pages[:3]:
        text = page.get("text", "") or page.get("normalized_text", "")
        if text:
            texts.append(text[:2000])  # Ограничиваем каждую страницу
            total_chars += len(text)
    
    combined_text = "\n\n".join(texts)
    
    # Формируем промпт в зависимости от типа
    if summary_type == "brief":
        prompt_template = """Создай краткое резюме документа в 2-3 предложениях.

Требования:
- Основная тема документа
- Для кого предназначен
- Ключевой вывод или результат

Текст документа:
---
{text}
---

Верни только резюме, без дополнительного текста."""
    
    elif summary_type == "detailed":
        prompt_template = """Создай подробное резюме документа в одном абзаце.

Требования:
- Основная тема и цель документа
- Структура документа (разделы)
- Ключевые выводы или результаты

Текст документа:
---
{text}
---

Верни только резюме, без дополнительного текста."""
    
    else:  # bullet
        prompt_template = """Создай резюме документа в виде маркированного списка ключевых пунктов.

Требования:
- 5-7 основных пунктов
- Каждый пункт - законченная мысль
- Пункты покрывают основные аспекты документа

Текст документа:
---
{text}
---

Верни только маркированный список."""

    prompt = prompt_template.format(text=combined_text[:6000])
    
    try:
        summary = call_llm(prompt, llm_model, api_key, api_base)
        
        result = {
            "summary": summary.strip(),
            "summary_type": summary_type,
            "llm_model": llm_model,
            "pages_used": min(len(pages), 3),
            "chars_processed": total_chars,
            "metadata": {
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "source": "llm_summarizer"
            }
        }
        
        logger.info(f"[Summarizer] Резюме создано: {len(summary)} символов")
        return result
        
    except Exception as e:
        logger.error(f"[Summarizer] Ошибка: {e}")
        return {
            "summary": "",
            "error": str(e),
            "summary_type": summary_type,
            "llm_model": llm_model
        }


def generate_page_summaries(
    pages: List[Dict[str, Any]],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> List[Dict[str, Any]]:
    """
    Генерирует резюме для каждой страницы документа.
    
    Args:
        pages: Список страниц.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Список страниц с добавленными резюме.
    """
    from src.llm_chunker import call_llm
    
    logger.info(f"[Summarizer] Генерация резюме для {len(pages)} страниц")
    
    results = []
    for i, page in enumerate(pages):
        text = page.get("text", "") or page.get("normalized_text", "")
        if not text or len(text.strip()) < 50:
            results.append({**page, "page_summary": ""})
            continue
        
        prompt = f"""Создай краткое резюме этой страницы документа в 1-2 предложениях.

Страница {page.get('page_number', i+1)}:
---
{text[:1500]}
---

Верни только резюме."""
        
        try:
            summary = call_llm(prompt, llm_model, api_key, api_base)
            results.append({
                **page,
                "page_summary": summary.strip()
            })
        except Exception as e:
            logger.warning(f"[Summarizer] Ошибка для страницы {i+1}: {e}")
            results.append({**page, "page_summary": ""})
    
    return results


def generate_section_summaries(
    structured_text: Dict[str, Any],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> List[Dict[str, Any]]:
    """
    Генерирует резюме для каждого раздела документа.
    
    Args:
        structured_text: Структурированный текст (из structure_text).
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Список резюме разделов.
    """
    from src.llm_chunker import call_llm
    
    logger.info("[Summarizer] Генерация резюме разделов")
    
    sections = []
    
    # Обрабатываем заголовки с их содержимым
    headings = structured_text.get("headings", [])
    paragraphs = structured_text.get("paragraphs", [])
    
    for i, heading in enumerate(headings):
        # Находим соответствующий контент
        content_start = i * 3  # Примерная оценка
        content = paragraphs[content_start:content_start+3] if paragraphs else []
        combined = heading + "\n\n" + " ".join(content[:2])
        
        prompt = f"""Создай краткое резюме этого раздела в 1 предложении.

Раздел:
---
{combined[:800]}
---

Верни только резюме."""
        
        try:
            summary = call_llm(prompt, llm_model, api_key, api_base)
            sections.append({
                "heading": heading,
                "summary": summary.strip(),
                "type": "section"
            })
        except Exception as e:
            sections.append({
                "heading": heading,
                "summary": "",
                "error": str(e)
            })
    
    return sections


# Функция для добавления в pipeline
def add_summary_to_document(
    processed_result: Dict[str, Any],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> Dict[str, Any]:
    """
    Добавляет резюме к результату обработки PDF.
    
    Args:
        processed_result: Результат из process_pdf().
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Результат с добавленным document_summary.
    """
    pages = processed_result.get("pages", [])
    if not pages:
        return processed_result
    
    summary_result = generate_document_summary(pages, llm_model, api_key, api_base)
    
    # Добавляем к результату
    processed_result["document_summary"] = summary_result
    
    # Также добавляем к каждому чанку если есть
    if "chunks" in processed_result:
        for chunk in processed_result["chunks"]:
            chunk["metadata"]["document_summary"] = summary_result.get("summary", "")[:200]
    
    return processed_result
