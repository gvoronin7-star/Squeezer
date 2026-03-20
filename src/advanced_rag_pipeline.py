"""
Интеграционный модуль: Advanced RAG Pipeline.

Объединяет все улучшения:
- Кэширование эмбеддингов
- Query rewriting
- Self-RAG с цитатами
- Извлечение таблиц
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AdvancedRAGPipeline:
    """
    Полный пайплайн Advanced RAG.
    
    Возможности:
    - Кэширование эмбеддингов
    - Query rewriting
    - Self-RAG оценка
    - Генерация ответов с цитатами
    - Извлечение таблиц
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        vector_store = None,
        dataset: List[Dict] = None
    ):
        """
        Инициализация пайплайна.
        
        Args:
            config: Конфигурация.
            vector_store: FAISS хранилище.
            dataset: Датасет чанков.
        """
        self.config = config or {}
        self.vector_store = vector_store
        self.dataset = dataset
        
        # Параметры
        self.llm_model = self.config.get('llm_model', 'gpt-4o-mini')
        self.api_key = self.config.get('api_key')
        self.api_base = self.config.get('api_base', 'https://openai.api.proxyapi.ru/v1')
        
        # Загружаем модули
        self._init_modules()
    
    def _init_modules(self) -> None:
        """Инициализирует модули."""
        # Кэширование эмбеддингов
        try:
            from src.embedding_cache import get_embedding_cache
            self.embedding_cache = get_embedding_cache()
            logger.info("Модуль кэширования эмбеддингов загружен")
        except ImportError as e:
            logger.warning(f"Модуль кэширования недоступен: {e}")
            self.embedding_cache = None
        
        # Query rewriting
        try:
            from src.query_rewriter import QueryRewriter
            self.query_rewriter = QueryRewriter(
                llm_model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base
            )
            logger.info("Модуль query rewriting загружен")
        except ImportError as e:
            logger.warning(f"Модуль query rewriting недоступен: {e}")
            self.query_rewriter = None
        
        # Answer generation
        try:
            from src.answer_generator import AnswerGenerator
            self.answer_generator = AnswerGenerator(
                llm_model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base
            )
            logger.info("Модуль генерации ответов загружен")
        except ImportError as e:
            logger.warning(f"Модуль генерации ответов недоступен: {e}")
            self.answer_generator = None
        
        # Self-RAG
        try:
            from src.self_rag import SelfRAG
            self.self_rag = SelfRAG(
                vector_store=self.vector_store,
                llm_model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base
            )
            logger.info("Self-RAG модуль загружен")
        except ImportError as e:
            logger.warning(f"Self-RAG модуль недоступен: {e}")
            self.self_rag = None
        
        # Table extractor
        try:
            from src.table_extractor import TableExtractor
            self.table_extractor = TableExtractor(
                llm_model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base
            )
            logger.info("Модуль извлечения таблиц загружен")
        except ImportError as e:
            logger.warning(f"Модуль извлечения таблиц недоступен: {e}")
            self.table_extractor = None
    
    def query(
        self,
        query: str,
        use_query_rewrite: bool = True,
        use_self_rag: bool = True,
        use_citations: bool = True,
        top_k: int = 5,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Выполняет запрос через полный пайплайн.
        
        Args:
            query: Запрос пользователя.
            use_query_rewrite: Использовать перезапись запроса.
            use_self_rag: Использовать Self-RAG.
            use_citations: Использовать цитаты.
            top_k: Количество документов.
            verbose: Выводить прогресс.
        
        Returns:
            Результат с ответом, цитатами и метаданными.
        """
        result = {
            'query': query,
            'query_rewritten': None,
            'answer': None,
            'citations': [],
            'confidence': 0.0,
            'tables': [],
            'metadata': {}
        }
        
        # Шаг 1: Query rewriting
        if use_query_rewrite and self.query_rewriter:
            if verbose:
                print("1. Перезапись запроса...")
            
            rewrite_result = self.query_rewriter.rewrite(query)
            result['query_rewritten'] = rewrite_result['rewritten']
            
            if 'sub_queries' in rewrite_result:
                # Сложный запрос - обрабатываем подзапросы
                sub_results = []
                for sq in rewrite_result['sub_queries']:
                    sub_result = self._search_and_answer(sq, top_k, use_citations)
                    sub_results.append(sub_result)
                
                # Объединяем результаты
                result['answer'] = self._merge_answers(sub_results)
                result['citations'] = self._merge_citations(sub_results)
            else:
                query = rewrite_result['rewritten']
        
        # Шаг 2: Поиск и ответ
        if verbose:
            print("2. Поиск и генерация ответа...")
        
        search_result = self._search_and_answer(query, top_k, use_citations)
        result['answer'] = search_result.get('answer', result['answer'])
        result['citations'] = search_result.get('citations', [])
        result['confidence'] = search_result.get('confidence', 0.0)
        
        # Шаг 3: Self-RAG оценка (если включено)
        if use_self_rag and self.self_rag:
            if verbose:
                print("3. Self-RAG оценка...")
            
            # Выполняем Self-RAG
            self_rag_result = self.self_rag.query(query, top_k=top_k, verbose=verbose)
            
            result['metadata']['self_rag'] = {
                'iterations': self_rag_result.iterations,
                'final_confidence': self_rag_result.final_confidence,
                'answer_quality': self_rag_result.answer_evaluation.quality.value,
                'grounded': self_rag_result.answer_evaluation.grounded,
                'hallucinations': self_rag_result.answer_evaluation.hallucinations
            }
            
            # Обновляем если Self-RAG дал лучший результат
            if self_rag_result.final_confidence > result['confidence']:
                result['answer'] = self_rag_result.answer
                result['confidence'] = self_rag_result.final_confidence
        
        # Шаг 4: Оценка через Answer Generator (если не Self-RAG)
        elif use_citations and self.answer_generator and not use_self_rag:
            if verbose:
                print("3. Генерация ответа с цитатами...")
            
            documents = self._search(query, top_k)
            answer_result = self.answer_generator.generate(
                query, documents, include_citations=True, verbose=verbose
            )
            
            result['answer'] = answer_result.answer
            result['citations'] = [
                {
                    'chunk_id': c.chunk_id,
                    'source': c.source,
                    'page': c.page,
                    'text': c.text,
                    'relevance': c.relevance_score
                }
                for c in answer_result.citations
            ]
            result['confidence'] = answer_result.confidence
        
        return result
    
    def _search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Ищет документы."""
        if self.vector_store is None:
            return []
        
        try:
            if hasattr(self.vector_store, 'similarity_search'):
                return self.vector_store.similarity_search(query, k=top_k)
            elif hasattr(self.vector_store, 'search'):
                return self.vector_store.search(query, k=top_k)
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
        
        return []
    
    def _search_and_answer(
        self,
        query: str,
        top_k: int,
        use_citations: bool
    ) -> Dict[str, Any]:
        """Ищет и генерирует ответ."""
        documents = self._search(query, top_k)
        
        if not documents:
            return {
                'answer': 'Документы не найдены',
                'citations': [],
                'confidence': 0.0
            }
        
        if use_citations and self.answer_generator:
            result = self.answer_generator.generate(query, documents)
            return {
                'answer': result.answer,
                'citations': [
                    {
                        'chunk_id': c.chunk_id,
                        'source': c.source,
                        'page': c.page,
                        'text': c.text,
                        'relevance': c.relevance_score
                    }
                    for c in result.citations
                ],
                'confidence': result.confidence
            }
        else:
            # Простой ответ - первый документ
            return {
                'answer': documents[0].get('text', '')[:500],
                'citations': [],
                'confidence': 0.5
            }
    
    def _merge_answers(self, sub_results: List[Dict]) -> str:
        """Объединяет ответы от подзапросов."""
        answers = [r.get('answer', '') for r in sub_results if r.get('answer')]
        
        if not answers:
            return "Не удалось найти информацию"
        
        return "\n\n".join(answers)
    
    def _merge_citations(self, sub_results: List[Dict]) -> List[Dict]:
        """Объединяет цитаты от подзапросов."""
        all_citations = []
        seen_ids = set()
        
        for result in sub_results:
            for cit in result.get('citations', []):
                cit_id = cit.get('chunk_id')
                if cit_id and cit_id not in seen_ids:
                    all_citations.append(cit)
                    seen_ids.add(cit_id)
        
        return all_citations
    
    def extract_tables(
        self,
        pdf_path: str,
        use_llm: bool = True,
        verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Извлекает таблицы из PDF.
        
        Args:
            pdf_path: Путь к PDF.
            use_llm: Использовать LLM для интерпретации.
            verbose: Выводить прогресс.
        
        Returns:
            Список таблиц.
        """
        if not self.table_extractor:
            logger.warning("Table extractor не инициализирован")
            return []
        
        if verbose:
            print(f"Извлечение таблиц из {pdf_path}...")
        
        tables = self.table_extractor.extract_tables(
            pdf_path, 
            use_llm=use_llm,
            min_rows=2,
            min_cols=2
        )
        
        if verbose:
            print(f"Найдено таблиц: {len(tables)}")
        
        return tables
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша."""
        if self.embedding_cache:
            return self.embedding_cache.get_stats()
        return {'total_entries': 0, 'size_mb': 0}
    
    def clear_cache(self) -> None:
        """Очищает кэш эмбеддингов."""
        if self.embedding_cache:
            self.embedding_cache.clear()
            logger.info("Кэш очищен")


def create_advanced_rag_pipeline(
    config: Dict[str, Any] = None,
    vector_store = None,
    dataset: List[Dict] = None
) -> AdvancedRAGPipeline:
    """
    Создаёт Advanced RAG пайплайн.
    
    Args:
        config: Конфигурация.
        vector_store: FAISS хранилище.
        dataset: Датасет чанков.
    
    Returns:
        Экземпляр пайплайна.
    """
    return AdvancedRAGPipeline(
        config=config,
        vector_store=vector_store,
        dataset=dataset
    )


# Пример использования
if __name__ == "__main__":
    print("=" * 60)
    print("Advanced RAG Pipeline")
    print("=" * 60)
    
    # Пример конфигурации
    config = {
        'llm_model': 'gpt-4o-mini',
        'api_key': None,  # Будет взято из .env
        'api_base': 'https://openai.api.proxyapi.ru/v1',
        'embedding_model': 'text-embedding-3-small'
    }
    
    # Создание пайплайна
    pipeline = create_advanced_rag_pipeline(config)
    
    print("\nМодули:")
    print(f"  - Кэширование эмбеддингов: {'✓' if pipeline.embedding_cache else '✗'}")
    print(f"  - Query rewriting: {'✓' if pipeline.query_rewriter else '✗'}")
    print(f"  - Генерация ответов: {'✓' if pipeline.answer_generator else '✗'}")
    print(f"  - Self-RAG: {'✓' if pipeline.self_rag else '✗'}")
    print(f"  - Извлечение таблиц: {'✓' if pipeline.table_extractor else '✗'}")
    
    print("\n" + "=" * 60)
    print("Для использования загрузите векторное хранилище и вызовите:")
    print("  result = pipeline.query('ваш вопрос')")
    print("=" * 60)
