import subprocess
from collections import defaultdict
from pathlib import Path

SCRIPT = Path(__file__)
PROJECT_ROOT = SCRIPT.parent.parent
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"
REQUIREMENTS_DIR = PROJECT_ROOT / "cvat" / "requirements"
BASE_REQUIREMENTS = REQUIREMENTS_DIR / "base.txt"
PRODUCTION_REQUIREMENTS = REQUIREMENTS_DIR / "production.txt"
DEVELOPMENT_REQUIREMENTS = REQUIREMENTS_DIR / "development.txt"
ALL_REQUIREMENTS = REQUIREMENTS_DIR / "all.txt"
TESTING_REQUIREMENTS = REQUIREMENTS_DIR / "testing.txt"


def run_uv_commands():
    """Run the initial uv commands to generate requirement files."""
    commands = [
        ["uv", "lock"],
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            "-o",
            str(BASE_REQUIREMENTS.absolute()),
        ],
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            "--extra",
            "production",
            "-o",
            str(PRODUCTION_REQUIREMENTS.absolute()),
        ],
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            "--extra",
            "development",
            "-o",
            str(DEVELOPMENT_REQUIREMENTS.absolute()),
        ],
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            "--extra",
            "testing",
            "-o",
            str(TESTING_REQUIREMENTS.absolute()),
        ],
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            "--all-extras",
            "-o",
            str(ALL_REQUIREMENTS.absolute()),
        ],
    ]

    for cmd in commands:
        subprocess.run(cmd, check=True)  # noseq: B603  # commands are hardcoded


def parse_requirements(file_path: Path) -> dict[str, list[str]]:
    """
    Parse a requirements file and return a dictionary of package names and their full entries.
    Each entry is preserved as a list of lines to maintain exact formatting.
    """
    packages = defaultdict(list)
    current_package = None

    with open(file_path, "r") as f:
        for line in f:
            if not current_package and (
                not line.strip() or line.strip().startswith("#")
            ):
                # skipping previous empty lines and comments
                continue

            if line.startswith(" "):
                if not current_package:
                    raise ValueError("Unexpected indentation in requirements file")
                packages[current_package].append(line)
            else:
                current_package = line
                packages[current_package].append(current_package)

    return packages


def write_requirements(
    output_path: Path, packages: dict[str, list[str]], *parents: Path
):
    content = "".join(
        (
            f"# This file was autogenerated via {SCRIPT.relative_to(PROJECT_ROOT)}\n",
            *(f"-r {parent.relative_to(output_path.parent)}\n" for parent in parents),
            "\n",
            *(line for package_lines in packages.values() for line in package_lines),
        )
    )
    output_path.write_text(content)


def deduplicate_requirements():
    """Process all requirements files to remove duplicates and add proper references."""
    base_packages = parse_requirements(BASE_REQUIREMENTS)
    write_requirements(BASE_REQUIREMENTS, base_packages)
    prod_unique = {
        k: v
        for k, v in parse_requirements(PRODUCTION_REQUIREMENTS).items()
        if k not in base_packages
    }

    write_requirements(PRODUCTION_REQUIREMENTS, prod_unique, BASE_REQUIREMENTS)
    dev_packages = parse_requirements(DEVELOPMENT_REQUIREMENTS)
    dev_unique = {k: v for k, v in dev_packages.items() if k not in base_packages}
    write_requirements(DEVELOPMENT_REQUIREMENTS, dev_unique, BASE_REQUIREMENTS)
    test_unique = {
        k: v
        for k, v in parse_requirements(TESTING_REQUIREMENTS).items()
        if k not in base_packages and k not in dev_packages
    }
    write_requirements(TESTING_REQUIREMENTS, test_unique, DEVELOPMENT_REQUIREMENTS)
    write_requirements(
        ALL_REQUIREMENTS,
        {},
        DEVELOPMENT_REQUIREMENTS,
        PRODUCTION_REQUIREMENTS,
        TESTING_REQUIREMENTS,
    )


def main():
    """Main function to run the requirements processing."""
    run_uv_commands()
    deduplicate_requirements()
    print("Requirements files have been successfully processed.")


if __name__ == "__main__":
    main()