"""
Модуль генерации ответов с цитатами.

Создаёт ответы на основе найденных документов с автоматическими ссылками на источники.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Цитата из документа."""
    chunk_id: str
    source: str
    page: int
    text: str
    relevance_score: float


@dataclass
class AnswerWithCitations:
    """Ответ с цитатами."""
    answer: str
    citations: List[Citation]
    sources_used: int
    confidence: float
    metadata: Dict[str, Any]


class AnswerGenerator:
    """
    Генерирует ответы с цитатами на основе найденных документов.
    
    Особенности:
    - Автоматическое цитирование источников
    - Оценка уверенности ответа
    - Форматирование цитат
    """
    
    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1",
        citation_format: str = "[source: {chunk_id}, p.{page}]"
    ):
        """
        Инициализация генератора.
        
        Args:
            llm_model: Модель LLM.
            api_key: API ключ.
            api_base: Базовый URL.
            citation_format: Формат цитаты.
        """
        self.llm_model = llm_model
        self.api_key = api_key
        self.api_base = api_base
        self.citation_format = citation_format
        
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
        """Проверяет доступность LLM."""
        return bool(self.api_key)
    
    def generate(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        include_citations: bool = True,
        verbose: bool = False
    ) -> AnswerWithCitations:
        """
        Генерирует ответ с цитатами.
        
        Args:
            query: Запрос пользователя.
            documents: Список найденных документов.
            include_citations: Включить ли цитаты.
            verbose: Выводить ли прогресс.
        
        Returns:
            Ответ с цитатами.
        """
        if not documents:
            return AnswerWithCitations(
                answer="Не найдено релевантных документов для ответа на вопрос.",
                citations=[],
                sources_used=0,
                confidence=0.0,
                metadata={"error": "No documents found"}
            )
        
        if verbose:
            print(f"Генерация ответа на основе {len(documents)} документов...")
        
        # Форматируем контекст
        context = self._format_context(documents)
        
        # Парсим документы в Citation объекты
        citations = self._parse_citations(documents)
        
        if not self.is_available():
            # Fallback: простой ответ без LLM
            answer = self._generate_simple_answer(query, context)
            confidence = 0.5
        else:
            # Генерируем через LLM
            answer, confidence = self._generate_with_llm(
                query, context, include_citations, verbose
            )
        
        return AnswerWithCitations(
            answer=answer,
            citations=citations[:5],  # Ограничиваем цитаты
            sources_used=len(citations),
            confidence=confidence,
            metadata={
                "query": query,
                "total_documents": len(documents),
                "model": self.llm_model
            }
        )
    
    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Форматирует документы в контекст для LLM."""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            text = doc.get('text', '')[:500]  # Ограничиваем длину
            metadata = doc.get('metadata', {})
            chunk_id = metadata.get('chunk_id', f'chunk_{i}')
            page = metadata.get('page_number', 'N/A')
            source = metadata.get('source', 'unknown')
            
            # Формируем заголовок документа
            doc_header = f"--- Документ {i} [ID: {chunk_id}, стр. {page}] ---"
            
            context_parts.append(f"{doc_header}\n{text}")
        
        return "\n\n".join(context_parts)
    
    def _parse_citations(self, documents: List[Dict[str, Any]]) -> List[Citation]:
        """Парсит документы в объекты Citation."""
        citations = []
        
        for doc in documents:
            metadata = doc.get('metadata', {})
            
            citation = Citation(
                chunk_id=metadata.get('chunk_id', 'unknown'),
                source=metadata.get('source', 'unknown'),
                page=metadata.get('page_number', 0),
                text=doc.get('text', '')[:200],
                relevance_score=doc.get('score', 0.0)
            )
            citations.append(citation)
        
        return citations
    
    def _generate_with_llm(
        self,
        query: str,
        context: str,
        include_citations: bool,
        verbose: bool = False
    ) -> tuple:
        """Генерирует ответ через LLM."""
        try:
            from src.llm_chunker import call_llm
            
            # Формируем промпт
            citation_instruction = ""
            if include_citations:
                citation_instruction = """
Для каждого утверждения в ответе укажи источник в формате [ID: chunk_XXX, стр. Y].
Используй информацию из документов, не добавляй выдумок.
"""
            
            prompt = f"""Ответь на вопрос на основе предоставленных документов.

Вопрос: {query}

Документы:
{context}

{citation_instruction}
Требования к ответу:
- Отвечай только на основе предоставленных документов
- Если информации недостаточно, честно об этом скажи
- Ответ должен быть точным и информативным
- Используй цитаты из документов где уместно

Оцени свою уверенность в ответе от 0 до 1 в конце ответа в формате: [Уверенность: 0.XX]

Ответ:"""

            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.3,
                max_tokens=1000
            )
            
            if not response:
                return "Не удалось сгенерировать ответ.", 0.0
            
            # Извлекаем уверенность
            confidence = self._extract_confidence(response)
            
            # Очищаем ответ от метаданных
            answer = self._clean_answer(response)
            
            return answer, confidence
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"Ошибка генерации: {str(e)}", 0.0
    
    def _generate_simple_answer(self, query: str, context: str) -> str:
        """Генерирует простой ответ без LLM."""
        # Просто возвращаем первый релевантный документ
        lines = context.split('\n')
        for line in lines:
            if line.startswith('--- Документ'):
                return f"Найдена информация:\n\n{line}\n\n(Для полного ответа требуется LLM)"
        
        return "Информация найдена, но для генерации ответа требуется LLM."
    
    def _extract_confidence(self, response: str) -> float:
        """Извлекает уверенность из ответа."""
        # Ищем паттерн [Уверенность: 0.XX]
        match = re.search(r'\[Уверенность:\s*(0\.\d+)\]', response, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        # Ищем просто число в конце
        match = re.search(r'(0\.\d+)\s*$', response.strip())
        if match:
            return float(match.group(1))
        
        return 0.5  # Дефолтное значение
    
    def _clean_answer(self, response: str) -> str:
        """Очищает ответ от метаданных."""
        # Удаляем строку с уверенностью
        answer = re.sub(r'\[Уверенность:\s*0\.\d+\]', '', response)
        answer = re.sub(r'0\.\d+\s*$', '', answer)
        
        return answer.strip()
    
    def format_citations(self, citations: List[Citation]) -> str:
        """Форматирует цитаты для отображения."""
        if not citations:
            return "Источники не найдены"
        
        lines = ["**Источники:**"]
        
        for i, cit in enumerate(citations, 1):
            source_name = cit.source.split('/')[-1] if '/' in cit.source else cit.source
            lines.append(
                f"{i}. {source_name} [стр. {cit.page}, {cit.chunk_id}] "
                f"(релевантность: {cit.relevance_score:.2f})"
            )
        
        return "\n".join(lines)


def generate_answer_with_citations(
    query: str,
    documents: List[Dict[str, Any]],
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> Dict[str, Any]:
    """
    Удобная функция для генерации ответа с цитатами.
    
    Args:
        query: Запрос пользователя.
        documents: Список найденных документов.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL.
    
    Returns:
        Словарь с ответом, цитатами и метаданными.
    """
    generator = AnswerGenerator(
        llm_model=llm_model,
        api_key=api_key,
        api_base=api_base
    )
    
    result = generator.generate(query, documents)
    
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
        'sources_used': result.sources_used,
        'confidence': result.confidence,
        'metadata': result.metadata
    }
