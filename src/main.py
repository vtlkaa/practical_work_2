import xml.etree.ElementTree as ET
from pathlib import Path
import gzip
from urllib.request import urlopen
import re
import sys

if len(sys.argv) > 1:
    config_path = Path(sys.argv[1])
else:
    config_path = Path("config/config_test.xml")

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

def find_reverse_dependencies(package_name, graph):
    """Найти обратные зависимости с помощью DFS."""
    reverse_graph = {package: [] for package in graph}

    for package, dependencies in graph.items():
        for dependency in dependencies:
            reverse_graph[dependency].append(package)

    result = []
    visited = {package_name}

    def dfs(current_package):
        for dependent in reverse_graph[current_package]:
            if dependent not in visited:
                visited.add(dependent)
                result.append(dependent)
                dfs(dependent)

    dfs(package_name)
    return result

def main():
    """Загрузить настройки и найти обратные зависимости пакета."""
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
        test_graph = parse_test_repository(repository)

        if package_name not in test_graph:
            raise ValueError(f"Пакет {package_name} не найден в тестовом репозитории.")

        reverse_dependencies = find_reverse_dependencies(package_name, test_graph)

        print(f"\nОбратные зависимости пакета {package_name}:")

        if reverse_dependencies:
            for package in reverse_dependencies:
                print(package)
        else:
            print("Обратных зависимостей нет.")

    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}")

if __name__ == "__main__":
    main()
