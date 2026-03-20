"""
Централизованный реестр LLM промптов.

Этот файл содержит все промпты, используемые в системе для обращения к LLM.
Промпты сгруппированы по функциональному назначению.

Использование:
    from src.llm_prompts import (
        CHUNKING_PROMPTS,
        SUMMARIZATION_PROMPTS,
        ENTITY_EXTRACTION_PROMPTS,
        CLASSIFICATION_PROMPTS,
        QUERY_REWRITING_PROMPTS,
        ANSWER_GENERATION_PROMPTS,
        HYDE_PROMPTS
    )

Автор: Line_GV
Версия: 1.0.0
Дата: 2026-03-07
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class PromptCategory(Enum):
    """Категории промптов."""
    CHUNKING = "chunking"           # Разбиение текста на чанки
    SUMMARIZATION = "summarization" # Генерация резюме
    ENTITY_EXTRACTION = "entity_extraction"  # Извлечение сущностей
    CLASSIFICATION = "classification"        # Классификация документов
    QUERY_REWRITING = "query_rewriting"       # Перезапись запросов
    ANSWER_GENERATION = "answer_generation"   # Генерация ответов
    HYDE = "hyde"                             # Гипотетические ответы
    METADATA = "metadata"                     # Обогащение метаданных


@dataclass
class PromptTemplate:
    """Шаблон промпта."""
    name: str
    category: PromptCategory
    description: str
    prompt: str
    expected_output: str  # Описание ожидаемого формата вывода
    parameters: Dict[str, Any]  # Параметры по умолчанию
    examples: Optional[List[Dict[str, str]]] = None  # Примеры вход/выход


# =============================================================================
# ПРОМПТЫ ДЛЯ ЧАНКИНГА (Разбиение текста)
# =============================================================================

CHUNKING_PROMPTS = {
    """
    Промпты для интеллектуального разбиения текста на смысловые фрагменты.
    Используются в: src/smart_chunker.py
    """
    
    "smart_chunking": PromptTemplate(
        name="smart_chunking",
        category=PromptCategory.CHUNKING,
        description="Разбиение текста на логические смысловые фрагменты для RAG",
        prompt="""Разбей текст на логические смысловые фрагменты для RAG-системы.

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
{text}
---

Верни только JSON массив, без дополнительного текста.""",
        expected_output="JSON массив объектов с полями: text, summary, keywords, reason",
        parameters={"max_chunks": 20, "temperature": 0.2},
        examples=[
            {
                "input": "Длинный текст документа...",
                "output": '[{"text": "...", "summary": "...", "keywords": [...], "reason": "..."}]'
            }
        ]
    ),
    
    "simple_chunking": PromptTemplate(
        name="simple_chunking",
        category=PromptCategory.CHUNKING,
        description="Простое смысловое разбиение текста",
        prompt="""Разбей текст на смысловые блоки.
Каждый блок должен быть логически завершённым.
Максимальный размер: {max_size} символов.
Верни только список блоков через | разделитель.

Текст:
{text}""",
        expected_output="Текстовые блоки, разделённые символом |",
        parameters={"max_size": 500, "temperature": 0.2}
    ),
}


# =============================================================================
# ПРОМПТЫ ДЛЯ СУММАРИЗАЦИИ (Генерация резюме)
# =============================================================================

SUMMARIZATION_PROMPTS = {
    """
    Промпты для генерации резюме документов, страниц и разделов.
    Используются в: src/summarizer.py
    """
    
    "brief_summary": PromptTemplate(
        name="brief_summary",
        category=PromptCategory.SUMMARIZATION,
        description="Краткое резюме документа в 2-3 предложениях",
        prompt="""Создай краткое резюме документа в 2-3 предложениях.

Требования:
- Основная тема документа
- Для кого предназначен
- Ключевой вывод или результат

Текст документа:
---
{text}
---

Верни только резюме, без дополнительного текста.""",
        expected_output="Текст резюме (2-3 предложения)",
        parameters={"temperature": 0.3, "max_tokens": 200}
    ),
    
    "detailed_summary": PromptTemplate(
        name="detailed_summary",
        category=PromptCategory.SUMMARIZATION,
        description="Подробное резюме документа в одном абзаце",
        prompt="""Создай подробное резюме документа в одном абзаце.

Требования:
- Основная тема и цель документа
- Структура документа (разделы)
- Ключевые выводы или результаты

Текст документа:
---
{text}
---

