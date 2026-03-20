"""
Модуль Re-ranking для улучшения качества поиска в RAG-системах.

Re-ranking перераспределяет результаты поиска по реальной релевантности
с помощью LLM-анализа пары (запрос + документ).
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Документ для переранжирования."""
    id: str
    text: str
    metadata: Dict[str, Any]
    original_score: float = 0.0


@dataclass 
class RankedDocument:
    """Переранжированный документ с оценкой релевантности."""
    id: str
    text: str
    metadata: Dict[str, Any]
    relevance_score: float
    original_score: float
    rank: int


class Reranker:
    """
    Переранжировщик документов на основе LLM-анализа.
    
    Использует LLM для оценки релевантности каждого документа
    к запросу пользователя.
    """
    
    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1",
        top_k: int = 10,
        batch_size: int = 5
    ):
        """
        Инициализация переранжировщика.
        
        Args:
            llm_model: Модель LLM для оценки.
            api_key: API ключ.
            api_base: Базовый URL API.
            top_k: Количество документов для возврата.
            batch_size: Размер батча для оценки.
        """
        self.llm_model = llm_model
        self.api_key = api_key
        self.api_base = api_base
        self.top_k = top_k
        self.batch_size = batch_size
        
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
    
    def rank(
        self, 
        query: str, 
        documents: List[Document],
        verbose: bool = False
    ) -> List[RankedDocument]:
        """
        Переранжирует документы по релевантности к запросу.
        
        Args:
            query: Запрос пользователя.
            documents: Список документов для переранжирования.
            verbose: Выводить ли прогресс.
        
        Returns:
            Список переранжированных документов.
        """
        if not documents:
            return []
        
        if not self.is_available():
            logger.warning("LLM недоступен, возвращаем оригинальный порядок")
            return self._return_original_order(documents)
        
        if verbose:
            print(f"Re-ranking {len(documents)} документов...")
        
        # Оцениваем документы батчами
        all_scores = []
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_scores = self._score_batch(query, batch)
            all_scores.extend(batch_scores)
            
            if verbose:
                print(f"  Обработано {min(i + self.batch_size, len(documents))}/{len(documents)}")
        
        # Сортируем по релевантности
        ranked = self._create_ranked_list(documents, all_scores)
        
        # Возвращаем топ-K
        return ranked[:self.top_k]
    
    def _score_batch(
        self, 
        query: str, 
        documents: List[Document]
    ) -> List[float]:
        """Оценивает батч документов через LLM."""
        try:
            from src.llm_chunker import call_llm
            
            # Формируем промпт
            docs_text = "\n\n".join([
                f"Документ {i+1}:\n{doc.text[:500]}"
                for i, doc in enumerate(documents)
            ])
            
            prompt = f"""Оцени релевантность каждого документа к запросу.

Запрос: {query}

{docs_text}

Для каждого документа выведи оценку от 0 до 10 (где 10 - максимальная релевантность).
Ответь в формате JSON:
[{{"doc": 1, "score": 8.5}}, {{"doc": 2, "score": 3.2}}, ...]

Выведи ТОЛЬКО JSON, без пояснений."""

            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.1,
                max_tokens=500
            )
            
            if response:
                return self._parse_scores(response, len(documents))
            else:
                return [doc.original_score for doc in documents]
                
        except Exception as e:
            logger.error(f"Ошибка при переранжировании: {e}")
            return [doc.original_score for doc in documents]
    
    def _parse_scores(self, response: str, expected_count: int) -> List[float]:
        """Парсит оценки из ответа LLM."""
        import json
        import re
        
        scores = [5.0] * expected_count  # Дефолтная оценка
        
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                for item in data:
                    doc_idx = item.get('doc', 1) - 1
                    score = item.get('score', 5.0)
                    if 0 <= doc_idx < expected_count:
                        scores[doc_idx] = float(score)
        except Exception as e:
            logger.warning(f"Не удалось распарсить оценки: {e}")
        
        return scores
    
    def _create_ranked_list(
        self, 
        documents: List[Document], 
        scores: List[float]
    ) -> List[RankedDocument]:
        """Создаёт отсортированный список документов."""
        # Создаём пары (документ, оценка)
        paired = list(zip(documents, scores))
        
        # Сортируем по убыванию оценки
        paired.sort(key=lambda x: x[1], reverse=True)
        
        # Создаём результат
        ranked = []
        for rank, (doc, score) in enumerate(paired, 1):
            ranked.append(RankedDocument(
                id=doc.id,
                text=doc.text,
                metadata=doc.metadata,
                relevance_score=score,
                original_score=doc.original_score,
                rank=rank
            ))
        
        return ranked
    
    def _return_original_order(
        self, 
        documents: List[Document]
    ) -> List[RankedDocument]:
        """Возвращает документы в оригинальном порядке."""
        return [
            RankedDocument(
                id=doc.id,
                text=doc.text,
                metadata=doc.metadata,
                relevance_score=doc.original_score,
                original_score=doc.original_score,
                rank=i+1
            )
            for i, doc in enumerate(documents[:self.top_k])
        ]


def rerank_results(
    query: str,
    documents: List[Dict[str, Any]],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Удобная функция для переранжирования результатов поиска.
    
    Args:
        query: Запрос пользователя.
        documents: Список документов с полями 'text', 'metadata'.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL.
        top_k: Количество результатов.
    
    Returns:
        Список переранжированных документов.
    """
    # Конвертируем в Document
    doc_objects = [
        Document(
            id=str(i),
            text=doc.get('text', ''),
            metadata=doc.get('metadata', {}),
            original_score=doc.get('score', 5.0)
        )
        for i, doc in enumerate(documents)
    ]
    
    # Переранжируем
    reranker = Reranker(
        llm_model=llm_model,
        api_key=api_key,
        api_base=api_base,
        top_k=top_k
    )
    
    ranked = reranker.rank(query, doc_objects)
    
    # Конвертируем обратно
    return [
        {
            'text': r.text,
            'metadata': r.metadata,
            'relevance_score': r.relevance_score,
            'original_score': r.original_score,
            'rank': r.rank
        }
        for r in ranked
    ]
