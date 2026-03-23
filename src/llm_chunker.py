"""
Модуль LLM-усиленного чанкинга.
Использует LLM для создания качественных чанков и метаданных.
Поддерживает OpenAI (GPT) и Anthropic (Claude).
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

# Глобальный флаг отмены (thread-safe)
_cancel_event = threading.Event()

def request_cancel():
    """Запросить отмену обработки."""
    _cancel_event.set()
    logger.info("LLM: Получен сигнал отмены")

def clear_cancel():
    """Сбросить флаг отмены."""
    _cancel_event.clear()

def is_cancelled() -> bool:
    """Проверить, запрошена ли отмена."""
    return _cancel_event.is_set()

# Попытка импортировать openai
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

# Попытка импортировать anthropic
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


# Список поддерживаемых моделей через proxyAPI
# quality/speed/cost: 1-5 баллов
LLM_MODELS = {
    # ============ OpenAI (работают сразу) ============
    "gpt-4o-mini": {"provider": "openai", "context": 128000, "quality": 3, "speed": 5, "cost": 5, "available": True},
    "gpt-4o": {"provider": "openai", "context": 128000, "quality": 5, "speed": 4, "cost": 3, "available": True},
    "gpt-4o-2024-11-20": {"provider": "openai", "context": 128000, "quality": 5, "speed": 4, "cost": 3, "available": True},
    "gpt-4-turbo": {"provider": "openai", "context": 128000, "quality": 4, "speed": 4, "cost": 3, "available": True},
    "gpt-3.5-turbo": {"provider": "openai", "context": 16000, "quality": 3, "speed": 5, "cost": 5, "available": True},
    
    # ============ Anthropic (Claude) - работают через Anthropic SDK ============
    "claude-sonnet-4-6": {"provider": "anthropic", "context": 1000000, "quality": 5, "speed": 4, "cost": 3, "available": True},
    "claude-sonnet-4-5": {"provider": "anthropic", "context": 1000000, "quality": 5, "speed": 4, "cost": 3, "available": True},
    "claude-opus-4-6": {"provider": "anthropic", "context": 200000, "quality": 5, "speed": 2, "cost": 1, "available": True},
    "claude-haiku-4-5": {"provider": "anthropic", "context": 200000, "quality": 3, "speed": 5, "cost": 5, "available": True},
    
    # ============ Google (Gemini) - пока не работают ============
    "gemini-2.5-pro": {"provider": "google", "context": 1000000, "quality": 5, "speed": 4, "cost": 3, "available": False},
    "gemini-2.5-flash": {"provider": "google", "context": 1000000, "quality": 4, "speed": 5, "cost": 5, "available": False},
    "gemini-3.1-flash-preview": {"provider": "google", "context": 1000000, "quality": 4, "speed": 5, "cost": 4, "available": False},
}


class LLMChunker:
    """
    LLM-усиленный чанкер с опциональным обогащением.
    Поддерживает OpenAI, Anthropic (Claude), Google (Gemini) через proxyAPI.
    """
    
    # Base URLs для разных провайдеров через proxyAPI
    API_BASES = {
        "openai": "https://api.proxyapi.ru/openai/v1",
        "anthropic": "https://api.proxyapi.ru/anthropic",  # Claude через Anthropic SDK
        "google": "https://api.proxyapi.ru/openai/v1",  # Gemini пока не работает
    }
    
    def __init__(
        self, 
        api_key: str = None,
        api_base: str = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Инициализация LLM-ченкера.
        
        Args:
            api_key: API ключ (один для всех провайдеров через proxyAPI).
            api_base: Базовый URL API (опционально, определяется автоматически).
            model: Модель для обработки.
        """
        self.model = model
        self.provider = LLM_MODELS.get(model, {}).get("provider", "openai")
        
        # Определяем base URL
        if api_base:
            self.api_base = api_base
        else:
            self.api_base = self.API_BASES.get(self.provider, self.API_BASES["openai"])
        
        # Получаем API ключ из переменных окружения
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.warning("API ключ не предоставлен. Используйте OPENAI_API_KEY")
            self.client = None
            return
        
        # Инициализация в зависимости от провайдера
        if self.provider == "anthropic":
            # Claude через Anthropic SDK
            if not ANTHROPIC_AVAILABLE:
                logger.warning("anthropic не установлена. Установите: pip install anthropic")
                self.client = None
                return
            self.client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.api_base
            )
            logger.info(f"Claude инициализирован: {model}")
            
        else:
            # OpenAI (и другие через OpenAI-совместимый интерфейс)
            if not OPENAI_AVAILABLE:
                logger.warning("openai не установлена. Установите: pip install openai")
                self.client = None
                return
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base
            )
            logger.info(f"LLM инициализирован: {model} (провайдер: {self.provider})")
            
    def is_available(self) -> bool:
        """Проверяет доступность LLM."""
        return self.client is not None
    
    def enhance_metadata(self, chunks: List[Dict], batch_size: int = 10, cancel_check: callable = None, progress_callback: callable = None) -> List[Dict]:
        """
        Обогащает метаданные чанков через LLM.
        
        Args:
            chunks: Список чанков.
            batch_size: Размер батча для обработки.
            cancel_check: Функция проверки отмены (опционально, также используется глобальный флаг).
            progress_callback: Функция для обновления прогресса (current: int, total: int).
            
        Returns:
            Чанки с расширенными метаданными.
        """
        if not self.is_available():
            logger.warning("LLM недоступен. Пропуск обогащения метаданных.")
            return chunks
        
        logger.info(f"LLM ({self.provider}): Обогащение метаданных для {len(chunks)} чанков")
        
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        # Обрабатываем батчами
        stop_on_error = False  # Флаг для остановки при критических ошибках
        
        for batch_idx, i in enumerate(range(0, len(chunks), batch_size)):
            # Проверяем отмену (глобальный флаг или callback)
            if is_cancelled() or (cancel_check and cancel_check()):
                logger.info("LLM: Обогащение отменено пользователем")
                break
                
            if stop_on_error:
                break
                
            # Обновляем прогресс
            if progress_callback:
                progress_callback(batch_idx + 1, total_batches)
                
            batch = chunks[i:i + batch_size]
            
            prompt = self._build_metadata_prompt(batch)
            
            try:
                if self.provider == "anthropic":
                    # Claude через Anthropic SDK
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=2000,
                        temperature=0.3,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    content = response.content[0].text
                else:
                    # OpenAI и другие
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=2000
                    )
                    content = response.choices[0].message.content
                
                # Парсим ответ
                metadata_batch = self._parse_metadata_response(content)
                
                # Применяем к чанкам
                for j, meta in enumerate(metadata_batch):
                    if i + j < len(chunks):
                        chunks[i + j]['metadata'].update(meta)
                        
            except Exception as e:
                error_msg = str(e)
                logger.error(f"LLM: Ошибка при обогащении метаданных: {e}")
        
                # Проверяем критические ошибки (баланс, авторизация)
                if "402" in error_msg or "Insufficient balance" in error_msg:
                    logger.error("LLM: Недостаточно средств на балансе API. Прекращаем обогащение.")
                    stop_on_error = True
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    logger.error("LLM: Ошибка авторизации API. Прекращаем обогащение.")
                    stop_on_error = True
                elif "403" in error_msg or "Forbidden" in error_msg:
                    logger.error("LLM: Доступ запрещён. Прекращаем обогащение.")
                    stop_on_error = True
        
        return chunks
    
    def _build_metadata_prompt(self, chunks: List[Dict]) -> str:
        """Создаёт промпт для извлечения метаданных."""
        
        chunks_text = []
        for i, chunk in enumerate(chunks):
            chunks_text.append(f"""Chunk {i}:
Text: {chunk['text'][:400]}
Type: {chunk.get('type', 'unknown')}""")
        
        return f"""For each text chunk, extract brief metadata in Russian.
Return JSON array (no markdown):

[
  {{
    "chunk_id": 0,
    "summary": "brief 1-2 sentence summary in Russian",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "intent": "main purpose of this fragment"
  }},
  ...
]

Chunks:
{chr(10).join(chunks_text)}"""
    
    def _parse_metadata_response(self, response: str) -> List[Dict]:
        """Парсит ответ LLM в метаданные."""
        try:
            # Убираем markdown если есть
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            elif "```python" in response:
                response = response.split("```python")[1].split("```")[0]
            
            # Убираем лишние символы в начале и конце
            response = response.strip()
            if response.startswith("["):
                pass  # Уже чистый JSON
            elif "[" in response:
                response = response[response.find("["):response.rfind("]")+1]
            
            return json.loads(response)
        except Exception as e:
            logger.error(f"LLM: Ошибка парсинга метаданных: {e}")
            return []
    
    def smart_chunk_text(self, text: str, max_size: int = 500) -> List[str]:
        """
        Умное разбиение текста по смысловым границам.
        
        Args:
            text: Текст для разбиения.
            max_size: Максимальный размер чанка.
            
        Returns:
            Список текстовых чанков.
        """
        if not self.is_available():
            # Фоллбек на классический метод
            return self._fallback_chunking(text, max_size)
        
        prompt = f"""Разбей текст на смысловые блоки.
Каждый блок должен быть логически завершённым.
Максимальный размер: {max_size} символов.
Верни только список блоков через | разделитель.

Текст:
{text}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4000
            )
            
            chunks = response.choices[0].message.content.split("|")
            return [c.strip() for c in chunks if c.strip()]
            
        except Exception as e:
            logger.error(f"LLM: Ошибка умного разбиения: {e}")
            return self._fallback_chunking(text, max_size)
    
    def _fallback_chunking(self, text: str, max_size: int) -> List[str]:
        """Классическое разбиение как фоллбек."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current = ""
        
        for sent in sentences:
            if len(current) + len(sent) <= max_size:
                current += sent + " "
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = sent + " "
        
        if current.strip():
            chunks.append(current.strip())
        
        return chunks


