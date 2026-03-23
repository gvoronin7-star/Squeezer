# Система тестирования качества RAG-баз

**Версия:** 1.0.0  
**Автор:** Line_GV

---

## Обзор

Комплексная система для оценки качества RAG-баз данных (векторная БД + датасет чанков).

### Категории тестов

| Категория | Вес | Описание |
|-----------|-----|----------|
| **Structure** | 10% | Целостность файлов индекса |
| **Chunks** | 25% | Качество чанков (размер, дубликаты, метаданные) |
| **Search** | 30% | Качество поиска (precision, recall, latency) |
| **Answers** | 25% | Качество ответов (correctness, groundedness) |
| **Coverage** | 10% | Покрытие контента (темы, ключевые слова) |

---

## Установка

### Зависимости

```bash
pip install numpy faiss-cpu openai python-dotenv pyyaml matplotlib
```

### Дополнительно для LLM-оценки

```bash
pip install anthropic  # для Claude моделей
```

---

## Использование

### GUI (рекомендуется)

```bash
cd Testing_vector_RAG_base
python gui_tester.py
```

### CLI

```bash
cd Testing_vector_RAG_base
python rag_quality_tester.py --db-path ../output/vector_db --report report.md
```

### Python API

```python
from Testing_vector_RAG_base.rag_quality_tester import RAGQualityTester

# Создаём тестировщик
tester = RAGQualityTester(
    db_path="./output/vector_db",
    api_key="sk-...",
    llm_model="gpt-4o-mini"
)

# Запускаем все тесты
report = tester.run_all_tests()

# Проверяем результат
print(f"Оценка: {report.total_score}/100")
print(f"Статус: {'✅ ПРОЙДЕНО' if report.passed else '❌ НЕ ПРОЙДЕНО'}")

# Экспорт отчёта
tester.export_report("report.html", format="html")
```

---

## Структура

```
Testing_vector_RAG_base/
├── __init__.py              # Инициализация модуля
├── config.yaml              # Конфигурация тестов
├── rag_quality_tester.py    # Главный модуль тестирования
├── test_chunk_quality.py    # Тесты качества чанков
├── test_search_quality.py   # Тесты качества поиска
├── test_answer_quality.py   # Тесты качества ответов
├── test_coverage.py         # Тесты покрытия контента
├── generate_report.py       # Генератор отчётов
├── gui_tester.py            # GUI приложение
├── README.md                # Документация
├── PROPOSAL.md              # Предложение по реализации
├── test_history.json        # История тестов (создаётся автоматически)
└── reports/                 # Папка для отчётов
```

---

## Тесты

### 1. Structure (Структура)

| Тест | Описание |
|------|----------|
| `index_exists` | Проверка наличия index.faiss |
| `dataset_exists` | Проверка наличия dataset.json |
| `metadata_exists` | Проверка наличия metadata.json |
| `vectors_count_match` | Совпадение количества векторов и чанков |
| `embedding_dimension` | Проверка размерности эмбеддингов |

### 2. Chunks (Чанки)

| Тест | Описание | Порог |
|------|----------|-------|
| `chunk_sizes` | Размер чанков | 70% оптимальных |
| `empty_chunks` | Пустые чанки | 0 |
| `duplicates` | Дубликаты | < 5% |
| `metadata_completeness` | Полнота метаданных | 100% |
| `text_quality` | Качество текста | < 10% проблем |
| `overlap_quality` | Качество перекрытия | > 50% хорошее |

### 3. Search (Поиск)

| Тест | Описание | Порог |
|------|----------|-------|
| `search_availability` | Доступность поиска | работает |
| `latency` | Скорость поиска | < 2 сек |
| `precision_at_k` | Точность топ-K | > 0.7 |
| `recall_at_k` | Полнота топ-K | > 0.7 |
| `result_diversity` | Разнообразие результатов | > 0.5 |
| `edge_cases` | Граничные случаи | нет ошибок |

### 4. Answers (Ответы)

| Тест | Описание | Порог |
|------|----------|-------|
| `answer_generation` | Генерация ответов | работает |
| `correctness` | Правильность | > 0.7 |
| `groundedness` | Поддержка в документах | > 0.7 |
| `completeness` | Полнота | > 0.6 |
| `hallucinations` | Галлюцинации | < 10% |
| `refusal_handling` | Обработка отказов | > 50% |

### 5. Coverage (Покрытие)

| Тест | Описание | Порог |
|------|----------|-------|
| `topic_coverage` | Покрытие тем | > 0.8 |
| `keyword_coverage` | Покрытие ключевых слов | > 0.7 |
| `question_coverage` | Покрытие вопросов | > 0.6 |
| `information_density` | Плотность информации | > 0.5 |
| `source_coverage` | Покрытие источников | > 0.7 |

