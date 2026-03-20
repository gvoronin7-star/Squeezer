"""
Скрипт для восстановления системы "Соковыжималка" из бэкапа.
"""

import sys
import shutil
from pathlib import Path

# Настройка вывода для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def list_backups(backup_base_dir: Path) -> list:
    """
    Возвращает список доступных бэкапов.

    Args:
        backup_base_dir: Директория с бэкапами.

    Returns:
        Список путей к бэкапам.
    """
    if not backup_base_dir.exists():
        return []

    backups = []
    for item in backup_base_dir.iterdir():
        if item.is_dir() and item.name.startswith('squeezer_backup_'):
            backups.append(item)

    return sorted(backups, reverse=True)


def restore_from_backup(backup_dir: Path, target_dir: Path, dry_run: bool = False) -> dict:
    """
    Восстанавливает систему из бэкапа.

    Args:
        backup_dir: Директория бэкапа.
        target_dir: Целевая директория.
        dry_run: Если True, только показывает что будет сделано.

    Returns:
        Словарь со статистикой восстановления.
    """
    print(f"Восстановление: {backup_dir} -> {target_dir}")
    if dry_run:
        print("(режим проверки - файлы не будут копированы)")
    print("-" * 60)

    stats = {
        'files_to_restore': 0,
        'folders_to_restore': 0,
        'files_restored': 0,
        'folders_restored': 0,
        'skipped': 0,
        'errors': []
    }

    # Копируем файлы
    for item in backup_dir.iterdir():
        try:
            target_item = target_dir / item.name

            if item.is_file():
                stats['files_to_restore'] += 1

                # Проверяем существует ли файл
                if target_item.exists():
                    print(f"[SKIP] {item.name} (уже существует)")
                    stats['skipped'] += 1
                    continue

                if not dry_run:
                    shutil.copy2(item, target_item)
                    stats['files_restored'] += 1
                print(f"[FILE] {item.name}")

            elif item.is_dir():
                stats['folders_to_restore'] += 1

                # Проверяем существует ли папка
                if target_item.exists():
                    print(f"[SKIP] {item.name}/ (уже существует)")
                    stats['skipped'] += 1
                    continue

                if not dry_run:
                    shutil.copytree(item, target_item)
                    stats['folders_restored'] += 1
                print(f"[DIR]  {item.name}/")

        except Exception as e:
            error_msg = f"Ошибка при восстановлении {item.name}: {e}"
            print(f"[ERROR] {error_msg}")
            stats['errors'].append(error_msg)

    return stats


def select_backup(backups: list) -> Path:
    """
    Позволяет пользователю выбрать бэкап.

    Args:
        backups: Список доступных бэкапов.

    Returns:
        Выбранный бэкап.
    """
    print("Доступные бэкапы:")
    print()

    for i, backup in enumerate(backups, 1):
        # Извлекаем дату из имени
        name = backup.name.replace('squeezer_backup_', '')
        print(f"  {i}. {name}")

    print()
    print("0. Выход")
    print()

    while True:
        try:
            choice = input("Выберите бэкап (номер): ").strip()

            if choice == '0':
                return None

            index = int(choice) - 1
            if 0 <= index < len(backups):
                return backups[index]
            else:
                print(f"Неверный выбор. Введите число от 0 до {len(backups)}")

        except ValueError:
            print("Пожалуйста, введите число")
        except KeyboardInterrupt:
            print()
            return None


def main():
    """Главная функция."""
    # Определяем директории
    project_dir = Path(__file__).parent
    backup_base_dir = project_dir / "backups"

    print("=" * 60)
    print("Восстановление системы 'Соковыжималка'")
    print("=" * 60)
    print()

    # Получаем список бэкапов
    backups = list_backups(backup_base_dir)

    if not backups:
        print("Бэкапы не найдены.")
        print(f"Папка с бэкапами: {backup_base_dir}")
        return

    # Выбираем бэкап
    selected_backup = select_backup(backups)

    if not selected_backup:
        print("Отмена.")
        return

    print()
    print("=" * 60)
    print(f"Выбран бэкап: {selected_backup.name}")
    print("=" * 60)
    print()

    # Спрашиваем режим
    print("Режим восстановления:")
    print("  1. Обычный (копирует файлы)")
    print("  2. Проверка (только показывает что будет сделано)")
    print()

    while True:
        choice = input("Выберите режим (1-2): ").strip()

        if choice == '1':
            dry_run = False
            break
        elif choice == '2':
            dry_run = True
            break
        else:
            print("Пожалуйста, введите 1 или 2")

    print()

    try:
        # Восстанавливаем
        stats = restore_from_backup(selected_backup, project_dir, dry_run)

        # Выводим статистику
        print()
        print("=" * 60)

        if dry_run:
            print("Проверка завершена!")
        else:
            print("Восстановление завершено!")

        print("=" * 60)
        print()
        print("Статистика:")
        print(f"  Файлов для восстановления: {stats['files_to_restore']}")
        print(f"  Папок для восстановления: {stats['folders_to_restore']}")
        print(f"  Восстановлено файлов: {stats['files_restored']}")
        print(f"  Восстановлено папок: {stats['folders_restored']}")
        print(f"  Пропущено (существует): {stats['skipped']}")

        if stats['errors']:
            print()
            print("Ошибки:")
            for error in stats['errors']:
                print(f"  - {error}")

        if not dry_run and stats['files_restored'] > 0:
            print()
            print("Восстановление завершено успешно!")

    except Exception as e:
        print()
        print("=" * 60)
        print(f"ОШИБКА при восстановлении: {e}")
        print("=" * 60)


if __name__ == "__main__":
    main()
