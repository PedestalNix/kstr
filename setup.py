from setuptools import setup

setup(
    name='kstr',
    version='0.1.0',
    py_modules=['kstr'],
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'kstr = kstr:cli',
        ],
    },
)
