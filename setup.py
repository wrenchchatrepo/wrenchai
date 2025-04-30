from setuptools import setup, find_packages

setup(
    name="wrenchai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115.12",
        "pydantic>=2.11.3",
        "pytest>=8.3.5",
        "pytest-asyncio>=0.23.5",
    ],
) 