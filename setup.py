#!/usr/bin/env python
"""
Nexus: Record and replay Playwright navigation on blockchain (IPFS).
Installation setup for pip/pipx.
"""

from setuptools import setup, find_packages
import os

# Read version from __init__.py
version = {}
with open(os.path.join('nexus', '__init__.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            exec(line, version)
            break

# Read long description from README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='nexus-autopaths',
    version=version.get('__version__', '0.1.0'),
    author='Hyperlog',
    author_email='nattimmis@gmail.com',
    description='Record and replay web navigation via Playwright, store waypoints on IPFS',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/nattimmis/nexus',
    project_urls={
        'Bug Tracker': 'https://github.com/nattimmis/nexus/issues',
        'Documentation': 'https://github.com/nattimmis/nexus#readme',
        'Source Code': 'https://github.com/nattimmis/nexus',
    },
    license='Apache 2.0',
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=[
        'playwright>=1.40.0',
        'click>=8.1.0',
        'requests>=2.31.0',
        'pydantic>=2.0.0',
        'python-dotenv>=1.0.0',
        'aiohttp>=3.9.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.1.0',
            'black>=23.0.0',
            'isort>=5.12.0',
            'mypy>=1.5.0',
            'flake8>=6.1.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'nexus=nexus.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Testing',
        'Topic :: Internet :: WWW/HTTP :: Browsers',
    ],
    keywords='playwright automation testing web-automation blockchain ipfs recording replay',
)
