"""
Модуль Query Rewriting для улучшения качества поиска.

Переписывает запросы пользователя для более точного поиска в RAG.
"""

import logging
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    Переписывает запросы для улучшения поиска.
    
    Стратегии:
    1. Расширение синонимами
    2. Добавление контекста
    3. Разбиение сложных запросов
    4. Уточнение неопределённых терминов
    """
    
    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1"
    ):
        """
        Инициализация переписывателя.
        
        Args:
            llm_model: Модель LLM.
            api_key: API ключ.
            api_base: Базовый URL.
        """
        self.llm_model = llm_model
        self.api_key = api_key
        self.api_base = api_base
        
        # Загружаем .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        import os
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
    
    def is_available(self) -> bool:
        """Проверяет доступность LLM."""
        return bool(self.api_key)
    
    def rewrite(self, query: str, strategy: str = "auto") -> Dict[str, Any]:
        """
        Переписывает запрос.
        
        Args:
            query: Оригинальный запрос.
            strategy: Стратегия перезаписи ('auto', 'expand', 'split', 'clarify').
        
        Returns:
            Словарь с переписанным запросом и метаданными.
        """
        if not self.is_available():
            logger.warning("LLM недоступен, возвращаем оригинальный запрос")
            return {
                'original': query,
                'rewritten': query,
                'strategy': 'none',
                'reason': 'LLM not available'
            }
        
        if strategy == "auto":
            strategy = self._determine_strategy(query)
        
        if strategy == "expand":
            return self._expand_query(query)
        elif strategy == "split":
            return self._split_query(query)
        elif strategy == "clarify":
            return self._clarify_query(query)
        else:
            return self._expand_query(query)
    
    def _determine_strategy(self, query: str) -> str:
        """
        Определяет оптимальную стратегию для запроса.
        
        Args:
            query: Запрос пользователя.
        
        Returns:
            Название стратегии.
        """
        # Простые эвристики
        query_lower = query.lower()
        
        # Если запрос содержит сравнительные конструкции - разбиваем
        if any(word in query_lower for word in ['vs', 'versus', 'сравни', 'отличие', 'разница']):
            return 'split'
        
        # Если запрос очень короткий - расширяем
        if len(query.split()) < 3:
            return 'expand'
        
        # Если содержит неопределённые местоимения - уточняем
        if any(word in query_lower for word in ['это', 'оно', 'они', 'что это', 'кто это']):
            return 'clarify'
        
        # По умолчанию - расширяем
        return 'expand'
    
    def _expand_query(self, query: str) -> Dict[str, Any]:
        """Расширяет запрос синонимами и уточнениями."""
        try:
            from src.llm_chunker import call_llm
            
            prompt = f"""Перепиши запрос так, чтобы он был более информативным для семантического поиска в базе знаний.

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
Переписанный:"""

            rewritten = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.3,
                max_tokens=200
            )
            
            if rewritten:
                rewritten = rewritten.strip()
            else:
                rewritten = query
            
            return {
                'original': query,
                'rewritten': rewritten,
                'strategy': 'expand',
                'reason': 'Added synonyms and context'
            }
            
        except Exception as e:
            logger.error(f"Error in expand_query: {e}")
            return {
                'original': query,
                'rewritten': query,
                'strategy': 'expand',
                'error': str(e)
            }
    
    def _split_query(self, query: str) -> Dict[str, Any]:
        """Разбивает сложный запрос на подзапросы."""
        try:
            from src.llm_chunker import call_llm
            
            prompt = f"""Раздели сложный запрос на несколько простых подзапросов для поиска в базе знаний.

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
Подзапросы:"""

            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.3,
                max_tokens=300
            )
            
            # Парсим подзапросы
            sub_queries = []
            if response:
                for line in response.strip().split('\n'):
                    line = line.strip()
                    # Удаляем нумерацию и маркеры
                    line = line.lstrip('0123456789.-) ').strip()
                    if line and not line.startswith('Подзапросы'):
                        sub_queries.append(line)
            
            if not sub_queries:
                sub_queries = [query]
            
            return {
                'original': query,
                'rewritten': sub_queries[0] if sub_queries else query,
                'sub_queries': sub_queries,
                'strategy': 'split',
                'reason': 'Divided into sub-queries'
            }
            
        except Exception as e:
            logger.error(f"Error in split_query: {e}")
            return {
                'original': query,
                'rewritten': query,
                'strategy': 'split',
                'error': str(e)
            }
    
    def _clarify_query(self, query: str) -> Dict[str, Any]:
        """Уточняет неопределённые запросы."""
        try:
            from src.llm_chunker import call_llm
            
            prompt = f"""Перепиши неопределённый запрос так, чтобы он был понятен без контекста.

Правила:
1. Замени местоимения на конкретные существительные
2. Добавь уточняющие детали
3. Сохрани смысл запроса

Пример:
Оригинал: "как это работает"
Переписанный: "как работает технология RAG"

Оригинал: "{query}"
Переписанный:"""

            rewritten = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.3,
                max_tokens=200
            )
            
            if rewritten:
                rewritten = rewritten.strip()
            else:
                rewritten = query
            
            return {
                'original': query,
                'rewritten': rewritten,
                'strategy': 'clarify',
                'reason': 'Clarified ambiguous terms'
            }
            
        except Exception as e:
            logger.error(f"Error in clarify_query: {e}")
            return {
                'original': query,
                'rewritten': query,
                'strategy': 'clarify',
                'error': str(e)
            }


def rewrite_query(
    query: str,
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> Dict[str, Any]:
    """
    Удобная функция для перезаписи запроса.
    
    Args:
        query: Оригинальный запрос.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL.
    
    Returns:
        Переписанный запрос с метаданными.
    """
    rewriter = QueryRewriter(
        llm_model=llm_model,
        api_key=api_key,
        api_base=api_base
    )
    
    return rewriter.rewrite(query)


def rewrite_query_batch(
    queries: List[str],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> List[Dict[str, Any]]:
    """
    Перезаписывает батч запросов.
    
    Args:
        queries: Список запросов.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL.
    
    Returns:
        Список переписанных запросов.
    """
    rewriter = QueryRewriter(
        llm_model=llm_model,
        api_key=api_key,
        api_base=api_base
    )
    
    results = []
    for query in queries:
        result = rewriter.rewrite(query)
        results.append(result)
    
    return results
