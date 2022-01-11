#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import setuptools

setuptools.setup(
    name="quadstarfiles",
    version="0.2.0",
    author="Nicolas Vetsch",
    author_email="vetschnicolas@gmail.com",
    description="Parsing and converting .sac QMS files more efficiently than Quadstar 32-bit.",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/vetschn/quadstarfiles",
    project_urls={
        'Bug Tracker': "https://github.com/vetschn/eclabfiles/issues",
    },
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering',
    ],
    keywords=['.sac', 'Pfeiffer', 'QMS', 'Quadstar 32-bit'],
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    install_requires=['numpy', 'pandas', 'openpyxl'],
    python_requires='>=3.9',
)
