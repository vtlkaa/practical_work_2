import xml.etree.ElementTree as ET
from pathlib import Path
import gzip
from urllib.request import urlopen
import re
import sys
import shutil
import subprocess

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

            package_name, dependency_names = parse_dependency_line(line)

            if package_name in graph:
                raise ValueError(f"Пакет {package_name} указан повторно.")

            graph[package_name] = dependency_names

    for package_name, dependency_names in graph.items():
        for dependency_name in dependency_names:
            if dependency_name not in graph:
                raise ValueError(f"Зависимость {dependency_name} "f"пакета {package_name} не найдена.")

    return graph

def download_repository(url_repository):
    """Скачать и распаковать метаданные пакетов Ubuntu."""
    with urlopen(url_repository) as response:
        compressed_data = response.read()

    return gzip.decompress(compressed_data).decode("utf-8")

def find_package_record(package_name, repository_data):
    """Найти запись пакета по его имени в метаданных репозитория."""
    for package_record in repository_data.split("\n\n"):
        for line in package_record.splitlines():
            if line.startswith("Package:"):
                name = line.split(":", 1)[1].strip()

                if name == package_name:
                    return package_record

                break

    return None

def dependencies(package_record):
    """Извлечь поля Depends и Pre-Depends из записи пакета."""
    result = {"Pre-Depends": [],"Depends": []}

    current_field = None

    for line in package_record.splitlines():
        if line.startswith("Pre-Depends:"):
            current_field = "Pre-Depends"
            value = line.split(":", 1)[1].strip()
            result[current_field].append(value)

        elif line.startswith("Depends:"):
            current_field = "Depends"
            value = line.split(":", 1)[1].strip()
            result[current_field].append(value)

        elif line.startswith(" ") and current_field:
            result[current_field].append(line.strip())

        else:
            current_field = None

    for field in result:
        result[field] = " ".join(result[field]) or None

    return result

def get_dependencies_names(package_record):
    """Получить имена пакетов из Depends и Pre-Depends."""
    package_dependencies = dependencies(package_record)
    result = []

    for field in ("Pre-Depends", "Depends"):
        value = package_dependencies[field]

        if not value:
            continue

        for dependency in value.split(","):
            dependency = dependency.strip()

            if not dependency:
                continue

            package_name = re.split(r"[\s(:]", dependency, maxsplit=1)[0]

            if package_name and package_name not in result:
                result.append(package_name)

    return result

def get_real_dependencies(package_name, repository_data):
    """Получить прямые зависимости пакета из Ubuntu."""
    package_record = find_package_record(
        package_name,
        repository_data
    )

    if package_record is None:
        print(
            f"Предупреждение: пакет {package_name} "
            "не найден в репозитории."
        )
        return []

    return get_dependencies_names(package_record)

def build_dependency_graph(package_name, get_dependencies):
    """Построить граф зависимостей с помощью обхода в глубину."""
    graph = {}
    visited = set()
    visiting = set()

    def dfs(current_package):
        if current_package in visited:
            return

        if current_package in visiting:
            print(
                f"Обнаружен цикл зависимостей: {current_package}"
            )
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

def generate_d2(package_name, graph):
    """Сформировать описание графа зависимостей в формате D2."""
    visited = set()
    edges = []
    added_edges = set()

    def dfs(current_package):
        if current_package in visited:
            return

        visited.add(current_package)

        for dependency in graph[current_package]:
            edge = (current_package, dependency)

            if edge not in added_edges:
                edges.append(edge)
                added_edges.add(edge)

            dfs(dependency)

    dfs(package_name)

    lines = []

    for source, target in edges:
        lines.append(f"{source} -> {target}")

    return "\n".join(lines)

def create_diagram(package_name, graph):
    """Создать SVG-диаграмму зависимостей с помощью D2."""
    d2_text = generate_d2(package_name, graph)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    d2_file = output_dir / f"dependencies_{package_name}.d2"
    svg_file = output_dir / f"dependencies_{package_name}.svg"

    d2_file.write_text(d2_text + "\n", encoding="utf-8")

    d2_executable = shutil.which("d2")

    if d2_executable is None:
        candidate = Path.home() / "Downloads" / "D2" / "d2.exe"

        if candidate.is_file():
            d2_executable = str(candidate)

    if d2_executable is None:
        print("Ошибка: не удалось найти исполняемый файл D2.")
        return

    try:
        subprocess.run([d2_executable,str(d2_file.resolve()),str(svg_file.resolve()),],check=True,)

        print(f"Описание D2: {d2_file}")
        print(f"Диаграмма SVG: {svg_file}")


    except subprocess.CalledProcessError as error:
        print(f"Ошибка при создании SVG: {error}")
    except OSError as error:
        print(f"Не удалось запустить D2: {error}")

def main():
    root = ET.parse(config_path).getroot()

    package_name = root.findtext("package_name").strip()
    repository = root.findtext("repository").strip()

    if config_path.name == "config_test.xml":
        graph = parse_test_repository(repository)
    else:
        print("Загрузка метаданных репозитория Ubuntu...")
        repository_data = download_repository(repository)

        graph = build_dependency_graph(package_name,lambda name: get_real_dependencies(name,repository_data))

    if package_name not in graph:
        print(f"Пакет {package_name} не найден.")
        return

    print(f"\nГраф зависимостей пакета {package_name}")

    print(f"Диаграмма D2 для пакета {package_name}:")
    print(generate_d2(package_name, graph))

    create_diagram(package_name, graph)

if __name__ == "__main__":
    main()