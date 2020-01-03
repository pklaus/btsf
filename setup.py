# -*- coding: utf-8 -*-

from setuptools import setup

try:
    import pypandoc
    LDESC = open('README.md', 'r').read()
    LDESC = pypandoc.convert(LDESC, 'rst', format='md')
except (ImportError, IOError, RuntimeError) as e:
    print("Could not create long description:")
    print(str(e))
    LDESC = ''

setup(name='btsf',
      version = '0.1dev',
      description = 'btsf (for Binary Time Series File) is a package to store your data in a condensed and fast yet flexible way.',
      long_description = LDESC,
      author = 'Philipp Klaus',
      author_email = 'philipp.l.klaus@web.de',
      url = 'https://github.com/pklaus/btsf',
      license = 'GPL',
      #packages = ['',],
      py_modules = ['btfs',],
      entry_points = {
          'console_scripts': [
              #'btfs = btfs:main',
          ],
      },
      zip_safe = True,
      platforms = 'any',
      install_requires = [
          "attrs",
      ],
      test_suite = 'nose.collector',
      tests_require = ['nose'],
      keywords = 'Binary Time Series File Storage',
      classifiers = [
          'Development Status :: 4 - Beta',
          'Operating System :: OS Independent',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Topic :: System :: Archiving :: Compression',
          'Topic :: Office/Business :: Financial',
          'Topic :: Scientific/Engineering',
      ]
)
