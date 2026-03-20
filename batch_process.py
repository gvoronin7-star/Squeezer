#!/usr/bin/env python3
"""
Пакетная обработка нескольких PDF файлов в векторную базу данных.

Создаёт единую векторную БД из всех PDF файлов в указанной директории.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.preprocessor import process_pdf
from src.vectorizer import process_vectorization


def setup_logging(log_level: str = "INFO"):
    """Настраивает логирование."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    file_handler = logging.FileHandler('logs/batch_process.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def batch_process(
    input_dir: str,
    output_dir: str,
    chunk_size: int = 500,
    overlap: int = 50,
    embedding_model: str = "text-embedding-3-small",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1",
    ocr_enabled: bool = True,
    enable_vectorization: bool = True,
    use_llm: bool = True,
    llm_model: str = "claude-3-5-sonnet-latest"
) -> dict:
    """
    Обрабатывает все PDF в директории и создаёт единую векторную БД.

    Args:
        input_dir: Директория с PDF файлами.
        output_dir: Выходная директория для результатов.
        chunk_size: Максимальный размер чанка.
        overlap: Перекрытие между чанками.
        embedding_model: Модель эмбеддингов.
        api_key: API ключ OpenAI.
        api_base: Базовый URL API.
        ocr_enabled: Включить OCR.
        enable_vectorization: Включить векторизацию.
        use_llm: Использовать LLM для обогащения метаданных.
        llm_model: Модель LLM для обогащения.

    Returns:
        Словарь с результатами обработки.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Находим все PDF файлы
    pdf_files = list(input_path.glob('*.pdf'))
    pdf_files.extend(list(input_path.glob('**/*.pdf')))  # Рекурсивный поиск

    # Убираем дубликаты
    pdf_files = list(set(pdf_files))

    if not pdf_files:
        logging.warning(f"PDF files not found in: {input_dir}")
        return {"success": False, "message": "PDF files not found"}

    logging.info(f"Найдено файлов: {len(pdf_files)}")
    print(f"\n{'='*60}")
    print(f"Package PDF processing")
    print(f"{'='*60}")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Files to process: {len(pdf_files)}")
    print(f"Chunk size: {chunk_size}")
    print(f"Overlap: {overlap}")
    print(f"Embedding model: {embedding_model}")
    print(f"Vectorization: {'Yes' if enable_vectorization else 'No'}")
    print(f"{'='*60}\n")

    all_chunks = []
    processed_files = []

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        logging.info(f"Processing file: {pdf_file.name}")

        try:
            result = process_pdf(
                str(pdf_file),
                str(output_path / "temp"),
                ocr_enabled=ocr_enabled,
                ocr_lang="rus+eng",
                enable_chunking=True,
                max_chunk_size=chunk_size,
                overlap=overlap,
                enable_vectorization=False,  # Сначала собираем чанки
                generate_demo=False,
                use_llm=use_llm,
                llm_model=llm_model
            )

            if 'chunks' in result:
                # Добавляем source в метаданные для разделения файлов
                for chunk in result['chunks']:
                    chunk['metadata']['source_file'] = pdf_file.name
                all_chunks.extend(result['chunks'])
                processed_files.append(pdf_file.name)
                print(f"  -> Sozdano chunkov: {len(result['chunks'])}")
            else:
                print(f"  -> Preduprezhdenie: chunki ne sozdany")

        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_file.name}: {e}")
            print(f"  -> Oshibka: {e}")

    print(f"\n{'='*60}")
    print(f"File processing complete")
    print(f"Successfully processed: {len(processed_files)}/{len(pdf_files)}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"{'='*60}\n")

    # Векторизация всех чанков вместе
    vectorization_result = None
    if enable_vectorization and all_chunks:
        if not api_key:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            logging.error("API key not provided. Vectorization impossible.")
            print("Error: API key not provided. Vectorization skipped.")
            print("Use --api-key or set OPENAI_API_KEY in .env")
        else:
            print("Starting vectorization...")
            logging.info(f"Vectorization of {len(all_chunks)} chunks")
            
            try:
                vectorization_result = process_vectorization(
                    all_chunks,
                    output_dir=str(output_path),
                    model_name=embedding_model,
                    api_key=api_key,
                    api_base=api_base
                )
                
                total_vectors = vectorization_result.get('vectorization', {}).get('total_vectors', 0)
                print(f"\n{'='*60}")
                print(f"Vector DB created!")
                print(f"Vectors: {total_vectors}")
                print(f"Dimension: {vectorization_result.get('vectorization', {}).get('embedding_dim', 0)}")
                print(f"DB path: {output_path}/vector_db/")
                print(f"{'='*60}\n")
                
            except Exception as e:
                logging.error(f"Error during vectorization: {e}")
                print(f"Vectorization error: {e}")

    # Сохранение списка обработанных файлов
    manifest = {
        "created_at": datetime.now().isoformat(),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "parameters": {
            "chunk_size": chunk_size,
            "overlap": overlap,
            "embedding_model": embedding_model,
            "ocr_enabled": ocr_enabled
        },
        "processed_files": processed_files,
        "total_chunks": len(all_chunks),
        "total_vectors": vectorization_result.get('vectorization', {}).get('total_vectors', 0) if vectorization_result else 0
    }

    import json
    manifest_path = output_path / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Манифест сохранён: {manifest_path}")

    return {
        "success": True,
        "processed_files": len(processed_files),
        "total_files": len(pdf_files),
        "total_chunks": len(all_chunks),
        "vectorization": vectorization_result
    }


def main():
    parser = argparse.ArgumentParser(
        description="Пакетная обработка PDF файлов в векторную БД",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python batch_process.py --input pdfs/ --output my_vector_db/
  python batch_process.py --input pdfs/ --output db/ --chunk-size 300 --overlap 50
  python batch_process.py --input pdfs/ --output db/ --api-key sk-...
  python batch_process.py --input pdfs/ --output db/ --model text-embedding-3-large
        """
    )
    
    parser.add_argument("--input", "-i", required=True, 
                        help="Директория с PDF файлами")
    parser.add_argument("--output", "-o", required=True, 
                        help="Выходная директория для результатов")
    
    # Параметры чанкинга
    parser.add_argument("--chunk-size", type=int, default=500, 
                        help="Максимальный размер чанка (по умолчанию: 500)")
    parser.add_argument("--overlap", type=int, default=50, 
                        help="Перекрытие между чанками (по умолчанию: 50)")
    
    # Параметры векторизации
    parser.add_argument("--model", "--embedding-model", dest="embedding_model", 
                        default="text-embedding-3-small",
                        help="Модель эмбеддингов (по умолчанию: text-embedding-3-small)")
    parser.add_argument("--api-key", type=str, 
                        help="API ключ OpenAI (если не задан в .env)")
    parser.add_argument("--api-base", type=str, 
                        default="https://openai.api.proxyapi.ru/v1",
                        help="Базовый URL API (по умолчанию: https://openai.api.proxyapi.ru/v1)")
    
    # Дополнительные параметры
    parser.add_argument("--no-ocr", action="store_true", 
                        help="Отключить OCR для сканированных PDF")
    parser.add_argument("--no-vectorization", action="store_true", 
                        help="Не выполнять векторизацию (только чанкинг)")
    parser.add_argument("--no-llm", action="store_true", 
                        help="Отключить LLM-обогащение метаданных")
    parser.add_argument("--llm-model", type=str, 
                        default="gpt-4o-mini",
                        help="Модель LLM (по умолчанию: gpt-4o-mini)")
    parser.add_argument("--log-level", default="INFO",
                        help="Уровень логирования (по умолчанию: INFO)")

    args = parser.parse_args()

    setup_logging(args.log_level)

    batch_process(
        input_dir=args.input,
        output_dir=args.output,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        embedding_model=args.embedding_model,
        api_key=args.api_key,
        api_base=args.api_base,
        ocr_enabled=not args.no_ocr,
        enable_vectorization=not args.no_vectorization,
        use_llm=not args.no_llm,
        llm_model=args.llm_model
    )


if __name__ == "__main__":
    main()
