"""
Модуль HyDE (Hypothetical Document Embeddings) для улучшения поиска в RAG.

HyDE генерирует гипотетический идеальный ответ на запрос пользователя,
а затем ищет документы, похожие на этот ответ.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HyDEResult:
    """Результат поиска HyDE."""
    document: Dict[str, Any]
    hyde_answer: str
    similarity_score: float


class HyDESearch:
    """
    Поиск с использованием HyDE (Hypothetical Document Embeddings).
    
    Алгоритм:
    1. LLM генерирует гипотетический ответ на запрос
    2. Векторизуем гипотетический ответ
    3. Ищем документы, похожие на гипотетический ответ
    """
    
    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1",
        embedding_api_base: str = "https://openai.api.proxyapi.ru/v1",
        top_k: int = 10,
        include_hyde: bool = True
    ):
        """
        Инициализация HyDE поиска.
        
        Args:
            llm_model: Модель LLM для генерации гипотетического ответа.
            embedding_model: Модель эмбеддингов.
            api_key: API ключ.
            api_base: Базовый URL для LLM.
            embedding_api_base: Базовый URL для эмбеддингов.
            top_k: Количество результатов.
            include_hyde: Включить ли гипотетический ответ в результаты.
        """
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.api_key = api_key
        self.api_base = api_base
        self.embedding_api_base = embedding_api_base
        self.top_k = top_k
        self.include_hyde = include_hyde
        
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
        vector_db_path: str = None,
        documents: List[Dict[str, Any]] = None,
        index=None,
        dataset: List[Dict] = None,
        verbose: bool = False
    ) -> List[HyDEResult]:
        """
        Выполняет поиск с использованием HyDE.
        
        Args:
            query: Запрос пользователя.
            vector_db_path: Путь к векторной БД (альтернатива documents).
            documents: Список документов для поиска.
            index: FAISS индекс (альтернатива).
            dataset: Датасет документов (для index).
            verbose: Выводить ли прогресс.
        
        Returns:
            Список результатов с гипотетическими ответами.
        """
        if not self.is_available():
            logger.warning("LLM недоступен, используем обычный поиск")
            return self._fallback_search(query, documents, index, dataset)
        
        if verbose:
            print("HyDE: Генерация гипотетического ответа...")
        
        # Шаг 1: Генерируем гипотетический ответ
        hyde_answer = self._generate_hypothetical_answer(query)
        
        if not hyde_answer:
            logger.warning("Не удалось сгенерировать гипотетический ответ")
            return self._fallback_search(query, documents, index, dataset)
        
        if verbose:
            print(f"HyDE: Получен гипотетический ответ ({len(hyde_answer)} символов)")
        
        # Шаг 2: Векторизуем гипотетический ответ
        hyde_embedding = self._get_embedding(hyde_answer)
        
        if not hyde_embedding:
            logger.warning("Не удалось получить эмбеддинг")
            return self._fallback_search(query, documents, index, dataset)
        
        # Шаг 3: Ищем похожие документы
        if index is not None and dataset is not None:
            results = self._search_index(index, dataset, hyde_embedding, hyde_answer)
        elif documents:
            results = self._search_documents(documents, hyde_embedding, hyde_answer)
        else:
            logger.warning("Не предоставлены документы для поиска")
            return []
        
        if verbose:
            print(f"HyDE: Найдено {len(results)} результатов")
        
        return results
    
    def _generate_hypothetical_answer(self, query: str) -> Optional[str]:
        """Генерирует гипотетический идеальный ответ на запрос."""
        try:
            from src.llm_chunker import call_llm
            
            prompt = f"""Ты - эксперт, который отвечает на вопросы на основе документов.

Сгенерируй ПОДРОБНЫЙ и ПРАВИЛЬНЫЙ ответ на следующий вопрос, 
как будто ты нашёл идеальный документ с ответом.

Вопрос: {query}

