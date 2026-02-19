"""
Графическое приложение "Соковыжималка" для обработки PDF файлов.

Интегрирует UI загрузки PDF с модулем предобработки текста.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.pdf_loader import PDFLoaderUI
from src.preprocessor import process_pdf

# Настройка логирования
def setup_logging():
    """Настраивает логирование с поддержкой UTF-8."""
    # Убедимся, что директория для логов существует
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Очищаем существующие обработчики
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Устанавливаем уровень логирования
    root_logger.setLevel(logging.INFO)

    # Формат логов
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Файловый обработчик с кодировкой UTF-8
    file_handler = logging.FileHandler('logs/gui_app.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

setup_logging()
logger = logging.getLogger(__name__)


class SqueezerApp:
    """
    Основное приложение "Соковыжималка".
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
        self.current_file_path = None
        self.processing_result = None

        # Создаём UI
        self.ui = PDFLoaderUI(
            root,
            language=language,
            on_file_loaded=self._on_file_loaded,
            on_processing_complete=self._on_processing_complete
        )

        logger.info("Приложение инициализировано")

    def _on_file_loaded(self, file_path: Path):
        """
        Callback при загрузке файла.

        Args:
            file_path: Путь к загруженному файлу.
        """
        self.current_file_path = file_path
        logger.info(f"Файл загружен через UI: {file_path}")

    def _on_processing_complete(self, file_info: dict):
        """
        Callback при завершении обработки.

        Args:
            file_info: Информация о файле.
        """
        logger.info(f"Обработка завершена: {file_info}")

        # Обновляем UI с результатами
        if self.processing_result:
            stats = self.processing_result.get('stats', {})

            result_message = f"""
{self.ui.translations['processing_complete']}

{self.ui.translations['file_name']}: {file_info.get('name', '')}
{self.ui.translations['file_pages']}: {file_info.get('pages', 0)}

{self.ui.translations['file_info']}:
  {self.ui.translations['file_pages']}: {stats.get('structuring', {}).get('headings', 0)} заголовков
  Абзацев: {stats.get('structuring', {}).get('paragraphs', 0)}
  Списков: {stats.get('structuring', {}).get('lists', 0)}
"""

            # Добавляем информацию о чанкинге, если он был выполнен
            if 'chunks' in self.processing_result:
                chunks = self.processing_result.get('chunks', [])
                result_message += f"""
Этап 5-6: Чанкинг и метаданные
  Всего чанков: {len(chunks)}
  Средняя длина: {sum(c['metadata']['char_count'] for c in chunks) / len(chunks):.2f} символов
  Мин/Макс длина: {min(c['metadata']['char_count'] for c in chunks)}/{max(c['metadata']['char_count'] for c in chunks)}

Отчёт по чанкингу: output_module_3/chunking_report.txt
"""

                # Добавляем информацию о демонстрационном файле
                if 'chunking_demo_path' in self.processing_result:
                    result_message += f"""
Демонстрация чанкинга: output_module_3/content_demonstrator.txt
"""

            # Добавляем информацию о векторизации, если она была выполнена
            if 'vectorization' in self.processing_result:
                vectorization = self.processing_result.get('vectorization', {})
                vec_stats = vectorization.get('validation', {}).get('stats', {})
                vec_result = vectorization.get('vectorization', {})

                result_message += f"""
Этап 7-8: Векторизация и векторная БД
  Проверено чанков: {vec_stats.get('total_chunks', 0)}
  Пустых чанков: {vec_stats.get('empty_chunks', 0)}
  Средняя длина: {vec_stats.get('avg_char_count', 0):.2f} символов

  Модель эмбеддингов: {vec_result.get('embedding_dim', 0)}D ({vec_result.get('total_vectors', 0)} векторов)
  Тип БД: FAISS
  Путь к индексу: output/vector_db/index.faiss
  Путь к датасету: output/vector_db/dataset.json

Отчёт по векторизации: output_module_4/vectorization_report.txt
"""

            result_message += f"""
Результаты сохранены в: output_module_2/
"""

            from tkinter import messagebox
            messagebox.showinfo(
                self.ui.translations['success_title'],
                result_message.strip()
            )

    def process_pdf_file(
        self,
        file_path: Path,
        output_dir: str = './output_module_2/',
        enable_vectorization: bool = True,
        embedding_model: str = "text-embedding-3-small",
        vector_db_type: str = "faiss",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1"
    ) -> dict:
        """
        Обрабатывает PDF файл.

        Args:
            file_path: Путь к PDF файлу.
            output_dir: Директория для сохранения результатов.
            enable_vectorization: Включить этапы 7-8 (векторизация и БД).
            embedding_model: Модель эмбеддингов.
            vector_db_type: Тип векторной БД.
            api_key: API ключ OpenAI.
            api_base: Базовый URL API.

        Returns:
            Результаты обработки.
        """
        logger.info(f"Начало обработки файла: {file_path}")

        try:
            result = process_pdf(
                str(file_path),
                output_dir,
                ocr_enabled=False,
                ocr_lang='rus+eng',
                enable_chunking=True,      # Включаем этапы 5-6 (чанкинг)
                max_chunk_size=500,        # Максимальный размер чанка
                overlap=50,                # Перекрытие между чанками
                enable_vectorization=enable_vectorization,  # Включаем этапы 7-8
                embedding_model=embedding_model,
                vector_db_type=vector_db_type,
                api_key=api_key,
                api_base=api_base
            )

            self.processing_result = result
            return result

        except Exception as e:
            logger.error(f"Ошибка при обработке файла: {e}")
            raise

    def run(self):
        """Запускает приложение."""
        # Заменяем симуляцию обработки на реальную
        original_simulate = self.ui._simulate_processing

        def real_processing():
            try:
                if not self.current_file_path:
                    raise Exception("Файл не загружен")

                # Обрабатываем PDF
                result = self.process_pdf_file(self.current_file_path)

                # Останавливаем прогресс бар
                self.ui.progress.stop()
                self.ui.progress_label.config(text=self.ui.translations['processing_complete'])
                self.ui._log(self.ui.translations['processing_complete'])

                # Показываем результаты
                file_info = self.ui.get_file_info()
                self._on_processing_complete(file_info)

            except Exception as e:
                self.ui.progress.stop()
                self.ui.progress_label.config(text=self.ui.translations['processing_failed'])
                self.ui._log(f"Ошибка: {str(e)}")
                self.ui._show_error(self.ui.translations['processing_failed'])

            finally:
                self.ui.is_processing = False
                self.ui.process_button.config(state='normal')
                self.ui.load_button.config(state='normal')

        # Подменяем метод
        self.ui._simulate_processing = real_processing

        # Запускаем главный цикл
        self.root.mainloop()


def main():
    """Главная функция для запуска приложения."""
    root = tk.Tk()

    # Настройка стиля
    style = ttk.Style()
    style.theme_use('clam')

    # Создаём приложение
    app = SqueezerApp(root, language='ru')

    # Обработка закрытия окна
    def on_closing():
        app.ui.loader.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Запускаем
    app.run()


if __name__ == "__main__":
    main()
