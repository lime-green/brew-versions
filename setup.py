import os
from os.path import exists, join
from setuptools import find_packages, setup

base_dir = os.path.dirname(__file__)
readme_path = join(base_dir, "README.md")
if exists(readme_path):
    with open(readme_path) as stream:
        long_description = stream.read()
else:
    long_description = ""

INSTALL_REQUIRES = ("click", "colorlog", "requests")
DEV_REQUIRES = ("black", "flake8", "pytest")


setup(
    name="brew-versions",
    install_requires=INSTALL_REQUIRES,
    extras_require=dict(
        dev=DEV_REQUIRES,
    ),
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="Manage different versions of homebrew packages",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Josh DM",
    url="https://github.com/lime-green/brewv",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={
        "console_scripts": [
            "brewv = brewv:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.6, <4",
    license="MIT",
    keywords=["brew", "homebrew", "homebrew version", "development", "macos", "linux"],
)
