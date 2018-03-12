from setuptools import setup

setup(
    name='TStarBot',
    version='0.1',
    description='TStartBot',
    keywords='TStartBot',
    packages=[
        'tstarbot',
        'tstarbot.bin',
    ],

    install_requires=[
        'pysc2',
    ],
)
