import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Добавляем src в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from src.preprocessor import process_pdf


def parse_args():
    parser = argparse.ArgumentParser(description="Соковыжималка: подготовка данных для RAG")
    parser.add_argument("--input", type=str, required=True, help="Путь к PDF файлу или директории")
    parser.add_argument("--output", type=str, required=True, help="Путь к выходной директории")
    parser.add_argument("--config", type=str, default="config.json", help="Путь к конфигурационному файлу")
    
    # Параметры чанкинга (этапы 5-6)
    parser.add_argument("--enable-chunking", action="store_true", help="Включить чанкинг (этапы 5-6)")
    parser.add_argument("--chunk-size", type=int, default=500, help="Максимальный размер чанка (по умолчанию: 500)")
    parser.add_argument("--overlap", type=int, default=50, help="Перекрытие между чанками (по умолчанию: 50)")
    
    # Параметры векторизации (этапы 7-8)
    parser.add_argument("--enable-vectorization", action="store_true", help="Включить векторизацию (этапы 7-8)")
    parser.add_argument("--embedding-model", type=str, default="text-embedding-3-small", 
                        help="Модель эмбеддингов (по умолчанию: text-embedding-3-small)")
    parser.add_argument("--api-key", type=str, help="API ключ OpenAI (если не задан в .env)")
    parser.add_argument("--api-base", type=str, help="Базовый URL API (по умолчанию: https://openai.api.proxyapi.ru/v1)")
    
    # OCR
    parser.add_argument("--ocr", action="store_true", help="Включить OCR для сканированных PDF")
    
    # LLM
    parser.add_argument("--no-llm", action="store_true", help="Отключить LLM-обогащение метаданных")
    parser.add_argument("--llm-model", type=str, default="gpt-4o-mini",
                        help="Модель LLM (по умолчанию: gpt-4o-mini)")
    
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """Загружает конфигурацию из JSON файла."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def setup_logging(log_level: str = "INFO"):
    """Настраивает логирование."""
    # Убедимся, что директория для логов существует
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Очищаем существующие обработчики
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Устанавливаем уровень логирования
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Формат логов
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Файловый обработчик с кодировкой UTF-8
    file_handler = logging.FileHandler('logs/squeezer.log', encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def main():
    args = parse_args()
    
    # Загружаем конфигурацию
    config = load_config(args.config)
    
    # Настраиваем логирование
    setup_logging(config.get("log_level", "INFO"))
    
    # Определяем API base (CLI > config > default)
    api_base = args.api_base or config.get("api_base", "https://openai.api.proxyapi.ru/v1")
    
    logging.info("=" * 60)
    logging.info("Соковыжималка: запуск программы")
    logging.info(f"Входная директория: {args.input}")
    logging.info(f"Выходная директория: {args.output}")
    logging.info(f"Конфигурационный файл: {args.config}")
    logging.info(f"Чанкинг: {'Включён' if args.enable_chunking else 'Отключён'}")
    if args.enable_chunking:
        logging.info(f"  Размер чанка: {args.chunk_size}, Перекрытие: {args.overlap}")
    logging.info(f"Векторизация: {'Включена' if args.enable_vectorization else 'Отключена'}")
    if args.enable_vectorization:
        logging.info(f"  Модель: {args.embedding_model}")
    logging.info("=" * 60)
    
    # Создаём выходную директорию, если она не существует
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"Выходная директория подготовлена: {output_dir}")
    
    # Модуль 1: Базовый каркас и конфигурация - успешно инициализирован
    logging.info("Модуль 1: Базовый каркас и конфигурация - успешно инициализирован")

    # Модуль 2: Извлечение и предобработка текста
    logging.info("Модуль 2: Извлечение и предобработка текста - запуск")

    # Находим все PDF файлы во входной директории
    input_path = Path(args.input)
    if input_path.is_file() and input_path.suffix.lower() == '.pdf':
        pdf_files = [input_path]
    else:
        pdf_files = list(input_path.glob('*.pdf'))

    if not pdf_files:
        logging.warning(f"PDF файлы не найдены в директории: {args.input}")
        return

    logging.info(f"Найдено PDF файлов: {len(pdf_files)}")

    # Обрабатываем каждый файл
    results = []
    for pdf_file in pdf_files:
        try:
            logging.info(f"Обработка файла: {pdf_file.name}")
            result = process_pdf(
                str(pdf_file),
                args.output,
                ocr_enabled=args.ocr,
                ocr_lang="rus+eng",
                enable_chunking=args.enable_chunking,
                max_chunk_size=args.chunk_size,
                overlap=args.overlap,
                enable_vectorization=args.enable_vectorization,
                embedding_model=args.embedding_model,
                api_key=args.api_key,
                api_base=api_base,
                use_llm=not args.no_llm,
                llm_model=args.llm_model
            )
            results.append(result)
            logging.info(f"Файл обработан успешно: {pdf_file.name}")
        except Exception as e:
            logging.error(f"Ошибка при обработке файла {pdf_file.name}: {e}")

    logging.info(f"Модуль 2: Извлечение и предобработка текста - завершено. Обработано файлов: {len(results)}")
    logging.info("=" * 60)
    logging.info("Соковыжималка: работа завершена")


if __name__ == "__main__":
    main()
