"""
Self-RAG: RAG с самооценкой качества.

Оценивает релевантность документов и качество ответа.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RelevanceScore(Enum):
    """Оценка релевантности."""
    FULLY_RELEVANT = "fully_relevant"      # Полностью релевантен
    PARTIALLY_RELEVANT = "partially"       # Частично релевантен
    NOT_RELEVANT = "not_relevant"          # Не релевантен


class AnswerQuality(Enum):
    """Оценка качества ответа."""
    EXCELLENT = "excellent"                # Отлично
    GOOD = "good"                          # Хорошо
    PARTIAL = "partial"                    # Частично
    INSUFFICIENT = "insufficient"          # Недостаточно


@dataclass
class DocumentEvaluation:
    """Оценка документа."""
    chunk_id: str
    relevance: RelevanceScore
    relevance_score: float
    reasoning: str


@dataclass
class AnswerEvaluation:
    """Оценка ответа."""
    quality: AnswerQuality
    confidence: float
    grounded: bool  # Есть ли поддержка в документах
    hallucinations: bool  # Есть ли выдумки
    missing_info: List[str]  # Недостающая информация
    reasoning: str


@dataclass
class SelfRAGResult:
    """Результат Self-RAG."""
    answer: str
    documents_used: List[Dict[str, Any]]
    doc_evaluations: List[DocumentEvaluation]
    answer_evaluation: AnswerEvaluation
    iterations: int
    final_confidence: float


class SelfRAG:
    """
    Self-RAG: Самокорректирующийся RAG.
    
    Этапы:
    1. Поиск документов
    2. Оценка релевантности каждого документа (LLM)
    3. Фильтрация нерелевантных
    4. Генерация ответа
    5. Оценка качества ответа
    6. Повтор при необходимости
    """
    
    def __init__(
        self,
        vector_store=None,
        llm_model: str = "gpt-4o-mini",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1",
        max_iterations: int = 2,
        relevance_threshold: float = 0.3
    ):
        """
        Инициализация Self-RAG.
        
        Args:
            vector_store: Векторное хранилище (FAISS).
            llm_model: Модель LLM.
            api_key: API ключ.
            api_base: Базовый URL.
            max_iterations: Максимум итераций.
            relevance_threshold: Порог релевантности.
        """
        self.vector_store = vector_store
        self.llm_model = llm_model
        self.api_key = api_key
        self.api_base = api_base
        self.max_iterations = max_iterations
        self.relevance_threshold = relevance_threshold
        
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
    
    def query(
        self,
        query: str,
        top_k: int = 5,
        verbose: bool = False
    ) -> SelfRAGResult:
        """
        Выполняет запрос с самооценкой.
        
        Args:
            query: Запрос пользователя.
            top_k: Количество документов для поиска.
            verbose: Выводить ли прогресс.
        
        Returns:
            Результат с оценками.
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"Self-RAG: {query}")
            print(f"{'='*60}\n")
        
        # Загружаем .env для вызова LLM
        try:
            from src.llm_chunker import call_llm
        except ImportError:
            call_llm = None
        
        if not self.is_available() or call_llm is None:
            # Fallback: простой RAG без самооценки
            return self._fallback_rag(query, top_k, verbose)
        
        all_documents = []
        all_evaluations = []
        
        for iteration in range(1, self.max_iterations + 1):
            if verbose:
                print(f"\n--- Итерация {iteration} ---")
            
            # 1. Поиск документов
            documents = self._search(query, top_k)
            
            if not documents:
                if verbose:
                    print("Документы не найдены")
                break
            
            # 2. Оценка релевантности
            if iteration == 1:
                evaluations = self._evaluate_documents(query, documents, verbose)
                all_evaluations.extend(evaluations)
                
                # 3. Фильтрация
                relevant_docs = self._filter_relevant(documents, evaluations)
                
                if verbose:
                    relevant = len(relevant_docs)
                    print(f"Релевантных документов: {relevant}/{len(documents)}")
                
                if not relevant_docs:
                    if verbose:
                        print("Нет релевантных документов")
                    break
                
                all_documents.extend(relevant_docs)
            else:
                all_documents.extend(documents)
            
            # 4. Генерация ответа
            answer, confidence = self._generate_answer(
                query, all_documents, verbose
            )
            
            # 5. Оценка ответа
            answer_eval = self._evaluate_answer(
                query, answer, all_documents, verbose
            )
            
            if verbose:
                print(f"\nОценка ответа: {answer_eval.quality.value}")
                print(f"Уверенность: {answer_eval.confidence:.2f}")
                print(f"О grounded: {answer_eval.grounded}")
            
            # Проверяем, нужно ли повторить
            if answer_eval.quality in [AnswerQuality.EXCELLENT, AnswerQuality.GOOD]:
                break
            
            if iteration == self.max_iterations:
                if verbose:
                    print("Достигнут лимит итераций")
                break
        
        # Финальная оценка
        final_confidence = self._calculate_final_confidence(
            all_evaluations, answer_eval if 'answer_eval' in locals() else None
        )
        
        return SelfRAGResult(
            answer=answer if 'answer' in locals() else "Не удалось сгенерировать ответ",
            documents_used=all_documents[:top_k],
            doc_evaluations=all_evaluations,
            answer_evaluation=answer_eval if 'answer_eval' in locals() else AnswerEvaluation(
                quality=AnswerQuality.INSUFFICIENT,
                confidence=0.0,
                grounded=False,
                hallucinations=True,
                missing_info=[],
                reasoning="No evaluation"
            ),
            iterations=iteration,
            final_confidence=final_confidence
        )
    
    def _search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Ищет документы."""
        if self.vector_store is None:
            return []
        
        try:
            # Импорт здесь чтобы избежать циклических импортов
            from src.vectorizer import save_to_vector_db
            
            # Пробуем разные методы поиска
            if hasattr(self.vector_store, 'similarity_search'):
                docs = self.vector_store.similarity_search(query, k=top_k)
                return docs
            elif hasattr(self.vector_store, 'search'):
                return self.vector_store.search(query, k=top_k)
            else:
                logger.warning("vector_store не имеет метода search")
                return []
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []
    
    def _evaluate_documents(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        verbose: bool = False
    ) -> List[DocumentEvaluation]:
        """Оценивает релевантность документов."""
        from src.llm_chunker import call_llm
        
        evaluations = []
        
        for i, doc in enumerate(documents):
            text = doc.get('text', '')[:500]  # Ограничиваем для экономии токенов
            chunk_id = doc.get('metadata', {}).get('chunk_id', f'chunk_{i}')
            
            if verbose:
                print(f"Оцениваю документ {i+1}/{len(documents)}...")
            
            prompt = f"""Оцени релевантность документа для запроса.