Требования к ответу:
- Ответ должен быть развёрнутым (100-300 слов)
- Включай конкретику, детали, примеры
- Пиши так, будто это цитата из учебника или документации
- Используй правильную терминологию

Ответ:"""

            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.7,  # Немного креативности
                max_tokens=500
            )
            
            if response:
                return response.strip()
            
        except Exception as e:
            logger.error(f"Ошибка генерации HyDE ответа: {e}")
        
        return None
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Получает эмбеддинг текста."""
        try:
            import openai
            import os
            
            if not self.api_key:
                self.api_key = os.getenv("OPENAI_API_KEY")
            
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.embedding_api_base
            )
            
            response = client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга: {e}")
        
        return None
    
    def _search_index(
        self,
        index,
        dataset: List[Dict],
        query_embedding: List[float],
        hyde_answer: str
    ) -> List[HyDEResult]:
        """Ищет в FAISS индексе."""
        import numpy as np
        
        query_vec = np.array([query_embedding], dtype='float32')
        distances, indices = index.search(query_vec, self.top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(dataset):
                # Конвертируем расстояние в похожесть (чем меньше distance, тем больше similarity)
                similarity = 1.0 / (1.0 + dist)
                
                results.append(HyDEResult(
                    document=dataset[idx],
                    hyde_answer=hyde_answer,
                    similarity_score=similarity
                ))
        
        return results
    
    def _search_documents(
        self,
        documents: List[Dict[str, Any]],
        query_embedding: List[float],
        hyde_answer: str
    ) -> List[HyDEResult]:
        """Ищет в списке документов (без индекса)."""
        # Вычисляем косинусное сходство для каждого документа
        results = []
        
        for doc in documents:
            doc_embedding = self._get_embedding(doc.get('text', '')[:2000])
            
            if doc_embedding:
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                
                results.append(HyDEResult(
                    document=doc,
                    hyde_answer=hyde_answer,
                    similarity_score=similarity
                ))
        
        # Сортируем по убыванию похожести
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return results[:self.top_k]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Вычисляет косинусное сходство."""
        import numpy as np
        
        a = np.array(a)
        b = np.array(b)
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def _fallback_search(
        self,
        query: str,
        documents: List[Dict] = None,
        index=None,
        dataset: List[Dict] = None
    ) -> List[HyDEResult]:
        """Обычный поиск без HyDE (fallback)."""
        logger.info("Используем обычный поиск (без HyDE)")
        
        # Если есть индекс - используем его
        if index is not None and dataset is not None:
            query_embedding = self._get_embedding(query)
            if query_embedding:
                return self._search_index(index, dataset, query_embedding, "")
        
        # Иначе возвращаем пустой список
        return []


def hyde_search(
    query: str,
    index_path: str = None,
    dataset_path: str = None,
    llm_model: str = "gpt-4o-mini",
    embedding_model: str = "text-embedding-3-small",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Удобная функция для HyDE поиска.
    
    Args:
        query: Запрос пользователя.
        index_path: Путь к FAISS индексу.
        dataset_path: Путь к датасету JSON.
        llm_model: Модель LLM.
        embedding_model: Модель эмбеддингов.
        api_key: API ключ.
        api_base: Базовый URL.
        top_k: Количество результатов.
    
    Returns:
        Список найденных документов.
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
    
    # Создаём HyDE поиск
    hyde = HyDESearch(
        llm_model=llm_model,
        embedding_model=embedding_model,
        api_key=api_key,
        api_base=api_base,
        top_k=top_k
    )
    
    # Выполняем поиск
    results = hyde.search(
        query=query,
        index=index,
        dataset=dataset,
        verbose=True
    )
    
    # Конвертируем в удобный формат
    return [
        {
            'text': r.document.get('text', ''),
            'metadata': r.document.get('metadata', {}),
            'similarity_score': r.similarity_score,
            'hyde_answer': r.hyde_answer if hyde.include_hyde else None
        }
        for r in results
    ]
