import xml.etree.ElementTree as ET
from pathlib import Path
import gzip
from urllib.request import urlopen


def download_repository(url_repository):
    """Загрузить данные репозитория по URL."""
    with urlopen(url_repository) as response:
        compressed_data = response.read()
        
    return gzip.decompress(compressed_data).decode("utf-8")

def find_package_record(package_name, repository_data):
    """Найти запись пакета в метаданных репозитория."""
    packages = repository_data.split("\n\n")
    for pkg in packages:
        if f"Package: {package_name}\n" in pkg:
            return pkg
    return None

def dependencies(package_record):
    """Извлечь зависимости из записи пакета."""
    lines = package_record.splitlines()
    result = []
    reading_dependencies = False

    for line in lines:
        if line.startswith("Depends:"):
            result.append(line.removeprefix("Depends:").strip())
            reading_dependencies = True

        elif reading_dependencies and line.startswith(" "):
            result.append(line.strip())

        elif reading_dependencies:
            break

    if result:
        return " ".join(result)

    return None

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
    
    #print(f"package name: {package_name}")
    #print(f"repository: {repository}")
    #print(f"test mode: {test_mode}")


    try:
        repository_data = download_repository(repository)
    except Exception as error:
        print(f"Ошибка при загрузке репозитория: {error}")
        return

    package_record = find_package_record(package_name, repository_data)

    if package_record is None:
        print(f"Пакет {package_name} не найден в репозитории.")
        return

    package_dependencies = dependencies(package_record)

    print(f"Зависимости пакета {package_name}:")
    if package_dependencies:
        print(package_dependencies)
    else:
        print("Зависимости не указаны.")

if __name__ == "__main__":
    main()

