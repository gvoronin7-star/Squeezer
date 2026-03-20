"""
Автоматическая классификация и категоризация документов с использованием LLM.

Автоматически определяет:
- Тип документа
- Тематическую категорию
- Теги
- Целевую аудиторию
- Уровень сложности
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

# Категории документов
DOCUMENT_TYPES = [
    "academic",      # Академический/научный
    "technical",     # Технический/документация
    "business",      # Бизнес/финансы
    "legal",         # Юридический
    "news",          # Новости
    "educational",   # Образовательный
    "manual",        # Руководство/инструкция
    "report",        # Отчёт
    "article",       # Статья
    "book",          # Книга
    "faq",           # FAQ
    "presentation",  # Презентация
    "other"          # Другое
]

THEMATIC_CATEGORIES = [
    "technology", "science", "business", "finance", "law", "medicine",
    "education", "marketing", "hr", "engineering", "programming",
    "data_science", "ai_ml", "security", "cloud", "devops",
    "design", "management", "sales", "customer_service", "other"
]

TARGET_AUDIENCE = [
    "beginner",      # Начинающие
    "intermediate",  # Средний уровень
    "advanced",      # Продвинутые
    "expert",        # Эксперты
    "general"        # Общая аудитория
]


def classify_document(
    pages: List[Dict[str, Any]],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> Dict[str, Any]:
    """
    Классифицирует документ по нескольким параметрам.
    
    Args:
        pages: Список страниц документа.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Словарь с классификацией:
        {
            "document_type": "technical",
            "thematic_category": "programming",
            "tags": ["python", "api", "tutorial"],
            "target_audience": "intermediate",
            "complexity": "medium",
            "language": "ru",
            "confidence": 0.85
        }
    """
    from src.llm_chunker import call_llm
    
    logger.info(f"[Classifier] Классификация документа (модель: {llm_model})")
    
    # Собираем текст
    texts = []
    for page in pages[:2]:
        text = page.get("text", "") or page.get("normalized_text", "")
        if text:
            texts.append(text[:1500])
    
    combined_text = "\n\n".join(texts)
    
    prompt = f"""Проанализируй документ и определи его характеристики.

Доступные типы документов: {', '.join(DOCUMENT_TYPES)}
Тематические категории: {', '.join(THEMATIC_CATEGORIES)}
Целевая аудитория: {', '.join(TARGET_AUDIENCE)}

Верни JSON объект с полями:
- "document_type": тип документа (один из списка)
- "thematic_category": тематика (один из списка)
- "tags": массив 3-7 ключевых тегов (нижний регистр, на английском)
- "target_audience": целевая аудитория (одна из списка)
- "complexity": сложность (low/medium/high)
- "language": язык документа (ru/en/mixed)

Документ:
---
{combined_text[:4000]}
---

Верни только JSON."""

    try:
        import json
        import re
        
        response = call_llm(prompt, llm_model, api_key, api_base)
        
        if not response or not response.strip():
            raise ValueError("Empty response from LLM")
        
        # Ищем JSON в ответе
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            try:
                classification = json.loads(json_match.group())
            except json.JSONDecodeError:
                # Пробуем найти любой JSON объект
                classification = {"document_type": "other", "thematic_category": "other", "tags": [], "target_audience": "general", "complexity": "medium"}
        else:
            classification = json.loads(response)
        
        # Валидация и значения по умолчанию
        result = {
            "document_type": classification.get("document_type", "other"),
            "thematic_category": classification.get("thematic_category", "other"),
            "tags": classification.get("tags", [])[:7],
            "target_audience": classification.get("target_audience", "general"),
            "complexity": classification.get("complexity", "medium"),
            "language": classification.get("language", "unknown"),
            "confidence": classification.get("confidence", 0.7)
        }
        
        logger.info(f"[Classifier] Классификация: {result['document_type']} / {result['thematic_category']}")
        return result
        
    except Exception as e:
        logger.error(f"[Classifier] Ошибка: {e}")
        return {
            "document_type": "other",
            "thematic_category": "other",
            "tags": [],
            "target_audience": "general",
            "complexity": "medium",
            "language": "unknown",
            "confidence": 0.0,
            "error": str(e)
        }


def suggest_chunk_parameters(
    classification: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Предлагает оптимальные параметры чанкинга на основе классификации.
    
    Args:
        classification: Результат classify_document().
    
    Returns:
        Словарь с рекомендуемыми параметрами.
    """
    doc_type = classification.get("document_type", "other")
    complexity = classification.get("complexity", "medium")
    
    # Параметры по умолчанию
    params = {
        "chunk_size": 500,
        "overlap": 50,
        "strategy": "hybrid"
    }
    
    # Корректируем на основе типа документа
    if doc_type == "faq":
        params["chunk_size"] = 250
        params["overlap"] = 30
        params["strategy"] = "semantic"
    
    elif doc_type == "technical":
        params["chunk_size"] = 600
        params["overlap"] = 80
        params["strategy"] = "hybrid"
    
    elif doc_type == "academic":
        params["chunk_size"] = 700
        params["overlap"] = 100
        params["strategy"] = "semantic"
    
    elif doc_type == "manual":
        params["chunk_size"] = 400
        params["overlap"] = 50
        params["strategy"] = "hybrid"
    
    # Корректируем на основе сложности
    if complexity == "high":
        params["chunk_size"] = min(params["chunk_size"] + 100, 800)
    
    elif complexity == "low":
        params["chunk_size"] = max(params["chunk_size"] - 100, 300)
    
    return params


def add_classification_to_chunks(
    chunks: List[Dict[str, Any]],
    classification: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Добавляет классификацию в метаданные чанков.
    
    Args:
        chunks: Список чанков.
        classification: Результат classify_document().
    
    Returns:
        Чанки с добавленной классификацией.
    """
    for chunk in chunks:
        if "metadata" not in chunk:
            chunk["metadata"] = {}
        
        chunk["metadata"]["classification"] = {
            "document_type": classification.get("document_type"),
            "thematic_category": classification.get("thematic_category"),
            "tags": classification.get("tags", [])[:5],
            "target_audience": classification.get("target_audience"),
            "complexity": classification.get("complexity")
        }
    
    return chunks


def batch_classify_documents(
    documents: List[Dict[str, Any]],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> List[Dict[str, Any]]:
    """
    Пакетная классификация нескольких документов.
    
    Args:
        documents: Список документов (каждый - dict с ключом 'pages').
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Список классификаций для каждого документа.
    """
    results = []
    for i, doc in enumerate(documents):
        logger.info(f"[Classifier] Классификация документа {i+1}/{len(documents)}")
        pages = doc.get("pages", [])
        classification = classify_document(pages, llm_model, api_key, api_base)
        results.append(classification)
    
    return results


# Функция для получения всех доступных категорий
def get_available_categories() -> Dict[str, List[str]]:
    """
    Возвращает все доступные категории для классификации.
    
    Returns:
        Словарь с категориями.
    """
    return {
        "document_types": DOCUMENT_TYPES,
        "thematic_categories": THEMATIC_CATEGORIES,
        "target_audience": TARGET_AUDIENCE,
        "complexity_levels": ["low", "medium", "high"]
    }
