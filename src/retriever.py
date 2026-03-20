"""
Модуль Fusion Retrieval для объединения разных методов поиска в RAG.

Fusion Retrieval комбинирует:
- Векторный поиск (semantic similarity)
- Поиск по ключевым словам (BM25)
- LLM-поиск (логический вывод)

Поддерживает несколько алгоритмов слияния:
- Reciprocal Rank Fusion (RRF)
- Score-based Fusion
- LLM-based Fusion
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class FusionResult:
    """Результат Fusion поиска."""
    document: Dict[str, Any]
    combined_score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0
    llm_score: float = 0.0
    sources: List[str] = None


class FusionRetriever:
    """
    Объединенный поиск с использованием нескольких методов.
    
    Алгоритмы Fusion:
    1. RRF (Reciprocal Rank Fusion) - на основе рангов
    2. Score-based - на основе оценок
    3. LLM-based - LLM выбирает лучшие
    """
    
    # Типы алгоритмов слияния
    RRF = "rrf"
    SCORE_BASED = "score"
    LLM_BASED = "llm"
    
    def __init__(
        self,
        fusion_algorithm: str = RRF,
        vector_weight: float = 0.4,
        keyword_weight: float = 0.3,
        llm_weight: float = 0.3,
        rrf_k: int = 60,  # Параметр RRF
        top_k: int = 10,
        llm_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1"
    ):
        """
        Инициализация Fusion Retriever.
        
        Args:
            fusion_algorithm: Алгоритм слияния (rrf, score, llm).
            vector_weight: Вес векторного поиска.
            keyword_weight: Вес поиска по ключевым словам.
            llm_weight: Вес LLM-поиска.
            rrf_k: Параметр k для RRF.
            top_k: Количество результатов.
            llm_model: Модель LLM.
            embedding_model: Модель эмбеддингов.
            api_key: API ключ.
            api_base: Базовый URL.
        """
        self.fusion_algorithm = fusion_algorithm
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.llm_weight = llm_weight
        self.rrf_k = rrf_k
        self.top_k = top_k
        self.llm_model = llm_model
        self.embedding_model = embedding_model
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
        """Проверяет доступность API."""
        return bool(self.api_key)
    
    def search(
        self,
        query: str,
        documents: List[Dict[str, Any]] = None,
        index=None,
        dataset: List[Dict] = None,
        verbose: bool = False
    ) -> List[FusionResult]:
        """
        Выполняет Fusion поиск.
        
        Args:
            query: Запрос пользователя.
            documents: Список документов.
            index: FAISS индекс.
            dataset: Датасет для index.
            verbose: Выводить ли прогресс.
        
        Returns:
            Список объединённых результатов.
        """
        if not documents and (not index or not dataset):
            logger.warning("Нет документов для поиска")
            return []
        
        if verbose:
            print(f"Fusion: Начало поиска (алгоритм: {self.fusion_algorithm})")
        
        # Получаем результаты от разных методов
        vector_results = self._vector_search(query, index, dataset, verbose)
        keyword_results = self._keyword_search(query, documents, verbose)
        
        # LLM-поиск только если выбран LLM-алгоритм
        llm_results = {}
        if self.fusion_algorithm == self.LLM_BASED and self.is_available():
            llm_results = self._llm_search(query, documents, verbose)
        
        # Объединяем результаты
        if self.fusion_algorithm == self.RRF:
            combined = self._rrf_fusion(vector_results, keyword_results, llm_results)
        elif self.fusion_algorithm == self.SCORE_BASED:
            combined = self._score_fusion(vector_results, keyword_results, llm_results)
        elif self.fusion_algorithm == self.LLM_BASED:
            combined = self._llm_fusion(query, vector_results, keyword_results, llm_results, verbose)
        else:
            combined = self._score_fusion(vector_results, keyword_results, llm_results)
        
        return combined[:self.top_k]
    
    def _vector_search(
        self,
        query: str,
        index,
        dataset: List[Dict],
        verbose: bool = False
    ) -> Dict[str, float]:
        """Векторный поиск."""
        if verbose:
            print("  Vector search...")
        
        results = {}
        
        if index is not None and dataset is not None:
            # Получаем эмбеддинг запроса
            query_embedding = self._get_embedding(query)
            
            if query_embedding:
                import numpy as np
                query_vec = np.array([query_embedding], dtype='float32')
                distances, indices = index.search(query_vec, self.top_k * 2)
                
                for dist, idx in zip(distances[0], indices[0]):
                    if idx < len(dataset):
                        # Конвертируем distance в similarity
                        similarity = 1.0 / (1.0 + dist)
                        doc_id = str(idx)
                        results[doc_id] = similarity
        
        return results
    
    def _keyword_search(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        verbose: bool = False
    ) -> Dict[str, float]:
        """Поиск по ключевым словам (упрощённый BM25)."""
        if verbose:
            print("  Keyword search...")
        
        results = {}
        
        # Токенизируем запрос
        query_terms = query.lower().split()
        
        for i, doc in enumerate(documents):
            text = doc.get('text', '').lower()
            
            # Подсчитываем совпадения
            score = 0
            for term in query_terms:
                if term in text:
                    # Вес = количество вхождений / длину документа
                    count = text.count(term)
                    score += count / (len(text) / 1000 + 1)
            
            if score > 0:
                results[str(i)] = score
        
        # Нормализуем оценки
        if results:
            max_score = max(results.values())
            if max_score > 0:
                results = {k: v / max_score for k, v in results.items()}
        
        return results
    
    def _llm_search(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        verbose: bool = False
    ) -> Dict[str, float]:
        """Поиск через LLM (логический вывод)."""
        if verbose:
            print("  LLM search...")
        
        results = {}
        
        # Оцениваем только топ документы от других методов
        top_docs = documents[:20]
        
        try:
            from src.llm_chunker import call_llm
            
            docs_text = "\n\n".join([
                f"Документ {i}:\n{doc.get('text', '')[:300]}"
                for i, doc in enumerate(top_docs)
            ])
            
            prompt = f"""Оцени релевантность каждого документа к запросу.

