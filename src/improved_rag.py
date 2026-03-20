"""
Улучшенный RAG пайплайн с поддержкой Re-ranking, HyDE и Fusion Retrieval.

Этот модуль объединяет все три техники улучшенного поиска:
- Re-ranking: перераспределение по релевантности
- HyDE: поиск по гипотетическому ответу
- Fusion: объединение разных методов поиска
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Загружаем .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class RAGQueryResult:
    """Результат RAG запроса с улучшениями."""
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class ImprovedRAG:
    """
    Улучшенный RAG с поддержкой:
    - Re-ranking
    - HyDE
    - Fusion Retrieval
    """
    
    def __init__(
        self,
        use_reranking: bool = True,
        use_hyde: bool = False,
        use_fusion: bool = False,
        llm_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1",
        top_k: int = 5,
        final_top_k: int = 3
    ):
        """
        Инициализация Improved RAG.
        
        Args:
            use_reranking: Использовать Re-ranking.
            use_hyde: Использовать HyDE.
            use_fusion: Использовать Fusion.
            llm_model: Модель LLM для генерации ответов.
            embedding_model: Модель эмбеддингов.
            api_key: API ключ.
            api_base: Базовый URL.
            top_k: Количество кандидатов для поиска.
            final_top_k: Количество финальных результатов.
        """
        self.use_reranking = use_reranking
        self.use_hyde = use_hyde
        self.use_fusion = use_fusion
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base
        self.top_k = top_k
        self.final_top_k = final_top_k
        
        # Инициализируем компоненты
        self._init_components()
    
    def _init_components(self):
        """Инициализирует компоненты поиска."""
        if self.use_hyde:
            try:
                from src.hyde_search import HyDESearch
                self.hyde = HyDESearch(
                    llm_model=self.llm_model,
                    embedding_model=self.embedding_model,
                    api_key=self.api_key,
                    api_base=self.api_base,
                    top_k=self.top_k
                )
            except ImportError:
                logger.warning("HyDE не доступен")
                self.hyde = None
        
        if self.use_fusion:
            try:
                from src.retriever import FusionRetriever
                self.fusion = FusionRetriever(
                    fusion_algorithm="rrf",
                    vector_weight=0.4,
                    keyword_weight=0.3,
                    llm_weight=0.3,
                    top_k=self.top_k,
                    llm_model=self.llm_model,
                    embedding_model=self.embedding_model,
                    api_key=self.api_key,
                    api_base=self.api_base
                )
            except ImportError:
                logger.warning("Fusion не доступен")
                self.fusion = None
        
        if self.use_reranking:
            try:
                from src.reranker import Reranker
                self.reranker = Reranker(
                    llm_model=self.llm_model,
                    api_key=self.api_key,
                    api_base=self.api_base,
                    top_k=self.final_top_k
                )
            except ImportError:
                logger.warning("Reranker не доступен")
                self.reranker = None
    
    def query(
        self,
        query: str,
        index_path: str = None,
        dataset_path: str = None,
        documents: List[Dict[str, Any]] = None,
        verbose: bool = False
    ) -> RAGQueryResult:
        """
        Выполняет RAG запрос с улучшениями.
        
        Args:
            query: Запрос пользователя.
            index_path: Путь к FAISS индексу.
            dataset_path: Путь к датасету.
            documents: Список документов (альтернатива index/dataset).
            verbose: Выводить ли прогресс.
        
        Returns:
            Ответ с источниками и метаданными.
        """
        if verbose:
            print(f"\n=== Improved RAG Query ===")
            print(f"Query: {query}")
            print(f"Re-ranking: {self.use_reranking}, HyDE: {self.use_hyde}, Fusion: {self.use_fusion}")
        
        # Шаг 1: Поиск кандидатов
        candidates = self._search_candidates(
            query, index_path, dataset_path, documents, verbose
        )
        
        if not candidates:
            return RAGQueryResult(
                answer="Не удалось найти релевантные документы.",
                sources=[],
                metadata={"error": "No candidates found"}
            )
        
        if verbose:
            print(f"Найдено кандидатов: {len(candidates)}")
        
        # Шаг 2: Re-ranking (если включён)
        if self.use_reranking and self.reranker:
            if verbose:
                print("Применяю Re-ranking...")
            
            candidates = self._apply_reranking(query, candidates, verbose)
        
        # Шаг 3: Генерация ответа
        answer = self._generate_answer(query, candidates, verbose)
        
        # Формируем результат
        result = RAGQueryResult(
            answer=answer,
            sources=candidates[:self.final_top_k],
            metadata={
                "total_candidates": len(candidates),
                "used_reranking": self.use_reranking,
                "used_hyde": self.use_hyde,
                "used_fusion": self.use_fusion,
                "llm_model": self.llm_model
            }
        )
        
        return result
    
    def _search_candidates(
        self,
        query: str,
        index_path: str,
        dataset_path: str,
        documents: List[Dict],
        verbose: bool
    ) -> List[Dict[str, Any]]:
        """Поиск кандидатов с использованием выбранных методов."""
        
        # Используем HyDE
        if self.use_hyde and self.hyde and index_path and dataset_path:
            if verbose:
                print("Использую HyDE поиск...")
            
            import faiss
            index = faiss.read_index(index_path)
            with open(dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            
            hyde_results = self.hyde.search(
                query=query,
                index=index,
                dataset=dataset,
                verbose=verbose
            )
            
            return [
                {
                    'text': r.document.get('text', ''),
                    'metadata': r.document.get('metadata', {}),
                    'score': r.similarity_score
                }
                for r in hyde_results
            ]
        
        # Используем Fusion
        if self.use_fusion and self.fusion:
            if verbose:
                print("Использую Fusion поиск...")
            
            fusion_results = self.fusion.search(
                query=query,
                documents=documents,
                verbose=verbose
            )
            
            return [
                {
                    'text': r.document.get('text', ''),
                    'metadata': r.document.get('metadata', {}),
                    'score': r.combined_score,
                    'sources': r.sources
                }
                for r in fusion_results
            ]
        
        # Обычный векторный поиск
        if verbose:
            print("Использую обычный векторный поиск...")
        
        return self._vector_search(query, index_path, dataset_path)
    
    def _vector_search(
        self,
        query: str,
        index_path: str,
        dataset_path: str
    ) -> List[Dict[str, Any]]:
        """Обычный векторный поиск."""
        import faiss
        import numpy as np
        import openai
        
        if not index_path or not dataset_path:
            return []
        
        # Загружаем индекс и датасет
        index = faiss.read_index(index_path)
        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        # Получаем эмбеддинг
        client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)
        response = client.embeddings.create(
            model=self.embedding_model,
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Ищем
        query_vec = np.array([query_embedding], dtype='float32')
        distances, indices = index.search(query_vec, self.top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(dataset):
                similarity = 1.0 / (1.0 + dist)
                results.append({
                    'text': dataset[idx].get('text', ''),
                    'metadata': dataset[idx].get('metadata', {}),
                    'score': similarity
                })
        
        return results
    
    def _apply_reranking(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        verbose: bool
    ) -> List[Dict[str, Any]]:
        """Применяет Re-ranking к кандидатам."""
        from src.reranker import Document, RankedDocument
        
        # Конвертируем в Document объекты
        doc_objects = [
            Document(
                id=str(i),
                text=doc.get('text', ''),
                metadata=doc.get('metadata', {}),
                original_score=doc.get('score', 5.0)
            )
            for i, doc in enumerate(candidates)
        ]
        
        # Переранжируем
        ranked = self.reranker.rank(query, doc_objects, verbose=verbose)
        
        # Конвертируем обратно
        return [
            {
                'text': r.text,
                'metadata': r.metadata,
                'score': r.relevance_score,
                'original_score': r.original_score,
                'rank': r.rank
            }
            for r in ranked
        ]
    
    def _generate_answer(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        verbose: bool
    ) -> str:
        """Генерирует ответ на основе найденных документов."""
        try:
            from src.llm_chunker import call_llm
            
            # Формируем контекст из документов
            context = "\n\n---\n\n".join([
                f"Документ {i+1}:\n{doc.get('text', '')}"
                for i, doc in enumerate(candidates[:self.final_top_k])
            ])
            
            prompt = f"""На основе предоставленных документов ответь на вопрос.

