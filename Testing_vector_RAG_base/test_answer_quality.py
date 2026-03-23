"""
Тесты качества ответов.

Метрики:
- Correctness (правильность)
- Groundedness (поддержка в документах)
- Completeness (полнота)
- Hallucinations (галлюцинации)
- Citation accuracy (точность цитат)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

# Добавляем родительскую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Результат теста."""
    test_name: str
    category: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any]


class AnswerQualityTests:
    """
    Тесты качества ответов.
    
    Пример использования:
        tester = AnswerQualityTests(index, dataset, api_key)
        results = tester.run_all_tests()
    """
    
    def __init__(
        self,
        index,
        dataset: List[Dict],
        api_key: str = None,
        llm_model: str = "gpt-4o-mini",
        config: Dict = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1"
    ):
        """
        Инициализация.
        
        Args:
            index: FAISS индекс.
            dataset: Список чанков.
            api_key: API ключ OpenAI.
            llm_model: Модель LLM.
            config: Конфигурация тестов.
            api_base: Базовый URL API.
        """
        self.index = index
        self.dataset = dataset or []
        self.api_key = api_key
        self.llm_model = llm_model
        self.api_base = api_base
        self.config = config or {}
        
        # Параметры по умолчанию
        self.correctness_threshold = self.config.get('correctness_threshold', 0.7)
        self.groundedness_threshold = self.config.get('groundedness_threshold', 0.7)
        self.completeness_threshold = self.config.get('completeness_threshold', 0.6)
        self.max_hallucinations = self.config.get('max_hallucinations_percent', 10)
        self.test_questions_count = self.config.get('test_questions_count', 15)
        
        # Тестовые вопросы
        self.test_questions = self._generate_test_questions()
    
    def _generate_test_questions(self) -> List[Dict]:
        """Генерирует тестовые вопросы из чанков."""
        questions = []
        
        if not self.dataset:
            return questions
        
        # Генерируем вопросы на основе чанков
        step = max(1, len(self.dataset) // self.test_questions_count)
        
        for i in range(0, len(self.dataset), step):
            chunk = self.dataset[i]
            text = chunk.get('text', '')
            
            if len(text) < 100:
                continue
            
            # Создаём вопрос на основе контента
            # Простой подход: "Что сказано о X?"
            words = text.split()[:20]
            if len(words) >= 5:
                topic = ' '.join(words[2:5])  # Берем 2-4 слово как "тему"
                
                questions.append({
                    'question': f"Что сказано о {topic}?",
                    'context': text[:500],
                    'chunk_id': chunk.get('metadata', {}).get('chunk_id', i)
                })
        
        return questions[:self.test_questions_count]
    
    def run_all_tests(self) -> List[TestResult]:
        """Запускает все тесты ответов."""
        results = []
        
        results.append(self.test_answer_generation())
        results.append(self.test_correctness())
        results.append(self.test_groundedness())
        results.append(self.test_completeness())
        results.append(self.test_hallucinations())
        results.append(self.test_refusal_handling())
        
        return results
    
    # ------------------------------------------------------------------------
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ------------------------------------------------------------------------
    
    def _get_embedding(self, text: str):
        """Получает эмбеддинг для текста."""
        try:
            import openai
            import numpy as np
            
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base
            )
            
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            return np.array([response.data[0].embedding], dtype='float32')
            
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга: {e}")
            return None
    
    def _search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Выполняет поиск."""
        import numpy as np
        
        if not self.index or not self.dataset:
            return []
        
        query_vec = self._get_embedding(query)
        if query_vec is None:
            return []
        
        distances, indices = self.index.search(query_vec, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.dataset):
                doc = self.dataset[int(idx)].copy()
                doc['score'] = float(1.0 / (1.0 + dist))
                results.append(doc)
        
        return results
    
    def _generate_answer(self, question: str, context: List[Dict]) -> str:
        """Генерирует ответ через LLM."""
        try:
            from src.llm_chunker import call_llm
            
            # Формируем контекст
            context_text = "\n\n".join([
                f"[{i+1}] {doc.get('text', '')[:300]}"
                for i, doc in enumerate(context[:3])
            ])
            
            prompt = f"""Ответь на вопрос используя предоставленный контекст.

Вопрос: {question}

Контекст:
{context_text}

Ответ:"""
            
            answer = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.3,
                max_tokens=300
            )
            
            return answer or "Не удалось сгенерировать ответ"
            
        except ImportError:
            logger.warning("src.llm_chunker не найден, использую простой ответ")
            return f"Найдено {len(context)} документов. Для генерации ответа требуется LLM."
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return f"Ошибка: {str(e)}"
    
    def _evaluate_with_llm(
        self,
        question: str,
        answer: str,
        context: str,
        criteria: str
    ) -> Dict:
        """Оценивает ответ через LLM."""
        try:
            from src.llm_chunker import call_llm
            
            prompt = f"""Оцени ответ на вопрос по критерию: {criteria}

Вопрос: {question}

Ответ: {answer}

Контекст: {context}

Оцени от 0 до 1 и объясни.

