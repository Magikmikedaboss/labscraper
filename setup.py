from pathlib import Path

from setuptools import find_packages, setup


PROJECT_ROOT = Path(__file__).resolve().parent
README_PATH = PROJECT_ROOT / "README.md"
VERSION_PATH = PROJECT_ROOT / "labscraper" / "__version__.py"
version_namespace: dict[str, str] = {}
# Load __version__ from a simple trusted file at VERSION_PATH.
# This uses exec, so VERSION_PATH must not be user-controlled; if that is not
# guaranteed, prefer parsing the file or importing a module instead.
exec(VERSION_PATH.read_text(encoding="utf-8"), version_namespace)

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
    url="https://github.com/labscraper/labscraper",
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