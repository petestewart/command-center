"""
Setup script for Command Center
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
try:
    long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""
except (UnicodeDecodeError, Exception):
    # Fallback to simpler description if README has encoding issues
    long_description = "Terminal-based mission control for managing development tickets with AI agents"

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="command-center",
    version="0.1.0",
    author="Command Center Team",
    author_email="",
    description="Terminal-based mission control for managing development tickets with AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/petestewart/command-center",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ccc=ccc.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