Верни только резюме, без дополнительного текста.""",
        expected_output="Текст резюме (один абзац)",
        parameters={"temperature": 0.3, "max_tokens": 500}
    ),
    
    "bullet_summary": PromptTemplate(
        name="bullet_summary",
        category=PromptCategory.SUMMARIZATION,
        description="Резюме документа в виде маркированного списка",
        prompt="""Создай резюме документа в виде маркированного списка ключевых пунктов.

Требования:
- 5-7 основных пунктов
- Каждый пункт - законченная мысль
- Пункты покрывают основные аспекты документа

Текст документа:
---
{text}
---

Верни только маркированный список.""",
        expected_output="Маркированный список (5-7 пунктов)",
        parameters={"temperature": 0.3, "max_tokens": 500}
    ),
    
    "page_summary": PromptTemplate(
        name="page_summary",
        category=PromptCategory.SUMMARIZATION,
        description="Краткое резюме одной страницы документа",
        prompt="""Создай краткое резюме этой страницы документа в 1-2 предложениях.

Страница {page_number}:
---
{text}
---

Верни только резюме.""",
        expected_output="Текст резюме (1-2 предложения)",
        parameters={"temperature": 0.3, "max_tokens": 100}
    ),
    
    "section_summary": PromptTemplate(
        name="section_summary",
        category=PromptCategory.SUMMARIZATION,
        description="Резюме раздела документа",
        prompt="""Создай краткое резюме этого раздела в 1 предложении.

Раздел:
---
{text}
---

Верни только резюме.""",
        expected_output="Текст резюме (1 предложение)",
        parameters={"temperature": 0.3, "max_tokens": 100}
    ),
}


# =============================================================================
# ПРОМПТЫ ДЛЯ ИЗВЛЕЧЕНИЯ СУЩНОСТЕЙ (NER)
# =============================================================================

ENTITY_EXTRACTION_PROMPTS = {
    """
    Промпты для извлечения именованных сущностей из текста.
    Используются в: src/entity_extractor.py
    """
    
    "extract_entities": PromptTemplate(
        name="extract_entities",
        category=PromptCategory.ENTITY_EXTRACTION,
        description="Извлечение именованных сущностей из текста",
        prompt="""Извлеки из текста именованные сущности указанных типов.

Типы сущностей для извлечения: {entity_types}

Верни JSON объект, где ключи - типы сущностей, значения - массивы найденных сущностей.
Если сущности не найдены, верни пустой массив.

Текст:
---
{text}
---

Верни только JSON, без дополнительного текста.""",
        expected_output='JSON объект: {"dates": [...], "persons": [...], "organizations": [...], ...}',
        parameters={
            "entity_types": ["dates", "persons", "organizations", "locations", "amounts", "emails", "phones", "urls"],
            "temperature": 0.1,
            "max_tokens": 1000
        }
    ),
}


# =============================================================================
# ПРОМПТЫ ДЛЯ КЛАССИФИКАЦИИ
# =============================================================================

CLASSIFICATION_PROMPTS = {
    """
    Промпты для классификации документов.
    Используются в: src/metadata_classifier.py
    """
    
    "classify_document": PromptTemplate(
        name="classify_document",
        category=PromptCategory.CLASSIFICATION,
        description="Классификация документа по нескольким параметрам",
        prompt="""Проанализируй документ и определи его характеристики.

Доступные типы документов: {document_types}
Тематические категории: {thematic_categories}
Целевая аудитория: {target_audience}

Верни JSON объект с полями:
- "document_type": тип документа (один из списка)
- "thematic_category": тематика (один из списка)
- "tags": массив 3-7 ключевых тегов (нижний регистр, на английском)
- "target_audience": целевая аудитория (одна из списка)
- "complexity": сложность (low/medium/high)
- "language": язык документа (ru/en/mixed)

Документ:
---
{text}
---

Верни только JSON.""",
        expected_output='JSON: {"document_type": "...", "thematic_category": "...", "tags": [...], ...}',
        parameters={
            "document_types": ["academic", "technical", "business", "legal", "news", "educational", "manual", "report", "article", "book", "faq", "presentation", "other"],
            "thematic_categories": ["technology", "science", "business", "finance", "law", "medicine", "education", "marketing", "hr", "engineering", "programming", "data_science", "ai_ml", "security", "cloud", "devops", "design", "management", "sales", "customer_service", "other"],
            "target_audience": ["beginner", "intermediate", "advanced", "expert", "general"],
            "temperature": 0.3,
            "max_tokens": 500
        }
    ),
}


# =============================================================================
# ПРОМПТЫ ДЛЯ ПЕРЕЗАПИСИ ЗАПРОСОВ
# =============================================================================

QUERY_REWRITING_PROMPTS = {
    """
    Промпты для перезаписи (улучшения) поисковых запросов.
    Используются в: src/query_rewriter.py
    """
    
    "expand_query": PromptTemplate(
        name="expand_query",
        category=PromptCategory.QUERY_REWRITING,
        description="Расширение запроса синонимами и контекстом",
        prompt="""Перепиши запрос так, чтобы он был более информативным для семантического поиска в базе знаний.

