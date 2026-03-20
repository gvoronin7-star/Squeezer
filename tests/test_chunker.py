"""
Unit-тесты для модуля chunker.
"""

import pytest
from datetime import datetime


class TestHybridChunking:
    """Тесты функции hybrid_chunking."""
    
    def test_basic_chunking(self):
        """Тест базового чанкинга."""
        from src.chunker import hybrid_chunking
        
        structure = {
            "headings": [],
            "paragraphs": ["Тестовый абзац для проверки чанкинга."],
            "lists": []
        }
        
        chunks = hybrid_chunking(structure, max_chunk_size=100, overlap=10)
        assert len(chunks) > 0
        assert all("text" in chunk for chunk in chunks)
    
    def test_chunk_size_limit(self):
        """Тест ограничения размера чанка."""
        from src.chunker import hybrid_chunking
        
        long_text = "Очень длинный текст. " * 50  # ~1000 символов
        structure = {
            "headings": [],
            "paragraphs": [long_text],
            "lists": []
        }
        
        chunks = hybrid_chunking(structure, max_chunk_size=200, overlap=20)
        assert all(len(chunk["text"]) <= 250 for chunk in chunks)  # С запасом на overlap
    
    def test_preserve_lists(self):
        """Тест сохранения списков."""
        from src.chunker import hybrid_chunking
        
        structure = {
            "headings": [],
            "paragraphs": [],
            "lists": [["- Пункт 1", "- Пункт 2", "- Пункт 3"]]
        }
        
        chunks = hybrid_chunking(structure, max_chunk_size=500, overlap=10)
        assert len(chunks) >= 1
    
    def test_empty_structure(self):
        """Тест пустой структуры."""
        from src.chunker import hybrid_chunking
        
        structure = {
            "headings": [],
            "paragraphs": [],
            "lists": []
        }
        
        chunks = hybrid_chunking(structure, max_chunk_size=500, overlap=10)
        assert chunks == []


class TestAddMetadata:
    """Тесты функции add_metadata."""
    
    def test_basic_metadata(self):
        """Тест базовых метаданных."""
        from src.chunker import add_metadata
        
        chunks = [{"text": "Тест", "type": "paragraph"}]
        result = add_metadata(chunks, "test.pdf", page_number=1)
        
        assert len(result) == 1
        assert "metadata" in result[0]
        assert result[0]["metadata"]["source"] == "test.pdf"
        assert result[0]["metadata"]["page_number"] == 1
    
    def test_chunk_id_generation(self):
        """Тест генерации ID чанков."""
        from src.chunker import add_metadata
        
        chunks = [
            {"text": "Тест 1", "type": "paragraph"},
            {"text": "Тест 2", "type": "paragraph"},
            {"text": "Тест 3", "type": "paragraph"}
        ]
        result = add_metadata(chunks, "test.pdf", page_number=1)
        
        ids = [chunk["metadata"]["chunk_id"] for chunk in result]
        assert len(set(ids)) == 3  # Все ID уникальны
    
    def test_timestamp_format(self):
        """Тест формата timestamp."""
        from src.chunker import add_metadata
        
        chunks = [{"text": "Тест", "type": "paragraph"}]
        result = add_metadata(chunks, "test.pdf", page_number=1)
        
        timestamp = result[0]["metadata"]["timestamp"]
        # Проверяем ISO формат
        datetime.fromisoformat(timestamp)
    
    def test_char_and_word_count(self):
        """Тест подсчёта символов и слов."""
        from src.chunker import add_metadata
        
        chunks = [{"text": "Тестовый текст для подсчёта", "type": "paragraph"}]
        result = add_metadata(chunks, "test.pdf", page_number=1)
        
        assert result[0]["metadata"]["char_count"] > 0
        assert result[0]["metadata"]["word_count"] > 0


class TestValidateChunks:
    """Тесты функции validate_chunks."""
    
    def test_valid_chunks(self):
        """Тест валидных чанков."""
        from src.chunker import validate_chunks
        
        chunks = [
            {"text": "Нормальный текст", "metadata": {"char_count": 17}},
            {"text": "Ещё текст", "metadata": {"char_count": 9}}
        ]
        
        result = validate_chunks(chunks)
        assert result["total"] == 2
        assert result["empty"] == 0
    
    def test_empty_chunks_detection(self):
        """Тест обнаружения пустых чанков."""
        from src.chunker import validate_chunks
        
        chunks = [
            {"text": "", "metadata": {"char_count": 0}},
            {"text": "Текст", "metadata": {"char_count": 5}},
            {"text": "   ", "metadata": {"char_count": 3}}
        ]
        
        result = validate_chunks(chunks)
        assert result["empty"] >= 1
    
    def test_statistics(self):
        """Тест статистики чанков."""
        from src.chunker import validate_chunks
        
        chunks = [
            {"text": "Короткий", "metadata": {"char_count": 8}},
            {"text": "Более длинный текст", "metadata": {"char_count": 19}}
        ]
        
        result = validate_chunks(chunks)
        assert "avg_length" in result
        assert "min_length" in result
        assert "max_length" in result


class TestChunkTypes:
    """Тесты типов чанков."""
    
    def test_paragraph_type(self):
        """Тест типа paragraph."""
        from src.chunker import add_metadata
        
        chunks = [{"text": "Текст", "type": "paragraph"}]
        result = add_metadata(chunks, "test.pdf", page_number=1)
        
        assert result[0]["metadata"]["chunk_type"] == "paragraph"
    
    def test_heading_type(self):
        """Тест типа heading."""
        from src.chunker import add_metadata
        
        chunks = [{"text": "Заголовок", "type": "heading"}]
        result = add_metadata(chunks, "test.pdf", page_number=1)
        
        assert result[0]["metadata"]["chunk_type"] == "heading"
    
    def test_list_type(self):
        """Тест типа list."""
        from src.chunker import add_metadata
        
        chunks = [{"text": "- Пункт", "type": "list"}]
        result = add_metadata(chunks, "test.pdf", page_number=1)
        
        assert result[0]["metadata"]["chunk_type"] == "list"
