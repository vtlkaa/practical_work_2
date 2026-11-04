import xml.etree.ElementTree as ET
from pathlib import Path
import gzip
from urllib.request import urlopen
import re
import sys

if len(sys.argv) > 1:
    config_path = Path(sys.argv[1])
else:
    config_path = Path("config/config.xml")

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
    """Извлечь Pre-Depends и Depends из записи пакета."""
    lines = package_record.splitlines()
    result = {"Pre-Depends": [],"Depends": []}

    current_field = None

    for line in lines:
        if line.startswith("Pre-Depends:"):
            current_field = "Pre-Depends"
            result[current_field].append(line.removeprefix("Pre-Depends:").strip())

        elif line.startswith("Depends:"):
            current_field = "Depends"
            result[current_field].append(line.removeprefix("Depends:").strip())

        elif line.startswith(" ") and current_field:
            result[current_field].append(line.strip())

        else:
            current_field = None

    for field in result:
        result[field] = " ".join(result[field]) or None

    return result

def get_dependencies_names(package_record):
    """Получить имена зависимостей пакета."""
    package_dependencies = dependencies(package_record)

    result = []
    for field in ["Pre-Depends", "Depends"]:
        value = package_dependencies[field]

        if not value:
            continue

        for dependency in value.split(","):
            dependency = dependency.strip()
            package_name = dependency.split(" ")[0]
            result.append(package_name)

    return result

def build_dependency_graph(package_name, get_dependencies):
    """Построить граф зависимостей пакетов с помощью DFS."""
    graph = {}
    visited = set()
    visiting = set()

    def dfs(current_package):
        if current_package in visiting:
            print(f"Обнаружен цикл зависимостей: {current_package}")
            return

        if current_package in visited:
            return

        visiting.add(current_package)

        dependency_names = get_dependencies(current_package)
        graph[current_package] = dependency_names

        for dependency_name in dependency_names:
            dfs(dependency_name)

        visiting.remove(current_package)
        visited.add(current_package)

    dfs(package_name)
    return graph

def parse_dependency_line(line):
    """Разобрать строку с именем пакета и его зависимостями."""
    match = re.fullmatch(r"([A-Z]+)\s*:\s*(.*)", line)

    if not match:
        raise ValueError(f"Некорректная строка: {line}")

    package_name = match.group(1)
    dependencies_text = match.group(2).strip()

    if dependencies_text:
        dependency_names = [name.strip() for name in dependencies_text.split(",")]

        for name in dependency_names:
            if not re.fullmatch(r"[A-Z]+", name):
                raise ValueError(f"Некорректное имя зависимости: {name}")
    else:
        dependency_names = []

    return package_name, dependency_names

def parse_test_repository(file_path):
    """Прочитать тестовый репозиторий из файла."""
    graph = {}

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            package_name, dependency_names = (parse_dependency_line(line))

            if package_name in graph:
                raise ValueError(f"Пакет {package_name} указан повторно.")

            graph[package_name] = dependency_names

    for package_name, dependency_names in graph.items():
        for dependency_name in dependency_names:
            if dependency_name not in graph:
                raise ValueError(f"Зависимость {dependency_name} "f"пакета {package_name} не найдена.")

    return graph


def get_real_dependencies(package_name, repository_data):
    """Получить прямые зависимости пакета из репозитория Ubuntu."""
    package_record = find_package_record(package_name, repository_data)

    if package_record is None:
        print(
            f"Предупреждение: пакет {package_name} не найден. "
            "Его зависимости не раскрыты."
        )
        return []

    return get_dependencies_names(package_record)

def get_test_dependencies(package_name, test_graph):
    """Получить зависимости пакета из тестового репозитория."""
    if package_name not in test_graph:
        raise ValueError(f"Пакет {package_name} не найден в тестовом репозитории.")
    return test_graph[package_name]

def print_direct_dependencies(package_name, repository_data):
    """Вывести прямые зависимости пакета."""
    package_record = find_package_record(package_name, repository_data)

    if package_record is None:
        raise ValueError(f"Пакет {package_name} не найден в репозитории.")

    package_dependencies = dependencies(package_record)
    dependency_names = get_dependencies_names(package_record)

    print(f"\nПрямые зависимости пакета {package_name}:")

    print(f"Pre-Depends: {package_dependencies['Pre-Depends'] or 'нет'}")
    print(f"Depends: {package_dependencies['Depends'] or 'нет'}")
    print(f"Имена пакетов: {dependency_names}")


def main():
    """Загрузить настройки и запустить построение графа зависимостей."""

    try:
        root = ET.parse(config_path).getroot()
    except FileNotFoundError:
        print(f"Файл конфигурации {config_path} не найден.")
        return
    except ET.ParseError:
        print(f"Ошибка: файл {config_path} содержит некорректный XML.")
        return

    package_name = root.findtext("package_name")
    repository = root.findtext("repository")

    if not package_name or not package_name.strip():
        print("Ошибка: не задано имя пакета.")
        return

    if not repository or not repository.strip():
        print("Ошибка: не указан репозиторий.")
        return

    package_name = package_name.strip()
    repository = repository.strip()

    try:
        if config_path.name == "config_test.xml":
            test_graph = parse_test_repository(repository)

            dependency_graph = build_dependency_graph(
                package_name,
                lambda name: get_test_dependencies(name, test_graph)
            )
        else:
            repository_data = download_repository(repository)

            print_direct_dependencies(package_name, repository_data)

            dependency_graph = build_dependency_graph(
                package_name,
                lambda name: get_real_dependencies(name, repository_data)
            )

        print(f"\nГраф зависимостей пакета {package_name}:")
        for package, dependency_names in dependency_graph.items():
            print(f"{package} -> {dependency_names}")

    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}")
    except Exception as error:
        print(f"Ошибка при обработке репозитория: {error}")


if __name__ == "__main__":
    main()