Правила:
1. Добавь синонимы и связанные термины
2. Расширь аббревиатуры
3. Добавь контекстные уточнения
4. Используй более формальный стиль

Пример:
Оригинал: "как создать бота"
Переписанный: "как создать telegram бота с помощью python, инструкция по созданию"

Оригинал: "что такое rag"
Переписанный: "что такое RAG retrieval augmented generation, объяснение концепции"

Оригинал: "{query}"
Переписанный:""",
        expected_output="Переписанный запрос (1 строка)",
        parameters={"temperature": 0.3, "max_tokens": 200}
    ),
    
    "split_query": PromptTemplate(
        name="split_query",
        category=PromptCategory.QUERY_REWRITING,
        description="Разбиение сложного запроса на подзапросы",
        prompt="""Раздели сложный запрос на несколько простых подзапросов для поиска в базе знаний.

Правила:
1. Каждый подзапрос должен быть самодостаточным
2. Сохрани все аспекты оригинального запроса
3. Используй формальный стиль

Пример:
Оригинал: "чем отличается python от javascript"
Подзапросы:
- "что такое python, описание языка"
- "что такое javascript, описание языка"
- "сравнение python и javascript"

Оригинал: "{query}"
Подзапросы:""",
        expected_output="Список подзапросов (по одному на строке)",
        parameters={"temperature": 0.3, "max_tokens": 300}
    ),
    
    "clarify_query": PromptTemplate(
        name="clarify_query",
        category=PromptCategory.QUERY_REWRITING,
        description="Уточнение неопределённых запросов",
        prompt="""Перепиши неопределённый запрос так, чтобы он был понятен без контекста.

Правила:
1. Замени местоимения на конкретные существительные
2. Добавь уточняющие детали
3. Сохрани смысл запроса

Пример:
Оригинал: "как это работает"
Переписанный: "как работает технология RAG"

Оригинал: "{query}"
Переписанный:""",
        expected_output="Переписанный запрос (1 строка)",
        parameters={"temperature": 0.3, "max_tokens": 200}
    ),
}


# =============================================================================
# ПРОМПТЫ ДЛЯ ГЕНЕРАЦИИ ОТВЕТОВ
# =============================================================================

ANSWER_GENERATION_PROMPTS = {
    """
    Промпты для генерации ответов на основе найденных документов.
    Используются в: src/answer_generator.py
    """
    
    "generate_answer_with_citations": PromptTemplate(
        name="generate_answer_with_citations",
        category=PromptCategory.ANSWER_GENERATION,
        description="Генерация ответа с цитированием источников",
        prompt="""Ответь на вопрос на основе предоставленных документов.

Вопрос: {query}

Документы:
{context}

{citation_instruction}
Требования к ответу:
- Отвечай только на основе предоставленных документов
- Если информации недостаточно, честно об этом скажи
- Ответ должен быть точным и информативным
- Используй цитаты из документов где уместно

Оцени свою уверенность в ответе от 0 до 1 в конце ответа в формате: [Уверенность: 0.XX]

Ответ:""",
        expected_output="Текст ответа с цитатами и оценкой уверенности",
        parameters={
            "citation_instruction": "Для каждого утверждения в ответе укажи источник в формате [ID: chunk_XXX, стр. Y].\nИспользуй информацию из документов, не добавляй выдумок.\n",
            "temperature": 0.3,
            "max_tokens": 1000
        }
    ),
}


# =============================================================================
# ПРОМПТЫ ДЛЯ HYDE (Hypothetical Document Embeddings)
# =============================================================================

HYDE_PROMPTS = {
    """
    Промпты для HyDE (Hypothetical Document Embeddings).
    Используются в: src/hyde_search.py
    """
    
    "generate_hypothetical_answer": PromptTemplate(
        name="generate_hypothetical_answer",
        category=PromptCategory.HYDE,
        description="Генерация гипотетического идеального ответа",
        prompt="""Ты - эксперт, который отвечает на вопросы на основе документов.

