import xml.etree.ElementTree as ET
from pathlib import Path

config_path = Path("config/config.xml")

def main():
    """Загрузить настройки и вывести их на экран."""
    
    try:
        root = ET.parse(config_path).getroot()

    except FileNotFoundError:
        print(f"Файл: {config_path} не найден.")
        return

    except ET.ParseError:
        print(f"Ошибка: файл {config_path} содержит некорректный XML.")
        return

    package_name = root.findtext("package_name")
    repository = root.findtext("repository")
    test_mode = root.findtext("test_mode")  

    if not package_name or not package_name.strip():
        print("Ошибка: не задано имя пакета.")
        return

    if not repository or not repository.strip():
        print("Ошибка: не указан репозиторий.")
        return

    if not test_mode or not test_mode.strip():
        print("Ошибка: не задан режим тестирования.")
        return
    
    print(f"package name: {package_name}")
    print(f"repository: {repository}")
    print(f"test mode: {test_mode}")


if __name__ == "__main__":
    main()

