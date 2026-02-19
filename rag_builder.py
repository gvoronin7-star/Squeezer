"""
Приложение для создания RAG-баз данных из PDF-файлов.

Интегрирует UI выбора файлов с модулями обработки и генерации инструкций.
"""

import sys
import logging
import shutil
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.rag_builder_ui import RAGBuilderUI
from src.preprocessor import process_pdf
from src.vectorizer import process_vectorization
from src.rag_instructions import generate_rag_package

# Настройка логирования
def setup_logging():
    """Настраивает логирование с поддержкой UTF-8."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    file_handler = logging.FileHandler('logs/rag_builder.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

setup_logging()
logger = logging.getLogger(__name__)


class RAGBuilderApp:
    """
    Основное приложение для создания RAG-баз данных.
    """

    def __init__(self, root, language='ru'):
        """
        Инициализация приложения.

        Args:
            root: Корневое окно Tkinter.
            language: Язык интерфейса ('ru' или 'en').
        """
        self.root = root
        self.language = language

        # Создаём UI
        self.ui = RAGBuilderUI(
            root,
            language=language,
            on_rag_created=self._on_rag_create_start
        )

        logger.info("Приложение RAG Builder инициализировано")

    def _on_rag_create_start(self, config: dict):
        """
        Начинает процесс создания RAG-базы.

        Args:
            config: Конфигурация RAG-базы.
        """
        logger.info(f"Начало создания RAG-базы: {config['rag_name']}")
        logger.info(f"Файлов для обработки: {len(config['files'])}")

        try:
            # Создаём временную директорию для обработки
            temp_dir = Path("temp_rag_processing")
            temp_dir.mkdir(exist_ok=True)

            # Обрабатываем все PDF файлы
            all_chunks = []
            total_pages = 0

            for i, file_info in enumerate(config['files'], 1):
                logger.info(f"Обработка файла {i}/{len(config['files'])}: {file_info['original_name']}")
                self.ui._log(f"Обработка файла {i}/{len(config['files'])}: {file_info['original_name']}")

                try:
                    # Обрабатываем PDF
                    result = process_pdf(
                        file_info['temp_path'],
                        str(temp_dir / f"output_{i}"),
                        ocr_enabled=False,
                        ocr_lang='rus+eng',
                        enable_chunking=True,
                        max_chunk_size=500,
                        overlap=50,
                        generate_demo=False
                    )

                    # Добавляем чанки
                    if 'chunks' in result:
                        all_chunks.extend(result['chunks'])
                        total_pages += result['stats'].get('extraction', {}).get('total_pages', 0)

                    logger.info(f"Файл обработан: {file_info['original_name']}")

                except Exception as e:
                    logger.error(f"Ошибка при обработке файла {file_info['original_name']}: {e}")
                    self.ui._log(f"ОШИБКА при обработке {file_info['original_name']}: {e}")

            logger.info(f"Всего обработано файлов: {len(config['files'])}")
            logger.info(f"Всего чанков: {len(all_chunks)}")
            self.ui._log(f"Всего чанков: {len(all_chunks)}")

            if not all_chunks:
                raise Exception("Не удалось создать чанки из файлов")

            # Векторизация
            logger.info("Начало векторизации...")
            self.ui._log("Векторизация чанков...")

            vectorization_result = process_vectorization(
                all_chunks,
                output_dir=str(temp_dir),
                model_name="text-embedding-3-small",
                db_type="faiss"
            )

            logger.info("Векторизация завершена")
            self.ui._log("Векторизация завершена")

            # Создаём RAG-пакет
            logger.info("Создание RAG-пакета...")
            self.ui._log("Создание RAG-пакета...")

            rag_base_dir = Path("rag_bases")
            rag_base_dir.mkdir(exist_ok=True)

            index_path = Path(temp_dir / "vector_db" / "index.faiss")
            dataset_path = Path(temp_dir / "vector_db" / "dataset.json")
            metadata_path = Path(temp_dir / "vector_db" / "metadata.json")

            # Используем temp_path для исходных файлов
            source_files = [Path(f['temp_path']) for f in config['files']]

            rag_package = generate_rag_package(
                config['rag_name'],
                index_path,
                dataset_path,
                metadata_path,
                source_files,
                rag_base_dir
            )

            logger.info(f"RAG-пакет создан: {rag_package['rag_dir']}")
            self.ui._log(f"RAG-база создана: {rag_package['rag_dir']}")

            # Очищаем временную директорию
            shutil.rmtree(temp_dir, ignore_errors=True)

            # Завершаем обработку
            rag_info = {
                'rag_dir': rag_package['rag_dir'],
                'rag_name': config['rag_name'],
                'total_files': config['stats']['total_files'],
                'total_pages': total_pages,
                'total_chunks': len(all_chunks)
            }

            self.ui.complete_processing(rag_info)

        except Exception as e:
            logger.error(f"Ошибка при создании RAG-базы: {e}")
            self.ui._log(f"ОШИБКА: {str(e)}")
            self.ui.progress.stop()
            self.ui.progress_label.config(text=self.ui.translations['processing_failed'])
            self.ui.is_processing = False
            self.ui.process_button.config(state='normal')
            self.ui.load_button.config(state='normal')
            self.ui._update_ui()

    def run(self):
        """Запускает приложение."""
        self.root.mainloop()


def main():
    """Главная функция для запуска приложения."""
    root = tk.Tk()

    # Настройка стиля
    style = ttk.Style()
    style.theme_use('clam')

    # Создаём приложение
    app = RAGBuilderApp(root, language='ru')

    # Обработка закрытия окна
    def on_closing():
        app.ui.loader.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Запускаем
    app.run()


if __name__ == "__main__":
    main()
