from setuptools import setup, find_packages

install_requires=[
    'lxml',
    'attrs',
    'sortedcontainers',
    'toposort'
]

test_dependencies = [
    'pytest',
    'lxml-asserts',
    'pytest-lazy-fixture'
]

extras = {
    'test': test_dependencies,
}

setup(
    name='cassis',
    version='0.0.1',
    packages=find_packages(),
    
    author="DKPro cassis Team",
    author_email="dkpro-core-user@googlegroups.com",
    description='UIMA CAS processing library in Python',
    license='Apache License 2.0',
    keywords='uima cas xmi',
    url='https://github.com/dkpro/dkpro-cassis',
    

    project_urls={
        'Bug Tracker': 'https://github.com/dkpro/dkpro-cassis/issues',
        'Documentation': 'https://cassis.readthedocs.org/',
        'Source Code': 'https://github.com/dkpro/dkpro-cassis',
    },

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries'
    ],

    install_requires=install_requires,
    test_suite='tests',

    tests_require=test_dependencies,
    extras_require=extras,
)
