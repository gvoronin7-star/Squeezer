# Индекс документации "Соковыжималка"

**Версия:** 2.4.0 (Production Ready)
**Автор:** [Line_GV](https://t.me/Line_GV)
**Лицензия:** MIT

---

## 📚 Основная документация

| Файл | Описание |
|------|----------|
| [README.md](README.md) | Руководство пользователя |
| [README_PRODUCTION.md](README_PRODUCTION.md) | Production-ready документация |
| [USER_GUIDE.md](USER_GUIDE.md) | Полное руководство пользователя |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Архитектура проекта |
| [CHANGELOG.md](CHANGELOG.md) | История изменений |
| [AUTHORS](AUTHORS) | Информация об авторе |
| [LICENSE](LICENSE) | Лицензия MIT |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Как внести вклад в проект |

## 📖 Руководства

| Файл | Описание |
|------|----------|
| [RAG_BUILDER_GUIDE.md](RAG_BUILDER_GUIDE.md) | Руководство по созданию RAG-баз данных |
| [BACKUP_GUIDE.md](BACKUP_GUIDE.md) | Руководство по бэкапу и восстановлению |

## 🔧 API документация

| Файл | Описание |
|------|----------|
| [docs/MODULE_2.1_API.md](docs/MODULE_2.1_API.md) | API Модуля 2.1 (GUI) |
| [docs/MODULE_3_API.md](docs/MODULE_3_API.md) | API Модуля 3 (Чанкинг) |
| [docs/MODULE_4_API.md](docs/MODULE_4_API.md) | API Модуля 4 (Векторизация) |
| [docs/MODULE_5_API.md](docs/MODULE_5_API.md) | API Модуля 5 (RAG Builder) |

## ⚙️ Конфигурация

| Файл | Описание |
|------|----------|
| [.env.example](.env.example) | Пример конфигурации переменных окружения |
| [.gitignore](.gitignore) | Исключаемые файлы для Git |
| [requirements.txt](requirements.txt) | Зависимости Python |
| [config.json](config.json) | Конфигурация приложения |
| [VERSION](VERSION) | Версия системы |

## 🚀 Быстрый поиск

### Для начинающих
1. [Установка и запуск](USER_GUIDE.md#установка)
2. [Быстрый старт](USER_GUIDE.md#быстрый-старт)
3. [Этапы обработки](USER_GUIDE.md#этапы-обработки)
4. [Настройка окружения](README_PRODUCTION.md#установка)

### Для создания RAG-баз
1. [Руководство по RAG Builder](RAG_BUILDER_GUIDE.md)
2. [Модуль 5 API](docs/MODULE_5_API.md)

### Для бэкапа и восстановления
1. [Руководство по бэкапу](BACKUP_GUIDE.md)

### Для разработчиков
1. [Production документация](README_PRODUCTION.md)
2. [Архитектура проекта](ARCHITECTURE.md)
3. [Модуль 2.1 API](docs/MODULE_2.1_API.md)
4. [Модуль 3 API](docs/MODULE_3_API.md)
5. [Модуль 4 API](docs/MODULE_4_API.md)
6. [Модуль 5 API](docs/MODULE_5_API.md)
7. [Как внести вклад](CONTRIBUTING.md)

### Для пользователей
1. [Использование GUI](USER_GUIDE.md#графический-интерфейс-gui)
2. [Использование CLI](USER_GUIDE.md#командная-строка-cli)
3. [Выходные файлы](USER_GUIDE.md#выходные-файлы)

### Для DevOps/инженеров
1. [Production документация](README_PRODUCTION.md)
2. [Конфигурация окружения](.env.example)
3. [Зависимости](requirements.txt)
4. [Бэкап и восстановление](BACKUP_GUIDE.md)

## 📂 Структура проекта

```
squeezer/
├── README.md                    # Руководство пользователя
├── README_PRODUCTION.md         # Production документация
├── USER_GUIDE.md                # Полное руководство пользователя
├── ARCHITECTURE.md              # Архитектура проекта
├── CHANGELOG.md                 # История изменений
├── AUTHORS                      # Информация об авторе
├── LICENSE                      # Лицензия MIT
├── CONTRIBUTING.md              # Как внести вклад
├── DOCS_INDEX.md                # Индекс документации (этот файл)
├── BACKUP_GUIDE.md              # Руководство по бэкапу и восстановлению
├── RAG_BUILDER_GUIDE.md         # Руководство по созданию RAG-баз
├── VERSION                      # Версия системы
├── requirements.txt             # Зависимости
├── config.json                  # Конфигурация
├── .gitignore                   # Игнорируемые файлы
├── .env.example                 # Пример переменных окружения
│
├── squeezer.py                  # CLI приложение
├── gui_app.py                   # GUI приложение
├── rag_builder.py               # RAG Builder приложение
├── create_backup.py             # Скрипт создания бэкапа
├── restore_backup.py            # Скрипт восстановления из бэкапа
│
├── src/                         # Исходный код
│   ├── __init__.py             # Инициализация пакета
│   ├── preprocessor.py         # Модуль 2: Предобработка текста
│   ├── chunker.py              # Модуль 3: Чанкинг и метаданные
│   ├── vectorizer.py           # Модуль 4: Векторизация и БД
│   ├── rag_instructions.py     # Модуль 5: Инструкции RAG-баз
│   └── ui/                     # Модуль 2.1: GUI
│       ├── pdf_loader.py       # UI для загрузки PDF
│       └── rag_builder_ui.py   # UI для RAG Builder
│
├── docs/                        # API документация
│   ├── MODULE_2.1_API.md       # API Модуля 2.1
│   ├── MODULE_3_API.md         # API Модуля 3
│   ├── MODULE_4_API.md         # API Модуля 4
│   └── MODULE_5_API.md         # API Модуля 5
│
├── pdfs/                        # PDF файлы для тестирования
│   └── .gitkeep
│
├── output_module_2/             # Выходные данные Модуля 2
│   └── .gitkeep
│
├── output_module_3/             # Выходные данные Модуля 3
│   └── .gitkeep
│
├── output_module_4/             # Выходные данные Модуля 4
│   └── .gitkeep
│
├── output/                      # Выходные данные (векторная БД)
│   └── vector_db/              # Индекс FAISS и датасет
│       └── .gitkeep
│
├── rag_bases/                   # Готовые RAG-базы
│   └── .gitkeep
│
├── backups/                     # Бэкапы системы
│   └── .gitkeep
│
├── logs/                        # Логи
│   └── .gitkeep
│
├── temp_uploads/                # Временные файлы
│   └── .gitkeep
│
└── temp_rag_processing/         # Временные файлы RAG
    └── .gitkeep
```

## 📞 Контакты

**Автор:** Line_GV  
**Telegram:** [@Line_GV](https://t.me/Line_GV)
**GitHub:** [https://github.com/gvoronin7-star/Squeezer](https://github.com/gvoronin7-star/Squeezer)

## 📜 Лицензия

Проект лицензирован под MIT License — см. файл [LICENSE](LICENSE)

Проект разработан для образовательных целей в рамках обучения Prompt Engineering 3.0 от Zerocoder.

## 📊 Статус документации

| Раздел | Статус | Последнее обновление |
|--------|--------|---------------------|
| README.md | ✅ Актуально | 2026-02-18 |
| README_PRODUCTION.md | ✅ Актуально | 2026-02-18 |
| USER_GUIDE.md | ✅ Актуально | 2026-02-18 |
| ARCHITECTURE.md | ✅ Актуально | 2026-02-18 |
| CHANGELOG.md | ✅ Актуально | 2026-02-18 |
| BACKUP_GUIDE.md | ✅ Актуально | 2026-02-18 |
| RAG_BUILDER_GUIDE.md | ✅ Актуально | 2026-02-18 |
| CONTRIBUTING.md | ✅ Актуально | 2026-02-18 |
| LICENSE | ✅ Актуально | 2026-02-18 |
| MODULE_2.1_API.md | ✅ Актуально | 2026-02-18 |
| MODULE_3_API.md | ✅ Актуально | 2026-02-18 |
| MODULE_4_API.md | ✅ Актуально | 2026-02-18 |
| MODULE_5_API.md | ✅ Актуально | 2026-02-18 |

## 🎯 Roadmap документации

### Планируется:

- [ ] Добавление видео-туториалов
- [ ] Примеры интеграции с различными LLM
- [ ] Performance tuning guide
- [ ] Security best practices
- [ ] Deployment guide для различных платформ (Docker, Kubernetes, AWS, GCP)

---

**Автор:** Line_GV  
**Версия документации:** 2.4.0  
**Дата последнего обновления:** 2026-02-18  
**Статус:** Production Ready
