from setuptools import setup, find_packages

setup(
    name='urmom-lang',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'urm=src.cli:main',
            'urm-pkg=src.tools.pkg_manager:main',
            'urm-test=src.tools.test_runner:main',
        ],
    },
    python_requires='>=3.8',
)
