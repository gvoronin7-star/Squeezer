# Руководство по развертыванию (Deployment Guide)

**Версия:** 3.3.0
**Статус:** Production Ready  
**Дата последнего обновления:** 2026-03-20

---

## Обзор

Это руководство описывает процесс развертывания системы "Соковыжималка" (Squeezer) в production окружении.

---

## Предварительные требования

### Требования к системе

- **Python:** 3.8+
- **RAM:** Минимум 4 ГБ (рекомендуется 8 ГБ+)
- **Место на диске:** Минимум 2 ГБ
- **CPU:** Любой современный процессор
- **OS:** Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)

### Требования к сети

- Доступ к OpenAI API (или прокси)
- Стабильное интернет-соединение (для векторизации)

---

## Варианты развертывания

### Вариант 1: Локальное развертывание (Stand-alone)

Подходит для:
- Локального использования на одном компьютере
- Малых команд
- Тестирования и разработки

**Плюсы:**
- Простота настройки
- Нет дополнительных затрат на инфраструктуру
- Полный контроль над данными

**Минусы:**
- Ограниченная масштабируемость
- Зависимость от одного компьютера

### Вариант 2: Docker контейнеризация

Подходит для:
- Развертывания на серверах
- Консистентного окружения
- Легкой миграции между системами

**Плюсы:**
- Изолированное окружение
- Легкое развертывание
- Консистентность между окружениями

**Минусы:**
- Требует знания Docker
- Дополнительный уровень абстракции

### Вариант 3: Облачное развертывание (AWS/GCP/Azure)

Подходит для:
- Масштабируемых решений
- Команд с распределённой работой
- Интеграции с другими облачными сервисами

**Плюсы:**
- Масштабируемость
- Высокая доступность
- Интеграция с другими сервисами

**Минусы:**
- Дополнительные затраты
- Сложность настройки

---

## Развертывание: Вариант 1 (Локальное)

### Шаг 1: Установка

Следуйте инструкциям в [SETUP.md](../SETUP.md).

### Шаг 2: Конфигурация

1. **Настройте переменные окружения:**

```bash
cp .env.example .env
# Отредактируйте .env с вашими настройками
```

2. **Настройте config.json:**

```json
{
  "version": "3.3.0",
  "input_dir": "./pdfs/",
  "output_dir": "./output/",
  "chunk_size": 500,
  "overlap": 50,
  "embedding_model": "text-embedding-3-small",
  "llm_model": "gpt-4o-mini",
  "vector_db_type": "faiss",
  "api_base": "https://openai.api.proxyapi.ru/v1",
  "ocr_enabled": true,
  "log_level": "INFO"
}
```

### Шаг 3: Тестирование

```bash
# Тест GUI
python gui_app.py

# Тест CLI
python squeezer.py --help

# Тест RAG Builder
python rag_builder.py
```

### Шаг 4: Создание бэкапа

```bash
python create_backup.py
```

---

## Развертывание: Вариант 2 (Docker)

### Шаг 1: Создание Dockerfile

Создайте файл `Dockerfile` в корне проекта:

```dockerfile
FROM python:3.9-slim

# Метаданные
LABEL maintainer="Line_GV <https://t.me/Line_GV>"
LABEL version="3.3.0"
LABEL description="Squeezer - RAG System for PDF Processing"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание необходимых директорий
RUN mkdir -p /app/output /app/logs /app/pdfs /app/rag_bases /app/backups /app/temp_uploads /app/temp_rag_processing

# Настройка прав доступа
RUN chmod -R 755 /app

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Порт (если нужен веб-интерфейс)
EXPOSE 8000

# Команда запуска
CMD ["python", "gui_app.py"]
```

### Шаг 2: Создание docker-compose.yml

Создайте файл `docker-compose.yml`:

```yaml
version: '3.8'

services:
  squeezer:
    build: .
    container_name: squeezer-app
    restart: unless-stopped
    volumes:
      # Монтирование директорий для данных
      - ./pdfs:/app/pdfs
      - ./output:/app/output
      - ./logs:/app/logs
      - ./rag_bases:/app/rag_bases
      - ./backups:/app/backups
      # Монтирование конфигурации
      - ./.env:/app/.env
      - ./config.json:/app/config.json
    environment:
      - PYTHONUNBUFFERED=1
      - LANG=C.UTF-8
      - LC_ALL=C.UTF-8
    # Если нужен доступ к GUI через X11 (Linux)
    # environment:
    #   - DISPLAY=${DISPLAY}
    # volumes:
    #   - /tmp/.X11-unix:/tmp/.X11-unix
    ports:
      - "8000:8000"  # Для веб-интерфейса (если будет)
    networks:
      - squeezer-network

networks:
  squeezer-network:
    driver: bridge
```

### Шаг 3: Сборка и запуск

```bash
# Сборка образа
docker-compose build

# Запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### Шаг 4: Взаимодействие с контейнером

```bash
# Вход в контейнер
docker-compose exec squeezer bash

