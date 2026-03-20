"""
Извлечение именованных сущностей (NER) с использованием LLM.

Извлекает из текста:
- Даты
- Имена людей
- Организации
- Места
- Суммы/числа
- Email/телефоны
- URLs
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def extract_entities(
    text: str,
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    entity_types: List[str] = None
) -> Dict[str, List[str]]:
    """
    Извлекает именованные сущности из текста.
    
    Args:
        text: Текст для анализа.
        llm_model: Модель LLM (по умолчанию gpt-4o-mini).
        api_key: API ключ (из env если не указан).
        api_base: Базовый URL API.
        entity_types: Типы сущностей для извлечения.
                      По умолчанию: все типы.
    
    Returns:
        Словарь с типами сущностей и их значениями:
        {
            "dates": ["15 марта 2024", ...],
            "persons": ["Иван Иванов", ...],
            "organizations": ["ООО Рога и копыта", ...],
            "locations": ["Москва", ...],
            "amounts": ["100 000 руб", ...],
            "emails": ["email@example.com", ...],
            "phones": ["+7 999 123-45-67", ...],
            "urls": ["https://example.com", ...]
        }
    """
    from src.llm_chunker import call_llm
    
    if entity_types is None:
        entity_types = ["dates", "persons", "organizations", "locations", "amounts", "emails", "phones", "urls"]
    
    logger.info(f"[NER] Извлечение сущностей из текста ({len(text)} символов)")
    
    # Ограничиваем длину текста
    text_preview = text[:5000] if len(text) > 5000 else text
    
    prompt = f"""Извлеки из текста именованные сущности указанных типов.

Типы сущностей для извлечения: {', '.join(entity_types)}

Верни JSON объект, где ключи - типы сущностей, значения - массивы найденных сущностей.
Если сущности не найдены, верни пустой массив.

Текст:
---
{text_preview}
---

Верни только JSON, без дополнительного текста."""

    try:
        import json
        import re as regex_module
        
        response = call_llm(prompt, llm_model, api_key, api_base)
        
        # Ищем JSON в ответе
        json_match = regex_module.search(r'\{[\s\S]*\}', response)
        if json_match:
            entities = json.loads(json_match.group())
        else:
            entities = json.loads(response)
        
        # Дополнительная очистка - удаляем дубликаты
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        logger.info(f"[NER] Найдено сущностей: {sum(len(v) for v in entities.values())}")
        return entities
        
    except Exception as e:
        logger.error(f"[NER] Ошибка: {e}")
        # Возвращаем пустой словарь
        return {etype: [] for etype in entity_types}


def extract_entities_from_chunks(
    chunks: List[Dict[str, Any]],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    sample_size: int = 10
) -> Dict[str, Any]:
    """
    Извлекает сущности из чанков документа.
    
    Args:
        chunks: Список чанков.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
        sample_size: Количество чанков для анализа (0 = все).
    
    Returns:
        Словарь с агрегированными сущностями и статистикой.
    """
    logger.info(f"[NER] Извлечение сущностей из {len(chunks)} чанков")
    
    # Объединяем текст из чанков
    if sample_size > 0:
        text = " ".join([c.get("text", "")[:500] for c in chunks[:sample_size]])
    else:
        text = " ".join([c.get("text", "")[:300] for c in chunks])
    
    entities = extract_entities(text, llm_model, api_key, api_base)
    
    # Добавляем статистику
    result = {
        "entities": entities,
        "stats": {
            "total_entities": sum(len(v) for v in entities.values()),
            "chunks_analyzed": min(sample_size, len(chunks)) if sample_size > 0 else len(chunks),
            "by_type": {k: len(v) for k, v in entities.items()}
        }
    }
    
    return result


def add_entities_to_chunks(
    chunks: List[Dict[str, Any]],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> List[Dict[str, Any]]:
    """
    Добавляет извлечённые сущности в метаданные чанков.
    
    Args:
        chunks: Список чанков.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Чанки с добавленными сущностями в metadata.
    """
    logger.info(f"[NER] Добавление сущностей в {len(chunks)} чанков")
    
    # Объединяем текст для анализа
    combined_text = " ".join([c.get("text", "") for c in chunks[:20]])
    
    entities = extract_entities(combined_text, llm_model, api_key, api_base)
    
    # Добавляем сущности в каждый чанк
    for chunk in chunks:
        if "metadata" not in chunk:
            chunk["metadata"] = {}
        
        chunk["metadata"]["entities"] = {
            "dates": entities.get("dates", [])[:3],
            "persons": entities.get("persons", [])[:3],
            "organizations": entities.get("organizations", [])[:3],
            "locations": entities.get("locations", [])[:3],
            "amounts": entities.get("amounts", [])[:2]
        }
    
    logger.info(f"[NER] Сущности добавлены в чанки")
    return chunks


def create_entity_index(
    entities: Dict[str, List[str]]
) -> Dict[str, int]:
    """
    Создаёт индекс частотности сущностей.
    
    Args:
        entities: Словарь сущностей.
    
    Returns:
        Словарь {сущность: частота}.
    """
    index = {}
    for entity_list in entities.values():
        for entity in entity_list:
            entity_lower = entity.lower()
            index[entity_lower] = index.get(entity_lower, 0) + 1
    
    # Сортируем по частоте
    return dict(sorted(index.items(), key=lambda x: x[1], reverse=True))