Запрос: {query}

{docs_text}

Выведи оценки от 0 до 1 для каждого документа (1 - максимальная релевантность).
Ответь JSON массивом:
[{{"doc": 0, "score": 0.9}}, {{"doc": 1, "score": 0.3}}, ...]

Только JSON:"""

            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.1,
                max_tokens=300
            )
            
            if response:
                # Парсим JSON
                import re
                json_match = re.search(r'\[[\s\S]*\]', response)
                if json_match:
                    data = json.loads(json_match.group())
                    for item in data:
                        doc_idx = item.get('doc', 0)
                        score = item.get('score', 0)
                        if 0 <= doc_idx < len(top_docs):
                            results[str(doc_idx)] = float(score)
        
        except Exception as e:
            logger.error(f"LLM search error: {e}")
        
        return results
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Получает эмбеддинг текста."""
        try:
            import openai
            import os
            
            if not self.api_key:
                self.api_key = os.getenv("OPENAI_API_KEY")
            
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base
            )
            
            response = client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Embedding error: {e}")
        
        return None
    
    def _rrf_fusion(
        self,
        vector_results: Dict[str, float],
        keyword_results: Dict[str, float],
        llm_results: Dict[str, float]
    ) -> List[FusionResult]:
        """Reciprocal Rank Fusion - объединение на основе рангов."""
        
        # Собираем все ID документов
        all_ids = set(vector_results.keys()) | set(keyword_results.keys()) | set(llm_results.keys())
        
        # Создаём словарь рангов для каждого метода
        def get_ranks(results: Dict[str, float]) -> Dict[str, int]:
            sorted_items = sorted(results.items(), key=lambda x: x[1], reverse=True)
            return {doc_id: rank for rank, (doc_id, _) in enumerate(sorted_items)}
        
        vector_ranks = get_ranks(vector_results)
        keyword_ranks = get_ranks(keyword_results)
        llm_ranks = get_ranks(llm_results)
        
        # Вычисляем RRF scores
        rrf_scores = {}
        for doc_id in all_ids:
            score = 0.0
            
            # Векторный поиск
            if doc_id in vector_ranks:
                score += self.vector_weight / (self.rrf_k + vector_ranks[doc_id])
            
            # Keyword поиск
            if doc_id in keyword_ranks:
                score += self.keyword_weight / (self.rrf_k + keyword_ranks[doc_id])
            
            # LLM поиск
            if doc_id in llm_ranks:
                score += self.llm_weight / (self.rrf_k + llm_ranks[doc_id])
            
            rrf_scores[doc_id] = score
        
        # Сортируем и создаём результаты
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, combined_score in sorted_ids:
            results.append(FusionResult(
                document={'id': doc_id},
                combined_score=combined_score,
                vector_score=vector_results.get(doc_id, 0),
                keyword_score=keyword_results.get(doc_id, 0),
                llm_score=llm_results.get(doc_id, 0),
                sources=self._get_sources(vector_results, keyword_results, llm_results, doc_id)
            ))
        
        return results
    
    def _score_fusion(
        self,
        vector_results: Dict[str, float],
        keyword_results: Dict[str, float],
        llm_results: Dict[str, float]
    ) -> List[FusionResult]:
        """Score-based Fusion - объединение на основе оценок."""
        
        all_ids = set(vector_results.keys()) | set(keyword_results.keys()) | set(llm_results.keys())
        
        combined = {}
        for doc_id in all_ids:
            score = (
                self.vector_weight * vector_results.get(doc_id, 0) +
                self.keyword_weight * keyword_results.get(doc_id, 0) +
                self.llm_weight * llm_results.get(doc_id, 0)
            )
            combined[doc_id] = score
        
        # Сортируем
        sorted_ids = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, combined_score in sorted_ids:
            results.append(FusionResult(
                document={'id': doc_id},
                combined_score=combined_score,
                vector_score=vector_results.get(doc_id, 0),
                keyword_score=keyword_results.get(doc_id, 0),
                llm_score=llm_results.get(doc_id, 0),
                sources=self._get_sources(vector_results, keyword_results, llm_results, doc_id)
            ))
        
        return results
    
    def _llm_fusion(
        self,
        query: str,
        vector_results: Dict[str, float],
        keyword_results: Dict[str, float],
        llm_results: Dict[str, float],
        verbose: bool = False
    ) -> List[FusionResult]:
        """LLM-based Fusion - LLM выбирает лучшие документы."""
        
        # Объединяем все документы от разных методов
        all_ids = set(vector_results.keys()) | set(keyword_results.keys()) | set(llm_results.keys())
        
        # Если слишком много - ограничиваем
        if len(all_ids) > 30:
            # Берём топ от каждого метода
            top_from_vector = sorted(vector_results.items(), key=lambda x: x[1], reverse=True)[:10]
            top_from_keyword = sorted(keyword_results.items(), key=lambda x: x[1], reverse=True)[:10]
            top_from_llm = sorted(llm_results.items(), key=lambda x: x[1], reverse=True)[:10]
            
            all_ids = set([x[0] for x in top_from_vector] + 
                         [x[0] for x in top_from_keyword] + 
                         [x[0] for x in top_from_llm])
        
        # Пока просто используем score-based как fallback
        # (полноценная LLM-версия требует передачи документов)
        return self._score_fusion(vector_results, keyword_results, llm_results)
    
    def _get_sources(
        self,
        vector_results: Dict[str, float],
        keyword_results: Dict[str, float],
        llm_results: Dict[str, float],
        doc_id: str
    ) -> List[str]:
        """Определяем источники документа."""
        sources = []
        if doc_id in vector_results and vector_results[doc_id] > 0:
            sources.append("vector")
        if doc_id in keyword_results and keyword_results[doc_id] > 0:
            sources.append("keyword")
        if doc_id in llm_results and llm_results[doc_id] > 0:
            sources.append("llm")
        return sources