Вопрос: {query}

Документы:
{context}

Требования к ответу:
- Отвечай только на основе предоставленных документов
- Если информации недостаточно, честно об этом скажи
- Ответ должен быть точным и информативным
- Используй цитаты из документов где уместно

Ответ:"""

            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.3,
                max_tokens=1000
            )
            
            return response if response else "Не удалось сгенерировать ответ."
            
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return f"Ошибка при генерации ответа: {str(e)}"


def improved_rag_query(
    query: str,
    index_path: str = None,
    dataset_path: str = None,
    use_reranking: bool = True,
    use_hyde: bool = False,
    use_fusion: bool = False,
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    top_k: int = 10,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Удобная функция для улучшенного RAG запроса.
    
    Args:
        query: Запрос пользователя.
        index_path: Путь к FAISS индексу.
        dataset_path: Путь к датасету.
        use_reranking: Использовать Re-ranking.
        use_hyde: Использовать HyDE.
        use_fusion: Использовать Fusion.
        llm_model: Модель LLM.
        api_key: API ключ.
        top_k: Количество результатов.
        verbose: Выводить ли прогресс.
    
    Returns:
        Словарь с ответом, источниками и метаданными.
    """
    rag = ImprovedRAG(
        use_reranking=use_reranking,
        use_hyde=use_hyde,
        use_fusion=use_fusion,
        llm_model=llm_model,
        api_key=api_key,
        top_k=top_k
    )
    
    result = rag.query(
        query=query,
        index_path=index_path,
        dataset_path=dataset_path,
        verbose=verbose
    )
    
    return {
        'answer': result.answer,
        'sources': result.sources,
        'metadata': result.metadata
    }
