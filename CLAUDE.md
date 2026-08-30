# CLAUDE.md — Squeezer

## Обзор проекта

**Squeezer** (v3.5.0) — система обработки PDF-документов для RAG:
извлечение текста (с OCR) → очистка → нормализация → структурирование
→ гибридный чанкинг → метаданные → проверка качества → векторизация.

## Технологический стек

| Компонент | Технология |
|-----------|------------|
| PDF-извлечение | pypdf, pdfplumber |
| OCR | pdf2image + pytesseract |
| Векторная БД | Faiss |
| Эмбеддинги | OpenAI `text-embedding-3-small` |
| LLM (метаданные) | OpenAI / Anthropic через proxyAPI |
| GUI | Tkinter (`gui_app.py`) |

## Команды запуска

```bash
pip install -r requirements.txt
cp .env.example .env   # затем задать OPENAI_API_KEY

python gui_app.py                                    # GUI
python squeezer.py --input document.pdf --output out/  # CLI
pytest                                                # тесты
flake8 . --select=E9,F63,F7,F82                       # проверка, которую реально гоняет CI
```

## Основные компоненты

| Компонент | Файл | Описание |
|-----------|------|----------|
| CLI-точка входа | `squeezer.py` | Аргументы, оркестрация пайплайна |
| GUI-точка входа | `gui_app.py` | Tkinter-интерфейс |
| Чанкинг | `src/chunker.py`, `src/smart_chunker.py`, `src/llm_chunker.py` | Разные стратегии разбиения |
| Векторизация | `src/vectorizer.py` | Faiss + OpenAI embeddings |
| RAG-движок | `src/rag_engine.py`, `src/advanced_rag_pipeline.py` | Поиск + генерация ответа |
| Оценка качества | `Testing_vector_RAG_base/` | Отдельный модуль тестирования RAG-баз |

## Известные особенности (сверено с кодом 2026-08-30)

- **Манифесты синхронизированы** — `requirements.txt` и `pyproject.toml`
  теперь содержат один и тот же список зависимостей; расхождение,
  бывшее здесь ранее, устранено.
- **CI** (`.github/workflows/ci.yml`) реально проходит только строгую
  проверку `flake8 --select=E9,F63,F7,F82` (синтаксис/неопределённые
  имена) — она валит сборку. Вторая команда flake8 и шаг mypy идут
  с `--exit-zero` / `|| true` и никогда не проваливают job.
- **config.json** — не путать пример из README.md с реальным файлом:
  в репозитории могут независимо разойтись `output_dir` и `api_base`,
  сверяйте перед правкой обоих.

## Формат ответа

Коротко, по-русски (кроме коммитов и кода — по-английски). Итог —
2–5 предложений, подробности в файле отчёта, если работа большая.