def fusion_search(
    query: str,
    documents: List[Dict[str, Any]] = None,
    index_path: str = None,
    dataset_path: str = None,
    fusion_algorithm: str = "rrf",
    vector_weight: float = 0.4,
    keyword_weight: float = 0.3,
    llm_weight: float = 0.3,
    llm_model: str = "gpt-4o-mini",
    embedding_model: str = "text-embedding-3-small",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    top_k: int = 10,
    verbose: bool = False
) -> List[Dict[str, Any]]:
    """
    Удобная функция для Fusion поиска.
    
    Args:
        query: Запрос пользователя.
        documents: Список документов.
        index_path: Путь к FAISS индексу.
        dataset_path: Путь к датасету.
        fusion_algorithm: Алгоритм (rrf, score, llm).
        vector_weight: Вес векторного поиска.
        keyword_weight: Вес поиска по ключевым словам.
        llm_weight: Вес LLM-поиска.
        llm_model: Модель LLM.
        embedding_model: Модель эмбеддингов.
        api_key: API ключ.
        api_base: Базовый URL.
        top_k: Количество результатов.
        verbose: Выводить ли прогресс.
    
    Returns:
        Список объединённых результатов.
    """
    import json
    import faiss
    import os
    
    # Загружаем индекс и датасет
    index = None
    dataset = None
    
    if index_path and dataset_path:
        if os.path.exists(index_path) and os.path.exists(dataset_path):
            index = faiss.read_index(index_path)
            with open(dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
    
    # Создаём Fusion retriever
    retriever = FusionRetriever(
        fusion_algorithm=fusion_algorithm,
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        llm_weight=llm_weight,
        top_k=top_k,
        llm_model=llm_model,
        embedding_model=embedding_model,
        api_key=api_key,
        api_base=api_base
    )
    
    # Выполняем поиск
    results = retriever.search(
        query=query,
        documents=documents,
        index=index,
        dataset=dataset,
        verbose=verbose
    )
    
    # Конвертируем в удобный формат
    return [
        {
            'document': r.document,
            'combined_score': r.combined_score,
            'vector_score': r.vector_score,
            'keyword_score': r.keyword_score,
            'llm_score': r.llm_score,
            'sources': r.sources
        }
        for r in results
    ]
