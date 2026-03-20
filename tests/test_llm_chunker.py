"""
Unit-тесты для модуля llm_chunker.
"""

import pytest


class TestLLMChunkerInit:
    """Тесты инициализации LLMChunker."""
    
    def test_init_without_api_key(self, monkeypatch):
        """Тест инициализации без API ключа."""
        from src.llm_chunker import LLMChunker
        
        # Убираем переменную окружения
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        chunker = LLMChunker()
        assert chunker.api_key is None
        assert not chunker.is_available()
    
    def test_init_with_api_key(self):
        """Тест инициализации с API ключом."""
        from src.llm_chunker import LLMChunker
        
        chunker = LLMChunker(api_key="test_key", model="gpt-4o-mini")
        assert chunker.api_key == "test_key"
        assert chunker.model == "gpt-4o-mini"
    
    def test_provider_detection(self):
        """Тест определения провайдера."""
        from src.llm_chunker import LLMChunker
        
        # OpenAI
        chunker_openai = LLMChunker(model="gpt-4o-mini", api_key="test")
        assert chunker_openai.provider == "openai"
        
        # Anthropic
        chunker_claude = LLMChunker(model="claude-sonnet-4-6", api_key="test")
        assert chunker_claude.provider == "anthropic"


class TestLLMModelsConfig:
    """Тесты конфигурации моделей."""
    
    def test_models_dict_exists(self):
        """Тест наличия словаря моделей."""
        from src.llm_chunker import LLM_MODELS
        
        assert isinstance(LLM_MODELS, dict)
        assert len(LLM_MODELS) > 0
    
    def test_openai_models_available(self):
        """Тест доступности OpenAI моделей."""
        from src.llm_chunker import LLM_MODELS
        
        openai_models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        for model in openai_models:
            assert model in LLM_MODELS
            assert LLM_MODELS[model]["provider"] == "openai"
    
    def test_anthropic_models_available(self):
        """Тест доступности Anthropic моделей."""
        from src.llm_chunker import LLM_MODELS
        
        anthropic_models = ["claude-sonnet-4-6", "claude-haiku-4-5"]
        for model in anthropic_models:
            assert model in LLM_MODELS
            assert LLM_MODELS[model]["provider"] == "anthropic"
    
    def test_model_has_required_fields(self):
        """Тест наличия обязательных полей в конфигурации модели."""
        from src.llm_chunker import LLM_MODELS
        
        required_fields = ["provider", "context", "quality", "speed", "cost"]
        
        for model_name, config in LLM_MODELS.items():
            for field in required_fields:
                assert field in config, f"Model {model_name} missing field {field}"


class TestMetadataPrompt:
    """Тесты генерации промптов для метаданных."""
    
    def test_build_metadata_prompt(self):
        """Тест построения промпта для метаданных."""
        from src.llm_chunker import LLMChunker
        
        chunker = LLMChunker(api_key="test")
        
        chunks = [
            {"text": "Тестовый текст для проверки", "type": "paragraph"},
            {"text": "Второй чанк для теста", "type": "paragraph"}
        ]
        
        prompt = chunker._build_metadata_prompt(chunks)
        
        assert "Chunk 0" in prompt
        assert "Chunk 1" in prompt
        assert "JSON" in prompt or "json" in prompt
    
    def test_parse_metadata_response_valid_json(self):
        """Тест парсинга валидного JSON ответа."""
        from src.llm_chunker import LLMChunker
        
        chunker = LLMChunker(api_key="test")
        
        response = '''[
            {"chunk_id": 0, "summary": "Тест", "keywords": ["test"], "intent": "test"},
            {"chunk_id": 1, "summary": "Тест 2", "keywords": ["test2"], "intent": "test2"}
        ]'''
        
        result = chunker._parse_metadata_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["chunk_id"] == 0
    
    def test_parse_metadata_response_with_markdown(self):
        """Тест парсинга JSON в markdown блоке."""
        from src.llm_chunker import LLMChunker
        
        chunker = LLMChunker(api_key="test")
        
        response = '''```json
[
    {"chunk_id": 0, "summary": "Тест", "keywords": ["test"], "intent": "test"}
]
```'''
        
        result = chunker._parse_metadata_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_parse_metadata_response_invalid(self):
        """Тест парсинга невалидного ответа."""
        from src.llm_chunker import LLMChunker
        
        chunker = LLMChunker(api_key="test")
        
        result = chunker._parse_metadata_response("invalid json")
        assert result == []


class TestFallbackChunking:
    """Тесты fallback чанкинга."""
    
    def test_fallback_chunking_basic(self):
        """Тест базового fallback чанкинга."""
        from src.llm_chunker import LLMChunker
        
        chunker = LLMChunker(api_key="test")
        
        text = "Первое предложение. Второе предложение. Третье предложение."
        chunks = chunker._fallback_chunking(text, max_size=50)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
    
    def test_fallback_chunking_respects_size(self):
        """Тест соблюдения размера при fallback чанкинге."""
        from src.llm_chunker import LLMChunker
        
        chunker = LLMChunker(api_key="test")
        
        text = "Длинный текст. " * 20
        chunks = chunker._fallback_chunking(text, max_size=100)
        
        # Все чанки должны быть не сильно больше max_size
        assert all(len(c) <= 150 for c in chunks)


class TestCallLlm:
    """Тесты функции call_llm."""
    
    def test_call_llm_without_key(self, monkeypatch):
        """Тест вызова LLM без ключа."""
        from src.llm_chunker import call_llm
        
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        result = call_llm("test prompt", api_key=None)
        assert result is None
    
    def test_call_llm_with_invalid_key(self):
        """Тест вызова LLM с невалидным ключом."""
        from src.llm_chunker import call_llm
        
        # Должен вернуть None при ошибке
        result = call_llm(
            "test prompt",
            api_key="invalid_key",
            model="gpt-4o-mini"
        )
        # Не падаем, просто возвращаем None
        assert result is None or isinstance(result, str)
