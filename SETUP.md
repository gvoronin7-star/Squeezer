# Установка и настройка "Соковыжималка" (Squeezer)

**Версия:** 3.1.0  
**Статус:** Production Ready

---

## Системные требования

### Минимальные требования

- **Операционная система:** Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python:** 3.8 или выше
- **RAM:** 4 ГБ (рекомендуется 8 ГБ)
- **Место на диске:** 500 МБ + место для PDF-файлов и выходных данных
- **Интернет-соединение:** Для векторизации (OpenAI API)

### Рекомендуемые требования

- **Python:** 3.9+
- **RAM:** 8 ГБ+
- **Место на диске:** 2 ГБ+

---

## Установка

### Шаг 1: Проверка версии Python

Проверьте, что у вас установлен Python 3.8 или выше:

```bash
python --version
# или
python3 --version
```

Если Python не установлен, скачайте его с [python.org](https://www.python.org/downloads/)

### Шаг 2: Клонирование репозитория

```bash
# Клонируйте репозиторий
git clone https://github.com/gvoronin7-star/Squeezer.git
cd Squeezer

# Или скачайте ZIP архив с GitHub и распакуйте его
```

### Шаг 3: Создание виртуального окружения (рекомендуется)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Шаг 4: Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 5: Установка Tesseract OCR (для сканированных PDF)

#### Windows

1. Скачайте установщик с [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Установите Tesseract
3. Добавьте путь к Tesseract в PATH (обычно `C:\Program Files\Tesseract-OCR`)

#### macOS

```bash
brew install tesseract
brew install tesseract-lang
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-rus tesseract-ocr-eng
```

### Шаг 6: Настройка переменных окружения

```bash
# Скопируйте пример файла .env
cp .env.example .env

# Откройте .env в текстовом редакторе и заполните свои значения
# Обязательно укажите OPENAI_API_KEY
```

Пример `.env`:

```env
# API ключ OpenAI (обязательно для векторизации)
OPENAI_API_KEY=your-api-key-here

# Базовый URL API (опционально, для прокси)
OPENAI_API_BASE=https://openai.api.proxyapi.ru/v1

# Модель эмбеддингов (опционально)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Язык OCR (опционально)
OCR_LANG=rus+eng

# Размер чанка по умолчанию (опционально)
DEFAULT_CHUNK_SIZE=500

# Перекрытие между чанками (опционально)
DEFAULT_OVERLAP=50

# Уровень логирования (опционально)
LOG_LEVEL=INFO

# Язык интерфейса (опционально)
LANGUAGE=ru
```

---

## Проверка установки

### Тест 1: Проверка импортов

```bash
python -c "import PyPDF2; import pdfplumber; import pytesseract; import openai; import faiss; print('Все модули установлены успешно!')"
```

### Тест 2: Проверка Tesseract OCR

```bash
tesseract --version
```

### Тест 3: Проверка GUI

```bash
python gui_app.py
```

Должно открыться окно приложения.

### Тест 4: Проверка CLI

```bash
python squeezer.py --help
```

Должна отобразиться справка по использованию.

---

## Конфигурация

### config.json

Основные параметры настраиваются в `config.json`:

```json
{
  "version": "3.1.0",
  "author": "Line_GV",
  "author_url": "https://t.me/Line_GV",
  "release_date": "2026-03-07",
  "input_dir": "./pdfs/",
  "output_dir": "./output_module_2/",
  "chunk_size": 500,
  "overlap": 50,
  "embedding_model": "text-embedding-3-small",
  "llm_model": "gpt-4o-mini",
  "vector_db_type": "faiss",
  "api_base": "https://openai.api.proxyapi.ru/v1",
  "ocr_enabled": true,
  "log_level": "INFO",
  "use_cache": true,
  "max_retries": 3,
  "retry_delay": 2.0
}
```

### Переменные окружения

Переменные окружения имеют приоритет над `config.json`:

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_API_BASE=https://openai.api.proxyapi.ru/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OCR_LANG=rus+eng
DEFAULT_CHUNK_SIZE=500
DEFAULT_OVERLAP=50
LOG_LEVEL=INFO
LANGUAGE=ru
```

---

## Запуск

### Запуск через GUI

```bash
python gui_app.py
```

### Запуск через CLI

```bash
# Базовая обработка
python squeezer.py --input document.pdf --output output/

# С чанкингом
python squeezer.py --input document.pdf --output output/ --enable-chunking

# С векторизацией
python squeezer.py --input document.pdf --output output/ --enable-chunking --enable-vectorization
```

### Запуск RAG Builder

```bash
python rag_builder.py
```

---

## Устранение проблем

### Проблема: Python не найден

**Решение:**
- Убедитесь, что Python установлен
- Добавьте Python в PATH
- Используйте `python3` вместо `python`

### Проблема: Ошибка при установке зависимостей

**Решение:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### Проблема: Tesseract не найден

**Решение:**
- Убедитесь, что Tesseract установлен
- Добавьте Tesseract в PATH
- Укажите путь к Tesseract в коде (если нужно)

### Проблема: Ошибка API ключа

**Решение:**
- Убедитесь, что файл `.env` создан
- Проверьте, что `OPENAI_API_KEY` указан в `.env`
- Убедитесь, что API ключ корректный и активен

### Проблема: GUI не запускается

**Решение:**
- Убедитесь, что установлен Tkinter
- Для Linux: `sudo apt-get install python3-tk`
- Для Windows: переустановите Python с включением Tcl/tk

### Проблема: Ошибка памяти при векторизации

**Решение:**
- Уменьшите размер чанка (`DEFAULT_CHUNK_SIZE`)
- Уменьшите количество файлов для обработки
- Увеличьте объём оперативной памяти

---

## Production развертывание

### Docker (опционально)

Создайте `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0

# Рабочая директория
WORKDIR /app

# Копирование файлов
COPY requirements.txt .
COPY . .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Создание директорий
RUN mkdir -p output logs pdfs rag_bases backups

# Запуск
CMD ["python", "gui_app.py"]
```

Создайте `docker-compose.yml`:

```yaml
version: '3.8'

services:
  squeezer:
    build: .
    volumes:
      - ./output:/app/output
      - ./logs:/app/logs
      - ./pdfs:/app/pdfs
      - ./rag_bases:/app/rag_bases
      - ./backups:/app/backups
    env_file:
      - .env
    ports:
      - "8000:8000"
```

Запуск:

```bash
docker-compose up -d
```

---

## Обновление

### Обновление до последней версии

```bash
# Создайте бэкап перед обновлением
python create_backup.py

# Обновите код
git pull origin main

# Обновите зависимости
pip install -r requirements.txt --upgrade

# Если нужно, восстановитесь из бэкапа
python restore_backup.py
```

---

## Дополнительные ресурсы

- [Руководство пользователя](USER_GUIDE.md)
- [Production документация](README_PRODUCTION.md)
- [Руководство по бэкапу](BACKUP_GUIDE.md)
- [Архитектура проекта](ARCHITECTURE.md)
- [API документация](docs/)

---

## Поддержка

Если у вас возникли проблемы:

1. Проверьте этот документ
2. Посмотрите [Устранение неполадок](USER_GUIDE.md#устранение-неполадок)
3. Создайте Issue на GitHub
4. Свяжитесь с автором: [Line_GV](https://t.me/Line_GV)

---

**Автор:** Line_GV  
**Версия:** 3.1.0  
**Дата последнего обновления:** 2026-03-07