Сгенерируй ПОДРОБНЫЙ и ПРАВИЛЬНЫЙ ответ на следующий вопрос, 
как будто ты нашёл идеальный документ с ответом.

Вопрос: {query}

Требования к ответу:
- Ответ должен быть развёрнутым (100-300 слов)
- Включай конкретику, детали, примеры
- Пиши так, будто это цитата из учебника или документации
- Используй правильную терминологию

Ответ:""",
        expected_output="Развёрнутый текст ответа (100-300 слов)",
        parameters={"temperature": 0.7, "max_tokens": 500}
    ),
}


# =============================================================================
# ПРОМПТЫ ДЛЯ ОБОГАЩЕНИЯ МЕТАДАННЫХ
# =============================================================================

METADATA_PROMPTS = {
    """
    Промпты для обогащения метаданных чанков.
    Используются в: src/llm_chunker.py
    """
    
    "enhance_metadata": PromptTemplate(
        name="enhance_metadata",
        category=PromptCategory.METADATA,
        description="Извлечение метаданных из чанков",
        prompt="""For each text chunk, extract brief metadata in Russian.
Return JSON array (no markdown):

[
  {{
    "chunk_id": 0,
    "summary": "brief 1-2 sentence summary in Russian",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "intent": "main purpose of this fragment"
  }},
  ...
]

Chunks:
{chunks_text}""",
        expected_output="JSON массив объектов с метаданными",
        parameters={"temperature": 0.3, "max_tokens": 2000}
    ),
}


# =============================================================================
# ОБЪЕДИНЁННЫЙ СЛОВАРЬ ВСЕХ ПРОМПТОВ
# =============================================================================

ALL_PROMPTS = {
    **CHUNKING_PROMPTS,
    **SUMMARIZATION_PROMPTS,
    **ENTITY_EXTRACTION_PROMPTS,
    **CLASSIFICATION_PROMPTS,
    **QUERY_REWRITING_PROMPTS,
    **ANSWER_GENERATION_PROMPTS,
    **HYDE_PROMPTS,
    **METADATA_PROMPTS,
}


# =============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПРОМПТАМИ
# =============================================================================

def get_prompt(
    name: str,
    variables: Dict[str, Any] = None,
    parameters: Dict[str, Any] = None
) -> tuple:
    """
    Получает промпт по имени с подстановкой переменных.
    
    Args:
        name: Имя промпта.
        variables: Переменные для подстановки в промпт.
        parameters: Дополнительные параметры (temperature, max_tokens).
    
    Returns:
        Кортеж (prompt: str, params: dict).
    
    Example:
        prompt, params = get_prompt("brief_summary", {"text": "Документ..."})
    """
    if name not in ALL_PROMPTS:
        raise ValueError(f"Промпт '{name}' не найден. Доступные: {list(ALL_PROMPTS.keys())}")
    
    template = ALL_PROMPTS[name]
    
    # Подставляем переменные
    prompt = template.prompt
    if variables:
        prompt = prompt.format(**variables)
    
    # Объединяем параметры
    params = {**template.parameters}
    if parameters:
        params.update(parameters)
    
    return prompt, params


def get_prompts_by_category(category: PromptCategory) -> Dict[str, PromptTemplate]:
    """
    Получает все промпты указанной категории.
    
    Args:
        category: Категория промптов.
    
    Returns:
        Словарь промптов категории.
    """
    return {k: v for k, v in ALL_PROMPTS.items() if v.category == category}


def list_all_prompts() -> List[Dict[str, Any]]:
    """
    Возвращает список всех промптов с описанием.
    
    Returns:
        Список словарей с информацией о промптах.
    """
    return [
        {
            "name": name,
            "category": template.category.value,
            "description": template.description,
            "expected_output": template.expected_output
        }
        for name, template in ALL_PROMPTS.items()
    ]


# =============================================================================
# ТЕСТИРОВАНИЕ
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("LLM PROMPTS REGISTRY")
    print("=" * 70)
    
    # Выводим статистику
    categories = {}
    for name, template in ALL_PROMPTS.items():
        cat = template.category.value
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nПромптов по категориям:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    
    print(f"\nВсего промптов: {len(ALL_PROMPTS)}")
    
    # Пример использования
    print("\n" + "=" * 70)
    print("ПРИМЕР ИСПОЛЬЗОВАНИЯ")
    print("=" * 70)
    
    prompt, params = get_prompt("brief_summary", {"text": "Пример текста документа..."})
    print(f"\nПромпт (brief_summary):\n{prompt[:200]}...")
    print(f"\nПараметры: {params}")