Запрос: {query}

Документ:
{text}

Оцени по шкале:
- fully_relevant: Документ полностью отвечает на запрос
- partially: Документ частично релевантен
- not_relevant: Документ не релевантен

Также оцени релевантность от 0 до 1.

Ответь в формате:
relevance: [fully_relevant|partially|not_relevant]
score: [число от 0 до 1]
reasoning: [краткое объяснение]"""

            try:
                response = call_llm(
                    prompt=prompt,
                    model=self.llm_model,
                    api_key=self.api_key,
                    api_base=self.api_base,
                    temperature=0.1,
                    max_tokens=200
                )
                
                # Парсим ответ
                relevance = RelevanceScore.PARTIALLY_RELEVANT
                score = 0.5
                reasoning = ""
                
                for line in response.split('\n'):
                    line = line.strip().lower()
                    if line.startswith('relevance:'):
                        if 'fully' in line:
                            relevance = RelevanceScore.FULLY_RELEVANT
                        elif 'not' in line:
                            relevance = RelevanceScore.NOT_RELEVANT
                    elif line.startswith('score:'):
                        try:
                            score = float(line.split(':')[1].strip())
                        except:
                            pass
                    elif line.startswith('reasoning:'):
                        reasoning = line.split(':', 1)[1].strip()
                
                evaluations.append(DocumentEvaluation(
                    chunk_id=chunk_id,
                    relevance=relevance,
                    relevance_score=score,
                    reasoning=reasoning
                ))
                
            except Exception as e:
                logger.error(f"Ошибка оценки документа: {e}")
                evaluations.append(DocumentEvaluation(
                    chunk_id=chunk_id,
                    relevance=RelevanceScore.PARTIALLY_RELEVANT,
                    relevance_score=0.5,
                    reasoning=str(e)
                ))
        
        return evaluations
    
    def _filter_relevant(
        self,
        documents: List[Dict[str, Any]],
        evaluations: List[DocumentEvaluation]
    ) -> List[Dict[str, Any]]:
        """Фильтрует релевантные документы."""
        relevant = []
        
        for doc, eval in zip(documents, evaluations):
            if eval.relevance in [RelevanceScore.FULLY_RELEVANT, 
                                  RelevanceScore.PARTIALLY_RELEVANT]:
                if eval.relevance_score >= self.relevance_threshold:
                    relevant.append(doc)
        
        return relevant
    
    def _generate_answer(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        verbose: bool = False
    ) -> tuple:
        """Генерирует ответ."""
        from src.llm_chunker import call_llm
        
        # Форматируем контекст
        context_parts = []
        for i, doc in enumerate(documents[:5], 1):
            text = doc.get('text', '')[:400]
            chunk_id = doc.get('metadata', {}).get('chunk_id', f'chunk_{i}')
            page = doc.get('metadata', {}).get('page_number', 'N/A')
            context_parts.append(f"--- Источник {i} [стр. {page}, {chunk_id}] ---\n{text}")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Ответь на вопрос используя предоставленные документы.

Вопрос: {query}

Документы:
{context}

Требования:
- Отвечай только на основе документов
- Укажи источники в формате [стр. X, источник Y]
- Если информации недостаточно, честно скажи об этом

Ответ:"""
        
        try:
            answer = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.3,
                max_tokens=800
            )
            
            # Оценка уверенности
            confidence = 0.7  # Дефолтное значение
            
            return answer or "Не удалось сгенерировать ответ", confidence
            
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            return f"Ошибка: {str(e)}", 0.0
    
    def _evaluate_answer(
        self,
        query: str,
        answer: str,
        documents: List[Dict[str, Any]],
        verbose: bool = False
    ) -> AnswerEvaluation:
        """Оценивает качество ответа."""
        from src.llm_chunker import call_llm
        
        # Формируем контекст из документов
        doc_texts = "\n".join([d.get('text', '')[:200] for d in documents[:3]])
        
        prompt = f"""Оцени качество ответа на вопрос.

Вопрос: {query}

Ответ:
{answer}

Контекст из документов:
{doc_texts}

Оцени по критериям:
1. Качество: excellent|good|partial|insufficient
2. Есть ли поддержка в документах (grounded): yes|no
3. Есть ли выдумки (hallucinations): yes|no
4. Чего не хватает (missing_info): список

Ответь в формате:
quality: [excellent|good|partial|insufficient]
grounded: [yes|no]
hallucinations: [yes|no]
missing_info: [чего не хватает через запятую]
reasoning: [объяснение]"""

        try:
            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.1,
                max_tokens=300
            )
            
            # Парсим ответ
            quality = AnswerQuality.GOOD
            grounded = True
            hallucinations = False
            missing = []
            reasoning = ""
            
            for line in response.split('\n'):
                line = line.strip().lower()
                if line.startswith('quality:'):
                    if 'excellent' in line:
                        quality = AnswerQuality.EXCELLENT
                    elif 'partial' in line:
                        quality = AnswerQuality.PARTIAL
                    elif 'insufficient' in line:
                        quality = AnswerQuality.INSUFFICIENT
                elif line.startswith('grounded:'):
                    grounded = 'yes' in line
                elif line.startswith('hallucinations:'):
                    hallucinations = 'yes' in line
                elif line.startswith('missing_info:'):
                    missing = [x.strip() for x in line.split(':')[1].split(',')]
                elif line.startswith('reasoning:'):
                    reasoning = line.split(':', 1)[1].strip()
            
            # Вычисляем confidence
            confidence = 0.8 if quality == AnswerQuality.EXCELLENT else (
                0.6 if quality == AnswerQuality.GOOD else (
                    0.4 if quality == AnswerQuality.PARTIAL else 0.2
                )
            )
            
            if hallucinations:
                confidence -= 0.2
            if not grounded:
                confidence -= 0.2
            
            return AnswerEvaluation(
                quality=quality,
                confidence=confidence,
                grounded=grounded,
                hallucinations=hallucinations,
                missing_info=missing,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Ошибка оценки ответа: {e}")
            return AnswerEvaluation(
                quality=AnswerQuality.PARTIAL,
                confidence=0.5,
                grounded=True,
                hallucinations=False,
                missing_info=[],
                reasoning=str(e)
            )
    
    def _calculate_final_confidence(
        self,
        doc_evaluations: List[DocumentEvaluation],
        answer_eval: Optional[AnswerEvaluation]
    ) -> float:
        """Вычисляет финальную уверенность."""
        if not doc_evaluations and not answer_eval:
            return 0.0
        
        doc_score = 0.0
        if doc_evaluations:
            doc_score = sum(e.relevance_score for e in doc_evaluations) / len(doc_evaluations)
        
        answer_score = answer_eval.confidence if answer_eval else 0.5
        
        # Среднее взвешенное
        return (doc_score * 0.4 + answer_score * 0.6)
    
    def _fallback_rag(
        self,
        query: str,
        top_k: int,
        verbose: bool = False
    ) -> SelfRAGResult:
        """Fallback RAG без LLM оценки."""
        documents = self._search(query, top_k)
        
        if not documents:
            return SelfRAGResult(
                answer="Документы не найдены",
                documents_used=[],
                doc_evaluations=[],
                answer_evaluation=AnswerEvaluation(
                    quality=AnswerQuality.INSUFFICIENT,
                    confidence=0.0,
                    grounded=False,
                    hallucinations=False,
                    missing_info=[],
                    reasoning="No documents found"
                ),
                iterations=1,
                final_confidence=0.0
            )
        
        # Простой ответ без оценки
        answer = f"Найдено {len(documents)} документов. Для полного ответа требуется LLM."
        
        return SelfRAGResult(
            answer=answer,
            documents_used=documents,
            doc_evaluations=[],
            answer_evaluation=AnswerEvaluation(
                quality=AnswerQuality.PARTIAL,
                confidence=0.5,
                grounded=True,
                hallucinations=False,
                missing_info=[],
                reasoning="Fallback mode"
            ),
            iterations=1,
            final_confidence=0.5
        )


def self_rag_query(
    query: str,
    vector_store=None,
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Удобная функция для Self-RAG запроса.
    
    Args:
        query: Запрос пользователя.
        vector_store: Векторное хранилище.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL.
        top_k: Количество документов.
    
    Returns:
        Результат с оценками.
    """
    rag = SelfRAG(
        vector_store=vector_store,
        llm_model=llm_model,
        api_key=api_key,
        api_base=api_base
    )
    
    result = rag.query(query, top_k=top_k)
    
    return {
        'answer': result.answer,
        'documents': [
            {
                'text': d.get('text', ''),
                'metadata': d.get('metadata', {}),
                'evaluation': {
                    'relevance': e.relevance.value,
                    'score': e.relevance_score,
                    'reasoning': e.reasoning
                }
            }
            for d, e in zip(result.documents_used, result.doc_evaluations)
        ],
        'answer_evaluation': {
            'quality': result.answer_evaluation.quality.value,
            'confidence': result.answer_evaluation.confidence,
            'grounded': result.answer_evaluation.grounded,
            'hallucinations': result.answer_evaluation.hallucinations,
            'missing_info': result.answer_evaluation.missing_info
        },
        'iterations': result.iterations,
        'final_confidence': result.final_confidence
    }
