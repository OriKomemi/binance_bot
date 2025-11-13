from setuptools import setup, find_packages

setup(
    name="binance-spot-bot",
    version="0.1.0",
    description="Low-risk Binance spot crypto trading bot",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    entry_points={
        "console_scripts": [
            "binance-bot=main:main",
        ],
    },
)
