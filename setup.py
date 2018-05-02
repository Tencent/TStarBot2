from setuptools import setup

setup(
    name='TStarBot',
    version='0.1',
    description='TStartBot',
    keywords='TStartBot',
    packages=[
        'tstarbot',
        'tstarbot.bin',
        'tstarbot.data',
        'tstarbot.data.pool',
        'tstarbot.data.queue',
        'tstarbot.act',
    ],

    install_requires=[
        'pysc2',
        'pillow'
    ],
)
