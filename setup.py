#!/usr/bin/env python

import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

setup(name='layer_snap',
      version='0.0.1',
      description='layer_snap',
      long_description=README,
      license='Apache License 2.0',
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
      ],
      url='https://git.launchpad.net/layer-snap',
      package_dir={'': 'lib'},
      packages=['charms/layer'],
      include_package_data=True,
      zip_safe=False,
      )
