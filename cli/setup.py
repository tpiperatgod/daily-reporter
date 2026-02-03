"""Setup configuration for xndctl CLI tool."""

from setuptools import setup, find_packages

setup(
    name="xndctl",
    version="0.1.0",
    description="CLI tool for managing X News Digest system",
    author="X News Digest Team",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "httpx>=0.24.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "croniter>=1.3.0",
        "pydantic>=2.0.0",
        "pydantic[email]>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "xndctl=xndctl.cli:cli",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
