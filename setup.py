import ast
from pathlib import Path

from setuptools import find_packages, setup


PROJECT_ROOT = Path(__file__).resolve().parent
README_PATH = PROJECT_ROOT / "README.md"
VERSION_PATH = PROJECT_ROOT / "labscraper" / "__version__.py"
version_namespace: dict[str, str] = {}
# Load __version__ from a trusted file using a literal-only parse.
version_module = ast.parse(VERSION_PATH.read_text(encoding="utf-8"), filename=str(VERSION_PATH))
for node in version_module.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__version__":
                if isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, str):
                        version_namespace["__version__"] = node.value.value
                    else:
                        raise ValueError("__version__ must be assigned a literal string")
                elif isinstance(node.value, ast.Str):
                    version_namespace["__version__"] = node.value.s
                else:
                    raise ValueError("__version__ must be assigned a literal string")
                break
        if "__version__" in version_namespace:
            break
if "__version__" not in version_namespace:
    raise ValueError("__version__ assignment not found in VERSION_PATH")

long_description = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""


setup(
    name="labscraper",
    version=version_namespace["__version__"],
    packages=find_packages(),
    python_requires=">=3.11",
    description="Domain-aware PDF scraping and dual-lens export tooling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LabScraper contributors",
    author_email="",
    url="https://github.com/Magikmikedaboss/labscraper",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "feedparser>=6.0,<7.0",
        "pdfplumber>=0.11,<1.0",
        "pdfminer.six>=2020.0,<20270000",
        "pandas>=2.0,<4.0",
        "numpy>=1.24,<3.0",
        "requests>=2.34.2,<3.0",
    ],
)