def call_llm(
    prompt: str,
    model: str = "gpt-4o",
    api_key: str = None,
    api_base: str = "https://api.proxyapi.ru/openai/v1",
    temperature: float = 0.3,
    max_tokens: int = 2000
) -> Optional[str]:
    """
    Универсальный вызов LLM через proxyAPI.
    
    Args:
        prompt: Текст промпта.
        model: Модель LLM (OpenAI, Claude, Gemini).
        api_key: API ключ.
        api_base: Base URL API.
        temperature: Температура генерации.
        max_tokens: Максимум токенов.
    
    Returns:
        Ответ LLM или None при ошибке.
    """
    try:
        chunker = LLMChunker(
            api_key=api_key,
            api_base=api_base,
            model=model
        )
    
        if not chunker.is_available():
            logger.warning("LLM недоступен")
            return None
        
        # Вызов в зависимости от провайдера
        if chunker.provider == "anthropic":
            response = chunker.client.messages.create(
                model=chunker.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        else:
            # OpenAI и другие
            response = chunker.client.chat.completions.create(
                model=chunker.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"LLM call error: {e}")
        return None


def process_chunks_with_llm(
    processed_pages: List[Dict],
    pdf_path: str,
    output_dir: str,
    max_chunk_size: int = 500,
    overlap: int = 50,
    use_llm: bool = True,
    llm_api_key: str = None,
    llm_model: str = "gpt-4o-mini",
    llm_api_base: str = None,
    generate_demo: bool = True,
    progress_callback: callable = None
) -> Dict[str, Any]:
    """
    Обработка чанков с опциональным LLM-обогащением.
    
    Args:
        processed_pages: Обработанные страницы.
        pdf_path: Путь к PDF.
        output_dir: Выходная директория.
        max_chunk_size: Размер чанка.
        overlap: Перекрытие.
        use_llm: Использовать LLM для обогащения.
        llm_api_key: API ключ.
        llm_model: Модель LLM.
        llm_api_base: Base URL для LLM (если None, выбирается автоматически по модели).
        generate_demo: Генерировать демо.
        progress_callback: Функция для обновления прогресса (stage: str, progress: float).
        
    Returns:
        Результат с чанками и метаданными.
    """
    # Импортируем классический чанкер
    from src.chunker import (
        hybrid_chunking, 
        add_metadata, 
        validate_chunks,
        generate_chunking_report,
        generate_chunking_demo
    )
    
    # Классический чанкинг
    all_chunks = []
    
    if progress_callback:
        progress_callback("✂️ Чанкинг", 0.25)
    
    for i, page in enumerate(processed_pages):
        structure = page["structure"]
        chunks = hybrid_chunking(structure, max_chunk_size, overlap)
        chunks_with_meta = add_metadata(chunks, pdf_path, page["page_number"])
        all_chunks.extend(chunks_with_meta)
    
        # Обновляем прогресс чанкинга (25-45%)
        if progress_callback:
            progress = 0.25 + (i / len(processed_pages)) * 0.20
            progress_callback("✂️ Чанкинг", progress)
    
    # Опциональное LLM-обогащение
    llm_enhanced = False
    llm_chunker = None
    
    if use_llm:
        if progress_callback:
            progress_callback("🤖 LLM-обогащение", 0.45)
        
        try:
            # Если llm_api_base не задан, LLMChunker выберет правильный URL автоматически
            llm_chunker = LLMChunker(
                api_key=llm_api_key, 
                model=llm_model,
                api_base=llm_api_base  # None означает автоматический выбор
            )
            
            if llm_chunker.is_available():
                logger.info("LLM: Начало обогащения метаданных...")
                
                # Создаём callback для LLM прогресса
                def llm_progress(current: int, total: int):
                    if progress_callback:
                        # LLM этап: 45-70%
                        progress = 0.45 + (current / total) * 0.25
                        progress_callback("🤖 LLM-обогащение", progress)
                
                all_chunks = llm_chunker.enhance_metadata(all_chunks, progress_callback=llm_progress)
                llm_enhanced = True
                logger.info("LLM: Метаданные успешно обогащены")
            else:
                logger.warning("LLM недоступен, используем базовые метаданные")
        except Exception as e:
            logger.error(f"LLM: Ошибка обогащения: {e}")
    
    # Валидация
    if progress_callback:
        progress_callback("📊 Валидация", 0.70)
    validation = validate_chunks(all_chunks)
    
    # Генерация отчётов
    if progress_callback:
        progress_callback("📝 Генерация отчётов", 0.75)
    report_path = Path("output_module_3") / "chunking_report.txt"
    generate_chunking_report(validation, max_chunk_size, overlap, str(report_path))
    
    demo_path = None
    if generate_demo:
        demo_path = generate_chunking_demo(
            all_chunks, 
            processed_pages, 
            str(Path("output_module_3") / "content_demonstrator.txt")
        )
    
    return {
        "chunks": all_chunks,
        "validation": validation,
        "report_path": str(report_path),
        "demo_path": demo_path,
        "llm_enhanced": llm_enhanced
    }
