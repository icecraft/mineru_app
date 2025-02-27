from setuptools import setup, find_packages
from src.version import __version__

def parse_requirements(filename):
    with open(filename) as f:
        lines = f.read().splitlines()

    requires = []

    for line in lines:
        if "http" in line:
            pkg_name_without_url = line.split('@')[0].strip()
            requires.append(pkg_name_without_url)
        else:
            requires.append(line)

    return requires

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mineru_app",
    version=__version__,
    author="Opendatalab",
    description="A PDF processing and conversion tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/opendatalab/MinerU-App",  # Replace with your actual repository URL
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'src': [
            'header.html',
            'examples/*.pdf',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Adjust the license as needed
        "Operating System :: OS Independent",
    ],
    python_requires="==3.10.*",
    install_requires=parse_requirements('requirements.txt'),
    entry_points={
        "console_scripts": [
            "mineru_app=src.app:main",  # Adjust the entry point based on your needs
        ],
    },
) 