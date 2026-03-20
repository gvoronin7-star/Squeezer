"""
Unit-тесты для модуля rag_engine.
"""

import pytest
import json
from pathlib import Path


class TestRAGConfig:
    """Тесты конфигурации RAG."""
    
    def test_default_config(self):
        """Тест конфигурации по умолчанию."""
        from src.rag_engine import RAGConfig
        
        config = RAGConfig()
        
        assert config.embedding_model == "text-embedding-3-small"
        assert config.llm_model == "gpt-4o-mini"
        assert config.top_k == 10
        assert config.use_reranker is True
    
    def test_custom_config(self):
        """Тест кастомной конфигурации."""
        from src.rag_engine import RAGConfig
        
        config = RAGConfig(
            embedding_model="text-embedding-3-large",
            llm_model="gpt-4o",
            top_k=5,
            use_reranker=False
        )
        
        assert config.embedding_model == "text-embedding-3-large"
        assert config.llm_model == "gpt-4o"
        assert config.top_k == 5
        assert config.use_reranker is False


class TestRAGEngineInit:
    """Тесты инициализации RAG Engine."""
    
    def test_init_without_config(self):
        """Тест инициализации без конфигурации."""
        from src.rag_engine import RAGEngine
        
        engine = RAGEngine()
        
        assert engine.config is not None
        assert engine.index is None
        assert engine.dataset is None
    
    def test_init_with_config(self):
        """Тест инициализации с конфигурацией."""
        from src.rag_engine import RAGEngine, RAGConfig
        
        config = RAGConfig(llm_model="gpt-4o")
        engine = RAGEngine(config)
        
        assert engine.config.llm_model == "gpt-4o"
    
    def test_is_ready_false_initially(self):
        """Тест начальной неготовности движка."""
        from src.rag_engine import RAGEngine
        
        engine = RAGEngine()
        assert not engine.is_ready()


class TestRAGEngineLoadIndex:
    """Тесты загрузки индекса."""
    
    def test_load_nonexistent_index(self):
        """Тест загрузки несуществующего индекса."""
        from src.rag_engine import RAGEngine
        
        engine = RAGEngine()
        result = engine.load_index("nonexistent_path")
        
        assert result is False
        assert not engine.is_ready()
    
    def test_load_index_missing_files(self, tmp_path):
        """Тест загрузки индекса с отсутствующими файлами."""
        from src.rag_engine import RAGEngine
        
        # Создаём пустую директорию
        (tmp_path / "vector_db").mkdir()
        
        engine = RAGEngine()
        result = engine.load_index(str(tmp_path / "vector_db"))
        
        assert result is False


class TestRAGEngineSearch:
    """Тесты поиска в RAG Engine."""
    
    def test_search_without_index(self):
        """Тест поиска без загруженного индекса."""
        from src.rag_engine import RAGEngine
        
        engine = RAGEngine()
        results = engine.search("test query")
        
        assert results == []
    
    def test_search_empty_query(self):
        """Тест поиска с пустым запросом."""
        from src.rag_engine import RAGEngine

        engine = RAGEngine()
        # Без индекса всё равно пустой результат
        results = engine.search("")
        assert results == []


class TestRAGEngineAsk:
    """Тесты генерации ответов."""
    
    def test_ask_without_index(self):
        """Тест вопроса без загруженного индекса."""
        from src.rag_engine import RAGEngine
        
        engine = RAGEngine()
        result = engine.ask("test question")
        
        assert "answer" in result
        assert "sources" in result
        assert result["sources"] == []
    
    def test_ask_returns_dict(self):
        """Тест что ask возвращает словарь."""
        from src.rag_engine import RAGEngine
        
        engine = RAGEngine()
        result = engine.ask("test")
        
        assert isinstance(result, dict)
        assert "query" in result


class TestCreateRagEngine:
    """Тесты функции create_rag_engine."""
    
    def test_create_engine_basic(self):
        """Тест базового создания движка."""
        from src.rag_engine import create_rag_engine
        
        engine = create_rag_engine()
        
        assert engine is not None
        assert not engine.is_ready()
    
    def test_create_engine_with_params(self):
        """Тест создания движка с параметрами."""
        from src.rag_engine import create_rag_engine
        
        engine = create_rag_engine(
            llm_model="gpt-4o",
            use_reranker=False
        )
        
        assert engine.config.llm_model == "gpt-4o"
        assert engine.config.use_reranker is False


class TestAskRag:
    """Тесты функции ask_rag."""
    
    def test_ask_rag_nonexistent_db(self):
        """Тест ask_rag с несуществующей БД."""
        from src.rag_engine import ask_rag
        
        result = ask_rag(
            query="test",
            db_path="nonexistent"
        )
        
        assert "answer" in result
        assert "error" in result["answer"].lower() or "не удалось" in result["answer"].lower()
    
    def test_ask_rag_returns_dict(self):
        """Тест что ask_rag возвращает словарь."""
        from src.rag_engine import ask_rag
        
        result = ask_rag("test", "nonexistent")
        
        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result


class TestRAGEngineMetrics:
    """Тесты метрик RAG Engine."""
    
    def test_get_metrics(self):
        """Тест получения метрик."""
        from src.rag_engine import RAGEngine
        
        engine = RAGEngine()
        metrics = engine.get_metrics()
        
        assert isinstance(metrics, dict)
    
    def test_from_vector_db(self):
        """Тест создания движка из векторной БД."""
        from src.rag_engine import RAGEngine
        
        engine = RAGEngine.from_vector_db("nonexistent")
        
        assert engine is not None
        assert not engine.is_ready()
