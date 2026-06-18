import ast
import pathlib
import sys

import tomllib

PYPROJECT_PATH = pathlib.Path("pyproject.toml")
INIT_PATH = pathlib.Path("qbittorrent2mqtt/__init__.py")


def get_pyproject_version() -> str:
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)
    if "project" not in data:
        raise ValueError("pyproject.toml has no [project] section")
    if "version" not in data["project"]:
        raise ValueError("pyproject.toml [project] has no version field")
    return data["project"]["version"]


def get_init_version() -> str:
    tree = ast.parse(INIT_PATH.read_text(), filename=str(INIT_PATH))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise ValueError(f"Could not find __version__ in {INIT_PATH!s}")


def main():
    try:
        pyproject_version = get_pyproject_version()
        init_version = get_init_version()
    except ValueError as exc:
        print(f"pre-commit: {exc}", file=sys.stderr)
        sys.exit(1)

    if pyproject_version != init_version:
        print(
            f"pre-commit: version mismatch: {PYPROJECT_PATH!s}={pyproject_version}, {INIT_PATH!s}={init_version}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
