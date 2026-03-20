"""
Интегрированный RAG-движок.

Объединяет все компоненты RAG в единый интерфейс:
- Извлечение (vectorizer)
- Поиск (retriever)  
- Переранжирование (reranker)
- Генерация ответов (answer_generator)
- Опционально: HyDE, Query Rewriting, кэширование
- Метрики и мониторинг

Использует единый API ключ и base_url для всех компонентов.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Метрики
try:
    from src.metrics import get_metrics, Timer
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    Timer = None

    def get_metrics():
        return None
    
    class Timer:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

@dataclass
class RAGConfig:
    """Конфигурация RAG-системы."""
    # Модели
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"
    
    # API
    api_key: str = None
    api_base: str = "https://openai.api.proxyapi.ru/v1"
    
    # Параметры поиска
    top_k: int = 10
    vector_weight: float = 0.4
    keyword_weight: float = 0.3
    llm_weight: float = 0.3
    
    # Параметры переранжирования
    use_reranker: bool = True
    reranker_top_k: int = 5
    
    # Опции
    use_hyde: bool = False
    use_query_rewriter: bool = False
    use_cache: bool = True
    
    # Параметры генерации
    include_citations: bool = True
    max_context_docs: int = 10


# ============================================================================
# ОСНОВНОЙ КЛАСС
# ============================================================================

class RAGEngine:
    """
    Интегрированный RAG-движок.
    
    Пример использования:
        rag = RAGEngine(config=RAGConfig(api_key="sk-..."))
        rag.load_index("vector_db/")
        answer = rag.ask("Ваш вопрос")
    """
    
    def __init__(self, config: RAGConfig = None):
        """
        Инициализация RAG-движка.
        
        Args:
            config: Конфигурация (или используется по умолчанию).
        """
        self.config = config or RAGConfig()
        
        # API ключ
        self.api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        
        # Состояние
        self.index = None
        self.dataset = None
        self.metadata = None
        
        # Компоненты (lazy loading)
        self._retriever = None
        self._reranker = None
        self._answer_generator = None
        
        logger.info("RAG Engine инициализирован")
    
    # ------------------------------------------------------------------------
    # ЗАГРУЗКА ИНДЕКСА
    # ------------------------------------------------------------------------
    
    def load_index(self, index_path: str) -> bool:
        """
        Загружает векторный индекс и датасет.
        
        Args:
            index_path: Путь к директории с индексом.
        
        Returns:
            True при успехе.
        """
        index_path = Path(index_path)
        
        # Загружаем индекс
        index_file = index_path / "index.faiss"
        dataset_file = index_path / "dataset.json"
        metadata_file = index_path / "metadata.json"
        
        try:
            import faiss
            
            if index_file.exists():
                self.index = faiss.read_index(str(index_file))
                logger.info(f"Индекс загружен: {self.index.ntotal} векторов")
            else:
                logger.warning(f"Индекс не найден: {index_file}")
                return False
            
            if dataset_file.exists():
                with open(dataset_file, 'r', encoding='utf-8') as f:
                    self.dataset = json.load(f)
                logger.info(f"Датасет загружен: {len(self.dataset)} документов")
            else:
                logger.warning(f"Датасет не найден: {dataset_file}")
                return False
            
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Метаданные загружены: {self.metadata.get('embedding_model')}")
            
            return True
            
        except ImportError:
            logger.error("faiss не установлен: pip install faiss-cpu")
            return False
        except Exception as e:
            logger.error(f"Ошибка загрузки индекса: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Проверяет готовность к поиску."""
        return self.index is not None and self.dataset is not None
    
    # ------------------------------------------------------------------------
    # ПОИСК
    # ------------------------------------------------------------------------
    
    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Выполняет поиск по запросу.
        
        Args:
            query: Запрос пользователя.
            top_k: Количество результатов (по умолчанию из конфига).
        
        Returns:
            Список найденных документов.
        """
        timer = Timer("rag.search") if METRICS_AVAILABLE else None
        if timer:
            timer.__enter__()
        
        try:
            if not self.is_ready():
                logger.warning("Индекс не загружен")
                return []
            
            top_k = top_k or self.config.top_k
            
            # Опционально: HyDE
            if self.config.use_hyde:
                query = self._hyde_transform(query)
            
            # Опционально: Query Rewriting
            if self.config.use_query_rewriter and self.api_key:
                query = self._rewrite_query(query)
            
            # Векторный поиск
            results = self._vector_search(query, top_k)
            
            # Опционально: Переранжирование
            if self.config.use_reranker and self.api_key and results:
                results = self._rerank(query, results)
            
            # Записываем метрику
            if METRICS_AVAILABLE:
                get_metrics().increment("rag.searches_total")
                get_metrics().increment(f"rag.search_results_{len(results)}")
            
            return results
            
        finally:
            if timer:
                timer.__exit__(None, None, None)
    
    def _vector_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Векторный поиск."""
        try:
            import numpy as np
            import openai
            
            # Получаем эмбеддинг запроса
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.config.api_base
            )
            
            response = client.embeddings.create(
                model=self.config.embedding_model,
                input=query
            )
            
            query_vec = np.array([response.data[0].embedding], dtype='float32')
            
            # Поиск
            distances, indices = self.index.search(query_vec, top_k)
            
            # Формируем результаты
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.dataset):
                    doc = self.dataset[int(idx)].copy()
                    doc['score'] = float(1.0 / (1.0 + dist))
                    doc['index'] = int(idx)
                    results.append(doc)
            
            return results
    
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []
    
    def _hyde_transform(self, query: str) -> str:
        """HyDE: преобразует запрос через LLM."""
        try:
            from src.llm_chunker import call_llm
            
            prompt = f"""Создай идеальный ответ на вопрос, который можно найти в документах.
Вопрос: {query}

Ответ (гипотетический документ):"""

            response = call_llm(
                prompt=prompt,
                model=self.config.llm_model,
                api_key=self.api_key,
                api_base=self.config.api_base,
                temperature=0.7,
                max_tokens=200
            )
            
            if response:
                logger.debug(f"HyDE: '{query}' -> '{response[:50]}...'")
                return response
                
        except Exception as e:
            logger.warning(f"HyDE error: {e}")
        
        return query
    
    def _rewrite_query(self, query: str) -> str:
        """Переписывает запрос через LLM."""
        try:
            from src.llm_chunker import call_llm
            
            prompt = f"""Перепиши запрос, чтобы он лучше подходил для семантического поиска в документах.
Сделай запрос более формальным и информативным.

Оригинальный запрос: {query}

Переписанный запрос:"""

            response = call_llm(
                prompt=prompt,
                model=self.config.llm_model,
                api_key=self.api_key,
                api_base=self.config.api_base,
                temperature=0.3,
                max_tokens=100
            )
            
            if response:
                logger.debug(f"Query rewrite: '{query}' -> '{response}'")
                return response
                
        except Exception as e:
            logger.warning(f"Query rewrite error: {e}")
        
        return query
    
    def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """Переранжирует результаты."""
        try:
            from src.reranker import rerank_results
            
            ranked = rerank_results(
                query=query,
                documents=results,
                llm_model=self.config.llm_model,
                api_key=self.api_key,
                api_base=self.config.api_base,
                top_k=self.config.reranker_top_k
            )
            
            return ranked
            
        except Exception as e:
            logger.warning(f"Reranker error: {e}")
            return results
    
    # ------------------------------------------------------------------------
    # ГЕНЕРАЦИЯ ОТВЕТА
    # ------------------------------------------------------------------------
    
    def ask(self, query: str) -> Dict[str, Any]:
        """
        Полный цикл RAG: поиск + генерация ответа.
        
        Args:
            query: Запрос пользователя.
        
        Returns:
            Словарь с ответом, источниками и метаданными.
        """
        timer = Timer("rag.ask") if METRICS_AVAILABLE else None
        if timer:
            timer.__enter__()
        
        try:
            logger.info(f"RAG: вопрос = '{query[:50]}...'")
            
            # Поиск
            documents = self.search(query)
            
            if not documents:
                if METRICS_AVAILABLE:
                    get_metrics().increment("rag.ask.no_results")
                return {
                    'answer': 'Не найдено релевантных документов для ответа на вопрос.',
                    'sources': [],
                    'confidence': 0.0,
                    'query': query
                }
            
            # Ограничиваем количество документов для контекста
            context_docs = documents[:self.config.max_context_docs]
            
            # Генерация ответа
            try:
                from src.answer_generator import generate_answer_with_citations
                
                result = generate_answer_with_citations(
                    query=query,
                    documents=context_docs,
                    llm_model=self.config.llm_model,
                    api_key=self.api_key,
                    api_base=self.config.api_base
                )
                
                if METRICS_AVAILABLE:
                    get_metrics().increment("rag.ask.success")
                
                return {
                    'answer': result['answer'],
                    'sources': result['citations'],
                    'confidence': result['confidence'],
                    'query': query,
                    'documents_found': len(documents),
                    'documents_used': len(context_docs)
                }
                
            except Exception as e:
                logger.error(f"Ошибка генерации: {e}")
                if METRICS_AVAILABLE:
                    get_metrics().increment("rag.ask.error")
                return {
                    'answer': f"Ошибка генерации: {str(e)}",
                    'sources': [],
                    'confidence': 0.0,
                    'query': query
                }
                
        finally:
            if timer:
                timer.__exit__(None, None, None)
    
    # ------------------------------------------------------------------------
    # УДОБНЫЕ ФУНКЦИИ
    # ------------------------------------------------------------------------
    
    @classmethod
    def from_vector_db(cls, db_path: str, **kwargs) -> 'RAGEngine':
        """
        Создаёт RAG-движок из существующей векторной БД.
        
        Args:
            db_path: Путь к директории с векторной БД.
            **kwargs: Дополнительные параметры конфигурации.
        
        Returns:
            Настроенный RAGEngine.
        """
        config = RAGConfig(**kwargs)
        engine = cls(config)
        engine.load_index(db_path)
        return engine

    def get_metrics(self) -> Dict[str, Any]:
        """
        Возвращает метрики работы RAG-движка.

        Returns:
            Словарь с метриками.
        """
        if METRICS_AVAILABLE:
            return get_metrics().get_stats()
        return {"error": "Metrics not available"}


