"""
Интеллектуальный чанкер с использованием LLM.

Разбивает текст на смысловые фрагменты вместо механического
разбиения по размеру. Использует LLM для определения
логических границ чанков.
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


def smart_chunk_with_llm(
    text: str,
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    max_chunks: int = 20
) -> List[Dict[str, Any]]:
    """
    Разбивает текст на смысловые чанки с использованием LLM.
    
    В отличие от механического разбиения (по символам),
    LLM анализирует смысл и разбивает по логическим границам:
    - Завершённые мысли
    - Логические абзацы
    - Тематические блоки
    
    Args:
        text: Текст для разбиения.
        llm_model: Модель LLM (по умолчанию gpt-4o-mini).
        api_key: API ключ (из env если не указан).
        api_base: Базовый URL API.
        max_chunks: Максимальное количество чанков.
    
    Returns:
        Список чанков с текстом и метаданными.
    """
    from src.llm_chunker import call_llm
    
    logger.info(f"[Smart Chunking] Начало смыслового разбиения (модель: {llm_model})")
    
    # Ограничиваем длину текста для LLM
    text_preview = text[:8000] if len(text) > 8000 else text
    
    prompt = f"""Разбей текст на логические смысловые фрагменты для RAG-системы.

Требования:
1. Каждый чанк должен быть самодостаточным - содержать законченную мысль
2. Разбивай по логическим границам (не посреди предложения)
3. Учитывай структуру документа (заголовки, абзацы, списки)
4. Максимум {max_chunks} чанков

Верни JSON массив объектов с полями:
- "text": текст чанка
- "summary": краткое резюме чанка (1-2 предложения)
- "keywords": ключевые слова (массив 3-5 слов)
- "reason": причина разбиения (почему именно здесь граница)

Текст для разбиения:
---
{text_preview}
---

Верни только JSON массив, без дополнительного текста."""

    try:
        response = call_llm(prompt, llm_model, api_key, api_base)
        
        # Парсим JSON из ответа
        import json
        import re
        
        # Ищем JSON массив в ответе
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            chunks_data = json.loads(json_match.group())
        else:
            # Пробуем распарсить весь ответ как JSON
            chunks_data = json.loads(response)
        
        # Добавляем метаданные
        result = []
        for idx, chunk in enumerate(chunks_data):
            result.append({
                "text": chunk.get("text", ""),
                "type": "smart_chunk",
                "summary": chunk.get("summary", ""),
                "keywords": chunk.get("keywords", []),
                "split_reason": chunk.get("reason", ""),
                "metadata": {
                    "chunk_id": f"smart_chunk_{idx:03d}",
                    "chunk_type": "smart_chunk",
                    "char_count": len(chunk.get("text", "")),
                    "word_count": len(chunk.get("text", "").split()),
                    "source": "llm_smart_chunking"
                }
            })
        
        logger.info(f"[Smart Chunking] Создано чанков: {len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"[Smart Chunking] Ошибка: {e}")
        # Возвращаем пустой список при ошибке
        return []


def smart_chunk_batch(
    texts: List[str],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> List[List[Dict[str, Any]]]:
    """
    Пакетная обработка нескольких текстов через интеллектуальный чанкер.
    
    Args:
        texts: Список текстов для обработки.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL API.
    
    Returns:
        Список списков чанков для каждого текста.
    """
    results = []
    for i, text in enumerate(texts):
        logger.info(f"[Smart Chunking] Обработка текста {i+1}/{len(texts)}")
        chunks = smart_chunk_with_llm(text, llm_model, api_key, api_base)
        results.append(chunks)
    
    return results


# Функция для обратной совместимости
def create_smart_chunker(config: Dict[str, Any] = None):
    """
    Создаёт интеллектуальный чанкер с конфигурацией.
    
    Args:
        config: Словарь с настройками (llm_model, api_key, api_base).
    
    Returns:
        Функцию smart_chunk_with_llm с предустановленными параметрами.
    """
    config = config or {}
    
    def chunker(text: str, **kwargs):
        return smart_chunk_with_llm(
            text,
            llm_model=kwargs.get("llm_model", config.get("llm_model", "gpt-4o-mini")),
            api_key=kwargs.get("api_key", config.get("api_key")),
            api_base=kwargs.get("api_base", config.get("api_base", "https://openai.api.proxyapi.ru/v1")),
            max_chunks=kwargs.get("max_chunks", config.get("max_chunks", 20))
        )
    
    return chunker