---

## Конфигурация

Файл `config.yaml`:

```yaml
# Общие настройки
general:
  threshold: 80  # Порог качества (%)
  save_history: true
  history_file: "test_history.json"

# Веса категорий
weights:
  structure: 0.10
  chunks: 0.25
  search: 0.30
  answers: 0.25
  coverage: 0.10

# Пороги тестов
chunk_tests:
  min_size: 100
  max_size: 1000
  max_duplicates_percent: 5

search_tests:
  precision_threshold: 0.7
  recall_threshold: 0.7
  max_latency_seconds: 2.0

answer_tests:
  correctness_threshold: 0.7
  groundedness_threshold: 0.7

coverage_tests:
  topic_coverage_threshold: 0.8
```

---

## GUI

### Возможности

- 📁 Выбор папки с RAG-базой
- ⚙️ Настройка порога качества
- 📊 Визуализация результатов
- 📈 Графики по категориям
- 💡 Рекомендации по улучшению
- 📜 История тестов
- 📤 Экспорт отчётов (Markdown, HTML, JSON)

### Скриншоты

```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Тестирование качества RAG-базы v1.0.0                   │
├─────────────────────────────────────────────────────────────┤
│ 📁 Выбор RAG-базы                                          │
│ Путь: [./output/vector_db              ] [Обзор]           │
│ Порог (%): [80]                                             │
├─────────────────────────────────────────────────────────────┤
│ 📊 Обзор │ 📋 Детали │ 📈 Графики │ 💡 Рекомендации         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│        78/100     ⚠️ НЕ ПРОЙДЕНО                           │
│                                                             │
│ Структура (10%): ████████░░ 85% ✅                         │
│ Чанки (25%):     ███████░░░ 72% ❌                         │
│ Поиск (30%):     █████████░ 82% ✅                         │
│ Ответы (25%):    ██████░░░░ 68% ❌                         │
│ Покрытие (10%):  ████████░░ 80% ✅                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ [████████████████████████████████████████] 100%            │
│ [▶️ Запустить тесты] [📤 Экспорт]                           │
└─────────────────────────────────────────────────────────────┘
```

---

## API

### RAGQualityTester

```python
from Testing_vector_RAG_base import RAGQualityTester

# Инициализация
tester = RAGQualityTester(
    db_path="./output/vector_db",  # Путь к базе
    api_key="sk-...",              # API ключ
    llm_model="gpt-4o-mini"        # Модель LLM
)

# Загрузка базы
tester.load_database()

# Запуск тестов
report = tester.run_all_tests()

# Доступ к результатам
print(f"Общий балл: {report.total_score}")
print(f"Пройден: {report.passed}")

for category, result in report.categories.items():
    print(f"{category}: {result.score}")
    for test in result.tests:
        print(f"  - {test.test_name}: {'✅' if test.passed else '❌'}")

# Экспорт отчёта
tester.export_report("report.html", format="html")
```

---

## История тестов

История сохраняется в `test_history.json`:

```json
[
  {
    "timestamp": "2026-03-23T15:30:00",
    "db_path": "./output/vector_db",
    "total_score": 78.5,
    "passed": false,
    "threshold": 80,
    "duration_seconds": 45.2,
    "categories": {
      "structure": {"score": 100, "passed": true},
      "chunks": {"score": 72, "passed": false},
      ...
    }
  }
]
```

---

## Интеграция с CI/CD

Пример для GitHub Actions:

```yaml
name: Test RAG Quality

on:
  push:
    paths:
      - 'output/vector_db/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run quality tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python Testing_vector_RAG_base/rag_quality_tester.py \
            --db-path output/vector_db \
            --report quality_report.json \
            --format json
      
      - name: Check threshold
        run: |
          score=$(python -c "import json; print(json.load(open('quality_report.json'))['total_score'])")
          if (( $(echo "$score < 80" | bc) )); then
            echo "Quality score $score is below threshold 80"
            exit 1
          fi
```

---

## Рекомендации

### Улучшение качества чанков

1. Оптимизируйте размер чанков (300-600 символов)
2. Удалите пустые чанки
3. Устраните дубликаты
4. Добавьте метаданные

### Улучшение качества поиска

1. Увеличьте top_k для лучшего recall
2. Оптимизируйте эмбеддинги
3. Используйте re-ranking

### Улучшение качества ответов

1. Улучшите промпты
2. Добавьте больше контекста
3. Используйте Self-RAG

---

## Лицензия

MIT License

---

**Автор:** Line_GV  
**Telegram:** @Line_GV  
**GitHub:** https://github.com/gvoronin7-star/Squeezer
