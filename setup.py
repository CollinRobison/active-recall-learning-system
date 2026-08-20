from setuptools import find_packages, setup


setup(
    name="portable-active-recall",
    version="0.1.0",
    description="Markdown-first, harness-agnostic active recall learning workspace tools",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.9",
    entry_points={"console_scripts": ["learning=active_recall.cli:main"]},
)
