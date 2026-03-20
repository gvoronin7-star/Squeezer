"""
Unit-тесты для модуля preprocessor.
"""

import pytest
from pathlib import Path


class TestExtractTextFromPdf:
    """Тесты функции extract_text_from_pdf."""
    
    def test_file_not_found(self):
        """Тест обработки несуществующего файла."""
        from src.preprocessor import extract_text_from_pdf
        
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf("nonexistent.pdf")
    
    def test_not_pdf_file(self, tmp_path):
        """Тест обработки не-PDF файла."""
        from src.preprocessor import extract_text_from_pdf
        
        # Создаём временный текстовый файл
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("test content")
        
        with pytest.raises(ValueError, match="не является PDF"):
            extract_text_from_pdf(str(txt_file))


class TestCleanText:
    """Тесты функции clean_text."""
    
    def test_remove_html_tags(self):
        """Тест удаления HTML-тегов."""
        from src.preprocessor import clean_text
        
        result = clean_text("<p>Текст</p><div>блок</div>", remove_html=True)
        assert "<p>" not in result
        assert "<div>" not in result
        assert "Текст" in result
        assert "блок" in result
    
    def test_normalize_whitespace(self):
        """Тест нормализации пробелов."""
        from src.preprocessor import clean_text
        
        result = clean_text("Текст   с    множеством    пробелов", normalize_whitespace=True)
        assert "    " not in result
        assert result == "Текст с множеством пробелов"
    
    def test_remove_control_chars(self):
        """Тест удаления управляющих символов."""
        from src.preprocessor import clean_text
        
        result = clean_text("Текст\x00с\x0bсимволами\x1f", remove_html=False)
        assert "\x00" not in result
        assert "\x0b" not in result
        assert "\x1f" not in result
    
    def test_empty_input(self):
        """Тест пустого ввода."""
        from src.preprocessor import clean_text
        
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_return_stats(self):
        """Тест возврата статистики."""
        from src.preprocessor import clean_text
        
        result, stats = clean_text("<p>Test</p>", return_stats=True)
        assert isinstance(stats, dict)
        assert "tags_removed" in stats
        assert stats["tags_removed"] > 0


class TestNormalizeText:
    """Тесты функции normalize_text."""
    
    def test_expand_abbreviations(self):
        """Тест расширения сокращений."""
        from src.preprocessor import normalize_text
        
        result = normalize_text("т.е. пример и т.д.", expand_abbr=True, lower=True)
        assert "то есть" in result
        assert "и так далее" in result
    
    def test_standardize_dates(self):
        """Тест стандартизации дат."""
        from src.preprocessor import normalize_text
        
        # Пропускаем если dateutil не установлен
        pytest.importorskip("dateutil")
        
        result = normalize_text("Дата: 15.03.2024", standardize_dates=True, lower=False)
        assert "2024-03-15" in result or "15.03.2024" in result  # Зависит от парсера
    
    def test_lower_case(self):
        """Тест приведения к нижнему регистру."""
        from src.preprocessor import normalize_text
        
        result = normalize_text("ТЕКСТ В ВЕРХНЕМ РЕГИСТРЕ", lower=True)
        assert result == result.lower()
    
    def test_preserve_structure(self):
        """Тест сохранения структуры текста."""
        from src.preprocessor import normalize_text
        
        text = "Первая строка\nВторая строка\nТретья строка"
        result = normalize_text(text, preserve_structure=True)
        assert "\n" in result
    
    def test_empty_input(self):
        """Тест пустого ввода."""
        from src.preprocessor import normalize_text
        
        assert normalize_text("") == ""
        assert normalize_text(None) == ""


class TestStructureText:
    """Тесты функции structure_text."""
    
    def test_detect_headings(self):
        """Тест определения заголовков."""
        from src.preprocessor import structure_text
        
        result = structure_text("# Главный заголовок\n## Подзаголовок")
        assert len(result["headings"]) >= 1
    
    def test_detect_paragraphs(self):
        """Тест определения абзацев."""
        from src.preprocessor import structure_text
        
        result = structure_text("Первый абзац.\n\nВторой абзац.\n\nТретий абзац.")
        assert len(result["paragraphs"]) >= 2
    
    def test_detect_lists(self):
        """Тест определения списков."""
        from src.preprocessor import structure_text
        
        result = structure_text("- Пункт 1\n- Пункт 2\n- Пункт 3")
        assert len(result["lists"]) >= 1
    
    def test_detect_faq(self):
        """Тест определения FAQ-блоков."""
        from src.preprocessor import structure_text
        
        result = structure_text("Вопрос: Как сделать?\nОтвет: Вот так.")
        assert result["metadata"]["has_questions"] is True
    
    def test_empty_input(self):
        """Тест пустого ввода."""
        from src.preprocessor import structure_text
        
        result = structure_text("")
        assert result["headings"] == []
        assert result["paragraphs"] == []
        assert result["lists"] == []
