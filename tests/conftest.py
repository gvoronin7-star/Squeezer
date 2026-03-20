"""
Конфигурация pytest для тестов Squeezer.
"""

import pytest
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_pdf_path():
    """Путь к тестовому PDF файлу."""
    return Path(__file__).parent.parent / "pdfs" / "test_document.pdf"


@pytest.fixture
def sample_chunks():
    """Пример чанков для тестирования."""
    return [
        {
            "text": "Первый тестовый чанк для проверки.",
            "type": "paragraph",
            "metadata": {
                "source": "test.pdf",
                "page_number": 1,
                "chunk_id": "chunk_000"
            }
        },
        {
            "text": "Второй тестовый чанк с другим содержимым.",
            "type": "paragraph",
            "metadata": {
                "source": "test.pdf",
                "page_number": 1,
                "chunk_id": "chunk_001"
            }
        }
    ]


@pytest.fixture
def sample_structure():
    """Пример структуры текста для тестирования."""
    return {
        "headings": ["Заголовок 1", "Заголовок 2"],
        "paragraphs": [
            "Первый абзац текста для проверки.",
            "Второй абзац с другим содержимым."
        ],
        "lists": [
            ["- Пункт 1", "- Пункт 2", "- Пункт 3"]
        ]
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Временная директория для вывода."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_env_api_key(monkeypatch):
    """Мок API ключа для тестов."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_api_key_12345")
    return "test_api_key_12345"
