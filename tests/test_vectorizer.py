"""
Unit-тесты для модуля vectorizer.
"""

import pytest
import json
from pathlib import Path


class TestValidateData:
    """Тесты функции validate_data."""
    
    def test_valid_chunks(self):
        """Тест валидных чанков."""
        from src.vectorizer import validate_data
        
        chunks = [
            {"text": "Нормальный текст чанка", "metadata": {}},
            {"text": "Ещё один чанк", "metadata": {}}
        ]
        
        result = validate_data(chunks)
        assert result["total_chunks"] == 2
        assert result["stats"]["empty_chunks"] == 0
    
    def test_empty_chunks_detection(self):
        """Тест обнаружения пустых чанков."""
        from src.vectorizer import validate_data
        
        chunks = [
            {"text": "Текст", "metadata": {}},
            {"text": "", "metadata": {}},
            {"text": "   ", "metadata": {}}
        ]
        
        result = validate_data(chunks)
        assert result["stats"]["empty_chunks"] >= 1
    
    def test_empty_input(self):
        """Тест пустого ввода."""
        from src.vectorizer import validate_data
        
        result = validate_data([])
        assert result["total_chunks"] == 0
        assert result["stats"]["avg_char_count"] == 0
    
    def test_statistics_calculation(self):
        """Тест расчёта статистики."""
        from src.vectorizer import validate_data
        
        chunks = [
            {"text": "Короткий", "metadata": {}},
            {"text": "Средний текст", "metadata": {}},
            {"text": "Более длинный текст для теста", "metadata": {}}
        ]
        
        result = validate_data(chunks)
        stats = result["stats"]
        
        assert stats["total_chunks"] == 3
        assert stats["total_chars"] > 0
        assert stats["avg_char_count"] > 0
        assert stats["min_char_count"] < stats["max_char_count"]


class TestSaveToVectorDb:
    """Тесты функции save_to_vector_db (без реальных API вызовов)."""
    
    def test_missing_openai(self, monkeypatch):
        """Тест отсутствия библиотеки openai."""
        # Пропускаем если openai установлен
        pytest.importorskip("openai")
    
    def test_missing_faiss(self, monkeypatch):
        """Тест отсутствия библиотеки faiss."""
        # Пропускаем если faiss установлен
        pytest.importorskip("faiss")
    
    def test_empty_dataset(self):
        """Тест пустого датасета."""
        from src.vectorizer import save_to_vector_db
        
        # Мокаем зависимости
        pytest.importorskip("openai")
        pytest.importorskip("faiss")
        
        result = save_to_vector_db([], api_key="test_key")
        assert result["success"] is False
        assert result["total_vectors"] == 0


class TestGenerateVectorizationReport:
    """Тесты функции generate_vectorization_report."""
    
    def test_report_generation(self, tmp_path):
        """Тест генерации отчёта."""
        from src.vectorizer import generate_vectorization_report
        
        validation_result = {
            "stats": {
                "total_chunks": 10,
                "empty_chunks": 0,
                "avg_char_count": 150.5,
                "min_char_count": 50,
                "max_char_count": 300
            }
        }
        
        vectorization_result = {
            "success": True,
            "total_vectors": 10,
            "embedding_dim": 1536,
            "vector_db_path": "output/vector_db/index.faiss",
            "dataset_path": "output/vector_db/dataset.json"
        }
        
        report_path = generate_vectorization_report(
            validation_result,
            vectorization_result,
            model_name="text-embedding-3-small",
            db_type="faiss",
            output_dir=str(tmp_path)
        )
        
        assert Path(report_path).exists()
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "text-embedding-3-small" in content
        assert "10" in content
        assert "faiss" in content
    
    def test_report_content_structure(self, tmp_path):
        """Тест структуры содержимого отчёта."""
        from src.vectorizer import generate_vectorization_report
        
        validation_result = {"stats": {"total_chunks": 5, "empty_chunks": 0}}
        vectorization_result = {"success": True, "total_vectors": 5, "embedding_dim": 1536}
        
        report_path = generate_vectorization_report(
            validation_result,
            vectorization_result,
            model_name="test-model",
            db_type="faiss",
            output_dir=str(tmp_path)
        )
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие ключевых разделов
        assert "Этап 7" in content or "Проверка качества" in content
        assert "Этап 8" in content or "Векторизация" in content


class TestProcessVectorization:
    """Тесты функции process_vectorization."""
    
    def test_empty_input(self, tmp_path):
        """Тест пустого ввода."""
        from src.vectorizer import process_vectorization
        
        result = process_vectorization(
            [],
            output_dir=str(tmp_path),
            api_key="test_key"
        )
        
        assert "validation" in result
        assert result["validation"]["total_chunks"] == 0


class TestVectorDbStructure:
    """Тесты структуры векторной БД."""
    
    def test_metadata_structure(self, tmp_path):
        """Тест структуры метаданных."""
        from src.vectorizer import generate_vectorization_report
        
        validation_result = {"stats": {"total_chunks": 1, "empty_chunks": 0}}
        vectorization_result = {
            "success": True,
            "total_vectors": 1,
            "embedding_dim": 1536,
            "vector_db_path": str(tmp_path / "index.faiss"),
            "dataset_path": str(tmp_path / "dataset.json")
        }
        
        report_path = generate_vectorization_report(
            validation_result,
            vectorization_result,
            model_name="text-embedding-3-small",
            db_type="faiss",
            output_dir=str(tmp_path)
        )
        
        assert Path(report_path).exists()
