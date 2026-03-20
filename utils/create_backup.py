"""
Скрипт для создания бэкапа системы "Соковыжималка".
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Настройка вывода для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Исключаемые файлы и папки
EXCLUDE = {
    # Временные файлы
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.pytest_cache',

    # Логи и временные данные
    'logs',
    'temp_uploads',
    'temp_rag_processing',
    '*.log',

    # Виртуальное окружение
    'venv',
    'env',
    '.venv',
    '.env',

    # Выходные данные
    'output',
    'output_module_2',
    'output_module_3',
    'output_module_4',
    'rag_bases',

    # PDF файлы
    'pdfs',

    # Git
    '.git',
    '.gitignore',

    # IDE
    '.vscode',
    '.idea',
    '*.swp',
    '*.swo',
    '*~',

    # OS
    '.DS_Store',
    'Thumbs.db',
    'desktop.ini',

    # Примеры и тесты
    'test_*.py',
    'demo_*.py',

    # Бэкапы (избегаем рекурсии)
    'backups',
    'create_backup.py',
    'restore_backup.py',
}


def should_exclude(path: Path) -> bool:
    """
    Проверяет, нужно ли исключить файл/папку.

    Args:
        path: Путь к файлу/папке.

    Returns:
        True если нужно исключить, иначе False.
    """
    # Проверяем имя файла/папки
    name = path.name

    # Исключаем по точному совпадению
    if name in EXCLUDE:
        return True

    # Исключаем по шаблону
    for pattern in EXCLUDE:
        if pattern.startswith('*'):
            if name.endswith(pattern[1:]):
                return True
        elif pattern.startswith('.') and name.startswith('.'):
            if name == pattern or name.startswith(pattern + '/'):
                return True

    # Исключаем скрытые файлы (Unix)
    if name.startswith('.') and name not in {'.gitkeep', '.gitattributes'}:
        return True

    return False


def create_backup(source_dir: Path, backup_dir: Path) -> dict:
    """
    Создаёт бэкап системы.

    Args:
        source_dir: Исходная директория.
        backup_dir: Директория для бэкапа.

    Returns:
        Словарь со статистикой бэкапа.
    """
    print(f"Создание бэкапа: {source_dir} -> {backup_dir}")
    print("-" * 60)

    # Создаём директорию для бэкапа
    backup_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        'files_copied': 0,
        'folders_created': 0,
        'total_size': 0,
        'excluded': 0,
        'errors': []
    }

    # Копируем файлы
    for item in source_dir.iterdir():
        if should_exclude(item):
            print(f"[SKIP] {item.name}")
            stats['excluded'] += 1
            continue

        try:
            if item.is_file():
                # Копируем файл
                dest_file = backup_dir / item.name
                shutil.copy2(item, dest_file)
                stats['files_copied'] += 1
                stats['total_size'] += item.stat().st_size
                print(f"[FILE] {item.name}")

            elif item.is_dir():
                # Копируем папку рекурсивно
                dest_dir = backup_dir / item.name
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)

                shutil.copytree(item, dest_dir,
                              ignore=shutil.ignore_patterns(*EXCLUDE))
                stats['folders_created'] += 1
                print(f"[DIR]  {item.name}/")

        except Exception as e:
            error_msg = f"Ошибка при копировании {item.name}: {e}"
            print(f"[ERROR] {error_msg}")
            stats['errors'].append(error_msg)

    return stats


def main():
    """Главная функция."""
    # Определяем директории
    project_dir = Path(__file__).parent
    backup_base_dir = project_dir / "backups"

    # Создаём папку для бэкапов
    backup_base_dir.mkdir(exist_ok=True)

    # Генерируем имя бэкапа с датой и временем
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = backup_base_dir / f"squeezer_backup_{timestamp}"

    print("=" * 60)
    print("Создание бэкапа системы 'Соковыжималка'")
    print("=" * 60)
    print()

    try:
        # Создаём бэкап
        stats = create_backup(project_dir, backup_dir)

        # Выводим статистику
        print()
        print("=" * 60)
        print("Бэкап успешно создан!")
        print("=" * 60)
        print(f"Путь: {backup_dir}")
        print()
        print("Статистика:")
        print(f"  Файлов скопировано: {stats['files_copied']}")
        print(f"  Папок создано: {stats['folders_created']}")
        print(f"  Исключено: {stats['excluded']}")
        print(f"  Общий размер: {stats['total_size'] / (1024*1024):.2f} MB")

        if stats['errors']:
            print()
            print("Ошибки:")
            for error in stats['errors']:
                print(f"  - {error}")

        print()
        print("Для восстановления скопируйте файлы из папки бэкапа в проект.")

    except Exception as e:
        print()
        print("=" * 60)
        print(f"ОШИБКА при создании бэкапа: {e}")
        print("=" * 60)


if __name__ == "__main__":
    main()
