# Соковыжималка (Squeezer) — RAG-система для обработки PDF-документов

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.4.0-orange.svg)](VERSION)
[![Status](https://img.shields.io/badge/status-production--ready-success.svg)](README.md)
[![Author](https://img.shields.io/badge/author-Line_GV-blue.svg)](https://t.me/Line_GV)

---

## Описание

**Соковыжималка (Squeezer)** — это production-ready система для обработки PDF-документов и подготовки данных для использования в RAG-системах (Retrieval-Augmented Generation).

### Основные возможности

- 📄 **Извлечение текста** из PDF-файлов с поддержкой OCR
- 🧹 **Очистка и нормализация** данных
- 📊 **Структурирование текста** с распознаванием заголовков, списков и FAQ
- ✂️ **Гибридный чанкинг** — семантическое и фиксированное разбиение текста
- 🏷️ **Обогащение метаданными** для каждого чанка
- 🔍 **Проверка качества данных** перед векторизацией
- 🎯 **Векторизация** через OpenAI API
- 💾 **Векторная база данных** на основе FAISS
- 🖥️ **Графический интерфейс** и **CLI**
- 🌐 **Двуязычная поддержка** (русский/английский)
- 📦 **RAG Builder** — создание готовых RAG-баз из PDF-файлов

---

## Быстрый старт

### Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/gvoronin7-star/Squeezer.git
cd Squeezer

# Установите зависимости
pip install -r requirements.txt

# Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env и добавьте свой OPENAI_API_KEY
```

### Запуск через GUI (рекомендуется)

```bash
python gui_app.py
```

### Запуск через CLI

```bash
# Базовая обработка
python squeezer.py --input document.pdf --output output/

# С чанкингом и векторизацией
python squeezer.py --input document.pdf --output output/ --enable-chunking --enable-vectorization
```

### Создание RAG-базы

```bash
python rag_builder.py
```

---

## Документация

| Документ | Описание |
|----------|----------|
| [USER_GUIDE.md](USER_GUIDE.md) | Полное руководство пользователя |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Архитектура проекта и модулей |
| [CHANGELOG.md](CHANGELOG.md) | История изменений |
| [RAG_BUILDER_GUIDE.md](RAG_BUILDER_GUIDE.md) | Руководство по созданию RAG-баз |
| [BACKUP_GUIDE.md](BACKUP_GUIDE.md) | Руководство по бэкапу и восстановлению |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Как внести вклад в проект |
| [DOCS_INDEX.md](DOCS_INDEX.md) | Индекс всей документации |

API документация:
- [Модуль 2.1 (GUI)](docs/MODULE_2.1_API.md)
- [Модуль 3 (Чанкинг)](docs/MODULE_3_API.md)
- [Модуль 4 (Векторизация)](docs/MODULE_4_API.md)
- [Модуль 5 (RAG Builder)](docs/MODULE_5_API.md)

---

## Архитектура

Система состоит из 5 основных модулей:

### Модуль 1: Базовый каркас
- Конфигурация системы
- Логирование
- Управление путями

### Модуль 2: Предобработка текста (Этапы 1-4)
1. Извлечение текста из PDF с OCR
2. Очистка данных
3. Нормализация данных
4. Структурирование текста

### Модуль 2.1: Графический интерфейс
- Загрузка PDF-файлов
- Управление обработкой
- Отображение прогресса

### Модуль 3: Чанкинг и метаданные (Этапы 5-6)
5. Гибридный чанкинг
6. Добавление метаданных

### Модуль 4: Векторизация и БД (Этапы 7-8)
7. Проверка качества данных
8. Векторизация через OpenAI API
9. Создание векторной БД FAISS

### Модуль 5: RAG Builder
- Создание готовых RAG-баз
- Генерация инструкций по подключению
- Примеры кода для интеграции

---

## Использование как библиотеки

```python
from src.preprocessor import process_pdf
from dotenv import load_dotenv

load_dotenv()

result = process_pdf(
    pdf_path="document.pdf",
    output_dir="output/",
    enable_chunking=True,
    enable_vectorization=True
)

# Доступ к результатам
chunks = result["chunks"]
vectorization = result["vectorization"]
```

---

## Выходные данные

### После обработки
- `output_module_2/report.txt` — отчёт по обработке
- `output_module_3/chunking_report.txt` — отчёт по чанкингу
- `output_module_4/vectorization_report.txt` — отчёт по векторизации
- `output/vector_db/index.faiss` — индекс FAISS
- `output/vector_db/dataset.json` — датасет с чанками
- `output/vector_db/metadata.json` — метаданные индекса

### После создания RAG-базы
- `rag_bases/MyBase/README_RAG.md` — инструкция по подключению
- `rag_bases/MyBase/example_connection.py` — пример кода
- `rag_bases/MyBase/index.faiss` — индекс FAISS
- `rag_bases/MyBase/dataset.json` — датасет
- `rag_bases/MyBase/metadata.json` — метаданные
- `rag_bases/MyBase/source_documents/` — исходные PDF

---

## Требования

- Python 3.8+
- pip
- API ключ OpenAI (для векторизации)

### Зависимости

- PyPDF2 — работа с PDF
- pdfplumber — извлечение текста
- pytesseract — OCR
- openai — эмбеддинги
- faiss-cpu — векторная БД
- numpy — работа с массивами
- python-dotenv — переменные окружения

Полный список см. в [requirements.txt](requirements.txt)

---

## Примеры использования

### 1. База знаний компании

```bash
# Создаём RAG-базу из документации
python rag_builder.py
# Добавляем PDF-файлы, называем базу "CompanyKnowledgeBase"
# Получаем готовую базу для интеграции в ассистент
```

### 2. Научные исследования

```bash
# Обрабатываем научные статьи
python squeezer.py --input papers/ --output output/ --enable-chunking --enable-vectorization
# Используем векторную БД для поиска релевантных исследований
```

### 3. Юридические документы

```bash
# Создаём базу законов и нормативов
python rag_builder.py
# Интегрируем в юридического ассистента
```

---

## Бэкап и восстановление

```bash
# Создание бэкапа
python create_backup.py

# Восстановление из бэкапа
python restore_backup.py
```

Подробнее: [BACKUP_GUIDE.md](BACKUP_GUIDE.md)

---

## Вклад в проект

Мы приветствуем вклад в развитие проекта! См. [CONTRIBUTING.md](CONTRIBUTING.md)

### Как внести вклад

1. Форкните репозиторий
2. Создайте ветку для вашей функции (`git checkout -b feature/AmazingFeature`)
3. Зафиксируйте изменения (`git commit -m 'Add: some AmazingFeature'`)
4. Отправьте изменения (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## Поддержка

- **Автор:** [Line_GV](https://t.me/Line_GV)
- **Telegram:** [@Line_GV](https://t.me/Line_GV)
- **Issues:** [GitHub Issues](https://github.com/gvoronin7-star/Squeezer/issues)

---

## Лицензия

Этот проект лицензирован под MIT License — см. файл [LICENSE](LICENSE)

---

## Статус

✅ **Production Ready** — система протестирована и готова к использованию в production.

---

## Благодарности

Проект разработан в рамках обучения Prompt Engineering 3.0 от Zerocoder.
