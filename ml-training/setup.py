from setuptools import setup, find_packages

setup(
    name="ml-training",
    version="0.1.0",
    description="ML Training Pipeline for CIC-IDS-2017 and CIC-DDoS-2019",
    author="Alonso Jimenez",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.3.0",
        "onnx>=1.14.0",
        "skl2onnx>=1.15.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "jupyter>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.4.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "ml-explore=ml_training.cli:explore",
            "ml-train=ml_training.cli:train",
        ]
    },
)