# ============================================================================
# УДОБНЫЕ ФУНКЦИИ
# ============================================================================

def create_rag_engine(
    db_path: str = None,
    embedding_model: str = "text-embedding-3-small",
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    use_reranker: bool = True,
    use_hyde: bool = False,
    use_query_rewriter: bool = False
) -> RAGEngine:
    """
    Создаёт и настраивает RAG-движок.
    
    Args:
        db_path: Путь к векторной БД.
        embedding_model: Модель эмбеддингов.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Base URL.
        use_reranker: Использовать переранжирование.
        use_hyde: Использовать HyDE.
        use_query_rewriter: Использовать переписывание запросов.
    
    Returns:
        Настроенный RAGEngine.
    """
    config = RAGConfig(
        embedding_model=embedding_model,
        llm_model=llm_model,
        api_key=api_key,
        api_base=api_base,
        use_reranker=use_reranker,
        use_hyde=use_hyde,
        use_query_rewriter=use_query_rewriter
    )
    
    engine = RAGEngine(config)
    
    if db_path:
        engine.load_index(db_path)
    
    return engine


def ask_rag(
    query: str,
    db_path: str,
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    use_reranker: bool = True
) -> Dict[str, Any]:
    """
    Быстрый вопрос к RAG-системе.
    
    Args:
        query: Вопрос пользователя.
        db_path: Путь к векторной БД.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Base URL.
        use_reranker: Использовать переранжирование.
    
    Returns:
        Ответ с источниками.
    """
    engine = create_rag_engine(
        db_path=db_path,
        llm_model=llm_model,
        api_key=api_key,
        api_base=api_base,
        use_reranker=use_reranker
    )
    
    if not engine.is_ready():
        return {
            'answer': f'Не удалось загрузить векторную БД из: {db_path}',
            'sources': [],
            'confidence': 0.0
        }
    
    return engine.ask(query)
