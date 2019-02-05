#!/usr/bin/env python

from distutils.core import setup
import versioneer

setup(name='sotoddb',
      version=versioneer.get_version(),
      description='TOD Pipeline Database Library',
      author='Simons Observatory Collaboration',
      author_email='software@simonsobsveratory.org',
      url='https://simonsobservatory.org/software/',
      packages=['sotoddb'],
      cmdclass=versioneer.get_cmdclass(),
     )
