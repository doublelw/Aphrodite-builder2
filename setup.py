from setuptools import setup, find_packages

setup(
    name='batteryfold',
    version='1.0.0',
    description='First-principles molecular design platform for organic battery materials',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/doublelw/Aphrodite-builder2',
    author='Wei Liu',
    author_email='13322429758@163.com',
    license='MIT',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[
        'numpy',
        'pyyaml',
    ],
    extras_require={
        'ai': [
            'anthropic',
            'openai',
        ],
        'model': [
            'torch',
        ],
        'chemistry': [
            'rdkit',
        ],
        'full': [
            'anthropic',
            'openai',
            'torch',
            'rdkit',
        ],
    },
    entry_points={
        'console_scripts': [
            'batteryfold=src.cli.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)
