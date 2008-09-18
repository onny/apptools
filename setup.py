#!/usr/bin/env python
#
# Copyright (c) 2008 by Enthought, Inc.
# All rights reserved.
#

"""
ETS Application Tools

The AppTools project includes a set of packages that Enthought has found useful
in creating a number of applications. They implement functionality that is
commonly needed by many applications

- **enthought.appscripting**: Framework for scripting applications.
- **enthought.help**: Implements the Adobe RoboHelp API in Python, for
  compiled HTML Help (.chm) and RoboHelp WebHelp formats. Includes an Envisage
  plug-in to provide context-sensitive help for applications. Can also be used
  in Traits-based, non-Envisage applications.
- **enthought.io**: Provides an abstraction for files and folders in a file
  system.
- **enthought.naming**: Manages naming contexts, supporting non-string data
  types and scoped preferences
- **enthought.permissions**: Supports limiting access to parts of an 
  application unless the user is appropriately authorised (not full-blown
  security).
- **enthought.persistence**: Supports pickling the state of a Python object
  to a dictionary, which can then be flexibly applied in restoring the state of
  the object.
- **enthought.preferences**: Manages application preferences.
- **enthought.resource**: Manages application resources such as images and
  sounds.
- **enthought.sweet_pickle**: Handles class-level versioning, to support
  loading of saved data that exist over several generations of internal class
  structures.
- **enthought.template**: Supports creating templatizable object hierarchies.
- **enthought.type_manager**: Manages type extensions, including factories
  to generate adapters, and hooks for methods and functions.
- **enthought.undo**: Supports undoing and scripting application commands.

Prerequisites
-------------
If you want to build AppTools from source, you must first install 
`setuptools <http://pypi.python.org/pypi/setuptools/0.6c8>`_.
"""

from distutils import log
from distutils.command.build import build as distbuild
from pkg_resources import DistributionNotFound, parse_version, require, \
    VersionConflict
from setuptools import setup, find_packages
from setuptools.command.develop import develop
import os
import zipfile

# FIXME: This works around a setuptools bug which gets setup_data.py metadata
# from incorrect packages. Ticket #1592
#from setup_data import INFO
setup_data = dict(__name__='', __file__='setup_data.py')
execfile('setup_data.py', setup_data)
INFO = setup_data['INFO'] 

# Pull the description values for the setup keywords from our file docstring.
DOCLINES = __doc__.split("\n")


class MyDevelop(develop):
    def run(self):
        develop.run(self)
        self.run_command('build_docs')


class MyBuild(distbuild):
    def run(self):
        distbuild.run(self)
        self.run_command('build_docs')


# The actual setup call.
setup(
    author = 'Enthought, Inc.',
    author_email = 'info@enthought.com',
    classifiers = [c.strip() for c in """\
        Development Status :: 5 - Production/Stable
        Intended Audience :: Developers
        Intended Audience :: Science/Research
        License :: OSI Approved :: BSD License
        Operating System :: MacOS
        Operating System :: Microsoft :: Windows
        Operating System :: OS Independent
        Operating System :: POSIX
        Operating System :: Unix
        Programming Language :: Python
        Topic :: Scientific/Engineering
        Topic :: Software Development
        Topic :: Software Development :: Libraries
        """.splitlines() if len(c.strip()) > 0],
    cmdclass = {
        'develop': MyDevelop,
        'build': MyBuild
    },
    dependency_links = [
        'http://code.enthought.com/enstaller/eggs/source',
        ],
    description = DOCLINES[1],
    extras_require = INFO['extras_require'],
    ext_modules = [],
    include_package_data = True,
    install_requires = INFO['install_requires'],
    license = 'BSD',
    long_description = '\n'.join(DOCLINES[3:]),
    maintainer = 'ETS Developers',
    maintainer_email = 'enthought-dev@enthought.com',
    name = 'AppTools',
    namespace_packages = [
        "enthought",
        ],
    packages = find_packages(),
    platforms = ["Windows", "Linux", "Mac OS-X", "Unix", "Solaris"],
    setup_requires = 'setupdocs',
    tests_require = [
        'nose >= 0.10.3',
        ],
    test_suite = 'nose.collector',
    url = 'http://code.enthought.com/projects/app_tools.php',
    version = INFO['version'],
    zip_safe = False,
    )