Формат ответа:
score: [число от 0 до 1]
reasoning: [объяснение]"""
            
            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.1,
                max_tokens=200
            )
            
            # Парсим ответ
            score = 0.5
            reasoning = ""
            
            if response:
                for line in response.split('\n'):
                    line = line.strip().lower()
                    if line.startswith('score:'):
                        try:
                            score = float(line.split(':')[1].strip())
                        except:
                            pass
                    elif line.startswith('reasoning:'):
                        reasoning = line.split(':', 1)[1].strip()
            
            return {'score': score, 'reasoning': reasoning}
            
        except ImportError:
            logger.warning("src.llm_chunker не найден, возвращаю дефолтную оценку")
            return {'score': 0.5, 'reasoning': 'LLM недоступен'}
        except Exception as e:
            logger.error(f"Ошибка оценки: {e}")
            return {'score': 0.5, 'reasoning': str(e)}
    
    # ------------------------------------------------------------------------
    # ТЕСТЫ
    # ------------------------------------------------------------------------
    
    def test_answer_generation(self) -> TestResult:
        """Проверяет возможность генерации ответов."""
        if not self.api_key:
            return TestResult(
                test_name="answer_generation",
                category="answers",
                passed=False,
                score=0.0,
                message="API ключ не указан",
                details={}
            )
        
        if not self.test_questions:
            return TestResult(
                test_name="answer_generation",
                category="answers",
                passed=True,
                score=1.0,
                message="Нет тестовых вопросов",
                details={}
            )
        
        # Пробуем сгенерировать ответ
        question_data = self.test_questions[0]
        question = question_data['question']
        
        try:
            # Поиск контекста
            context = self._search(question, top_k=3)
            
            if not context:
                return TestResult(
                    test_name="answer_generation",
                    category="answers",
                    passed=False,
                    score=0.0,
                    message="Контекст не найден",
                    details={}
                )
            
            # Генерация ответа
            answer = self._generate_answer(question, context)
            
            passed = len(answer) > 10 and not answer.startswith("Ошибка")
            score = 1.0 if passed else 0.0
            
            return TestResult(
                test_name="answer_generation",
                category="answers",
                passed=passed,
                score=score,
                message=f"Ответ сгенерирован: {len(answer)} символов",
                details={
                    'answer_length': len(answer),
                    'context_count': len(context)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="answer_generation",
                category="answers",
                passed=False,
                score=0.0,
                message=f"Ошибка: {str(e)}",
                details={'error': str(e)}
            )
    
    def test_correctness(self) -> TestResult:
        """Тестирует правильность ответов."""
        if not self.test_questions or not self.api_key:
            return TestResult(
                test_name="correctness",
                category="answers",
                passed=True,
                score=1.0,
                message="Нет тестовых вопросов или API ключа",
                details={}
            )
        
        scores = []
        
        for q_data in self.test_questions[:5]:  # Тестируем 5 вопросов
            question = q_data['question']
            context = q_data['context']
            
            # Генерируем ответ
            docs = self._search(question, top_k=3)
            answer = self._generate_answer(question, docs)
            
            # Оцениваем правильность
            eval_result = self._evaluate_with_llm(
                question, answer, context,
                "Правильность ответа (соответствует ли контексту)"
            )
            
            scores.append(eval_result['score'])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        passed = avg_score >= self.correctness_threshold
        score = avg_score
        
        return TestResult(
            test_name="correctness",
            category="answers",
            passed=passed,
            score=score,
            message=f"Средняя правильность: {avg_score:.2f}",
            details={
                'avg_score': round(avg_score, 3),
                'samples': len(scores)
            }
        )
    
    def test_groundedness(self) -> TestResult:
        """Тестирует поддержку ответов в документах."""
        if not self.test_questions or not self.api_key:
            return TestResult(
                test_name="groundedness",
                category="answers",
                passed=True,
                score=1.0,
                message="Нет тестовых вопросов или API ключа",
                details={}
            )
        
        scores = []
        
        for q_data in self.test_questions[:5]:
            question = q_data['question']
            
            # Генерируем ответ
            docs = self._search(question, top_k=3)
            answer = self._generate_answer(question, docs)
            
            # Оцениваем groundedness
            context = "\n".join([d.get('text', '')[:200] for d in docs])
            
            eval_result = self._evaluate_with_llm(
                question, answer, context,
                "Groundedness (есть ли поддержка в документах)"
            )
            
            scores.append(eval_result['score'])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        passed = avg_score >= self.groundedness_threshold
        score = avg_score
        
        return TestResult(
            test_name="groundedness",
            category="answers",
            passed=passed,
            score=score,
            message=f"Средняя поддержка: {avg_score:.2f}",
            details={
                'avg_score': round(avg_score, 3),
                'samples': len(scores)
            }
        )
    
    def test_completeness(self) -> TestResult:
        """Тестирует полноту ответов."""
        if not self.test_questions or not self.api_key:
            return TestResult(
                test_name="completeness",
                category="answers",
                passed=True,
                score=1.0,
                message="Нет тестовых вопросов или API ключа",
                details={}
            )
        
        scores = []
        
        for q_data in self.test_questions[:5]:
            question = q_data['question']
            context = q_data['context']
            
            # Генерируем ответ
            docs = self._search(question, top_k=3)
            answer = self._generate_answer(question, docs)
            
            # Оцениваем полноту
            eval_result = self._evaluate_with_llm(
                question, answer, context,
                "Полнота ответа (отвечает ли полностью на вопрос)"
            )
            
            scores.append(eval_result['score'])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        passed = avg_score >= self.completeness_threshold
        score = avg_score
        
        return TestResult(
            test_name="completeness",
            category="answers",
            passed=passed,
            score=score,
            message=f"Средняя полнота: {avg_score:.2f}",
            details={
                'avg_score': round(avg_score, 3),
                'samples': len(scores)
            }
        )
    
    def test_hallucinations(self) -> TestResult:
        """Тестирует наличие галлюцинаций в ответах."""
        if not self.test_questions or not self.api_key:
            return TestResult(
                test_name="hallucinations",
                category="answers",
                passed=True,
                score=1.0,
                message="Нет тестовых вопросов или API ключа",
                details={}
            )
        
        hallucination_count = 0
        total_checked = 0
        
        for q_data in self.test_questions[:5]:
            question = q_data['question']
            
            # Генерируем ответ
            docs = self._search(question, top_k=3)
            answer = self._generate_answer(question, docs)
            
            if not answer or len(answer) < 10:
                continue
            
            total_checked += 1
            
            # Проверяем на галлюцинации через LLM
            context = "\n".join([d.get('text', '')[:200] for d in docs])
            
            eval_result = self._evaluate_with_llm(
                question, answer, context,
                "Есть ли факты в ответе, которые НЕ основаны на контексте? (галлюцинации). Оцени 1 если есть галлюцинации, 0 если ответ основан только на контексте."
            )
            
            # score > 0.7 означает наличие галлюцинаций
            if eval_result['score'] > 0.7:
                hallucination_count += 1
        
        if total_checked == 0:
            return TestResult(
                test_name="hallucinations",
                category="answers",
                passed=True,
                score=1.0,
                message="Недостаточно данных для проверки",
                details={}
            )
        
        hallucination_percent = (hallucination_count / total_checked) * 100
        
        passed = hallucination_percent <= self.max_hallucinations
        score = max(0, 1.0 - hallucination_percent / 100)
        
        return TestResult(
            test_name="hallucinations",
            category="answers",
            passed=passed,
            score=score,
            message=f"Галлюцинаций: {hallucination_count}/{total_checked} ({hallucination_percent:.0f}%)",
            details={
                'hallucination_count': hallucination_count,
                'total_checked': total_checked,
                'hallucination_percent': round(hallucination_percent, 1)
            }
        )
    
    def test_refusal_handling(self) -> TestResult:
        """Тестирует обработку вопросов без ответа."""
        # Вопросы, на которые не должно быть ответа в документах
        impossible_questions = [
            "Сколько стоит луна?",
            "Как приготовить борщ?",
            "Кто выиграл чемпионат мира 2050 года?",
        ]
        
        correct_refusals = 0
        
        for question in impossible_questions:
            try:
                docs = self._search(question, top_k=3)
                answer = self._generate_answer(question, docs)
                
                # Проверяем, что ответ содержит отказ или признание незнания
                answer_lower = answer.lower()
                
                refusal_indicators = [
                    "не знаю", "не могу", "не найден", "не указан",
                    "нет информации", "не содержится", "не могу ответить",
                    "не хватает информации", "не представлен"
                ]
                
                has_refusal = any(ind in answer_lower for ind in refusal_indicators)
                
                if has_refusal or len(answer) < 50:
                    correct_refusals += 1
                    
            except Exception as e:
                logger.warning(f"Ошибка при проверке отказа: {e}")
        
        refusal_rate = correct_refusals / len(impossible_questions)
        
        # Прошёл, если большинство ответов содержат отказ
        passed = refusal_rate >= 0.5
        score = refusal_rate
        
        return TestResult(
            test_name="refusal_handling",
            category="answers",
            passed=passed,
            score=score,
            message=f"Корректных отказов: {correct_refusals}/{len(impossible_questions)}",
            details={
                'refusal_rate': round(refusal_rate, 2),
                'correct_refusals': correct_refusals
            }
        )


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    import faiss
    
    if len(sys.argv) < 3:
        print("Использование: python test_answer_quality.py <index.faiss> <dataset.json>")
        sys.exit(1)
    
    # Загружаем индекс и датасет
    index = faiss.read_index(sys.argv[1])
    with open(sys.argv[2], 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # Запускаем тесты
    tester = AnswerQualityTests(index, dataset)
    results = tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ ОТВЕТОВ")
    print("=" * 60)
    
    for result in results:
        status = "✅" if result.passed else "❌"
        print(f"\n{status} {result.test_name}")
        print(f"   Балл: {result.score * 100:.0f}%")
        print(f"   {result.message}")
    
    avg_score = sum(r.score for r in results) / len(results)
    print(f"\n{'=' * 60}")
    print(f"Средний балл: {avg_score * 100:.1f}%")
    print("=" * 60)