# Запуск команд внутри контейнера
docker-compose exec squeezer python squeezer.py --help
docker-compose exec squeezer python rag_builder.py

# Создание бэкапа
docker-compose exec squeezer python utils/create_backup.py
```

---

## Развертывание: Вариант 3 (Облачное - AWS)

### Шаг 1: Подготовка AWS аккаунта

1. Создайте AWS аккаунт
2. Настройте AWS CLI
3. Создайте IAM пользователя с правами S3, EC2, Lambda (если нужно)

### Шаг 2: Создание EC2 инстанса

```bash
# Запуск EC2 инстанса (Ubuntu 20.04)
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxx \
  --subnet-id subnet-xxxxxxxx \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=Squeezer}]"
```

### Шаг 3: Настройка EC2

```bash
# Подключение к EC2
ssh -i your-key-pair.pem ubuntu@your-instance-ip

# Обновление системы
sudo apt-get update && sudo apt-get upgrade -y

# Установка Docker
sudo apt-get install -y docker.io docker-compose

# Клонирование репозитория
git clone https://github.com/gvoronin7-star/Squeezer.git
cd Squeezer

# Настройка .env
cp .env.example .env
nano .env  # Редактирование

# Запуск через Docker Compose
docker-compose up -d
```

### Шаг 4: Настройка S3 для бэкапов (опционально)

```bash
# Создание S3 bucket
aws s3 mb s3://squeezer-backups

# Настройка автоматического бэкапа в S3
# (добавьте в cron или используйте AWS Lambda)
```

---

## Мониторинг и логирование

### Логирование

Логи хранятся в директории `logs/`:

- `squeezer.log` — основной лог
- `squeezer_debug.log` — отладочный лог
- `rag_builder.log` — лог RAG Builder

### Настройка ротации логов

Создайте файл `logrotate.conf`:

```
/path/to/squeezer/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 squeezer squeezer
}
```

### Мониторинг ресурсов

Используйте инструменты мониторинга:

- **htop** — для Linux
- **Resource Monitor** — для Windows
- **Activity Monitor** — для macOS
- **Prometheus + Grafana** — для продвинутого мониторинга

---

## Бэкап и восстановление

### Автоматический бэкап

Добавьте в cron (Linux):

```bash
# Ежедневный бэкап в 2:00 ночи
0 2 * * * cd /path/to/squeezer && /usr/bin/python3 utils/create_backup.py >> /var/log/squeezer_backup.log 2>&1
```

### Восстановление

```bash
python utils/restore_backup.py
```

---

## Обновление

### Обновление до новой версии

```bash
# 1. Создайте бэкап
python utils/create_backup.py

# 2. Получите обновления
git pull origin main

# 3. Обновите зависимости
pip install -r requirements.txt --upgrade

# 4. Перезапустите сервис
# Для Docker:
docker-compose down
docker-compose pull
docker-compose up -d

# 5. Проверьте работу
python squeezer.py --help
```

---

## Безопасность в Production

### Checklist

- [ ] Используйте сильные пароли и API ключи
- [ ] Настройте файрвол
- [ ] Ограничьте доступ по IP (если возможно)
- [ ] Используйте HTTPS (если есть веб-интерфейс)
- [ ] Регулярно обновляйте систему и зависимости
- [ ] Настройте мониторинг и оповещения
- [ ] Создайте план аварийного восстановления
- [ ] Регулярно создавайте бэкапы

Подробнее: [SECURITY.md](../SECURITY.md)

---

## Troubleshooting

### Проблема: Контейнер не запускается

**Решение:**

```bash
# Проверьте логи
docker-compose logs

# Проверьте статус
docker-compose ps

# Пересоберите образ
docker-compose build --no-cache
```

### Проблема: Нет доступа к GUI в Docker

**Решение:**

Для Linux используйте X11 forwarding:

```yaml
# В docker-compose.yml
services:
  squeezer:
    environment:
      - DISPLAY=${DISPLAY}
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
```

Для Windows/macOS используйте VNC или веб-интерфейс.

### Проблема: Ошибка памяти

**Решение:**

- Увеличьте RAM контейнера/инстанса
- Уменьшите размер чанков
- Обрабатывайте файлы пакетами

---

## Поддержка

Если у вас возникли проблемы с развертыванием:

1. Проверьте этот документ
2. Посмотрите [SECURITY.md](../SECURITY.md)
3. Проверьте [SETUP.md](../SETUP.md)
4. Создайте Issue на GitHub
5. Свяжитесь с автором: [Line_GV](https://t.me/Line_GV)

---

## Дополнительные ресурсы

- [Docker Documentation](https://docs.docker.com/)
- [AWS Documentation](https://docs.aws.amazon.com/)
- [Python Deployment Best Practices](https://docs.python-guide.org/deploying/)

---

**Автор:** Line_GV  
**Версия:** 3.3.0
**Дата последнего обновления:** 2026-03-20
