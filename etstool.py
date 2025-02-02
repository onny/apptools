# (C) Copyright 2005-2022 Enthought, Inc., Austin, TX
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in LICENSE.txt and may be redistributed only under
# the conditions described in the aforementioned license. The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
#
# Thanks for using Enthought open source!
"""
Tasks for Test Runs
===================

This file is intended to be used with a python environment with the
click library to automate the process of setting up test environments
and running the test within them.  This improves repeatability and
reliability of tests be removing many of the variables around the
developer's particular Python environment.  Test environment setup and
package management is performed using `EDM
<http://docs.enthought.com/edm/>`_

To use this to run you tests, you will need to install EDM and click
into your working environment.  You will also need to have git
installed to access required source code from github repositories.
You can then do::

    python etstool.py install --runtime=...

to create a test environment from the current codebase and::

    python etstool.py test --runtime=...

to run tests in that environment.  You can remove the environment with::

    python etstool.py cleanup --runtime=...

If you make changes you will either need to remove and re-install the
environment or manually update the environment using ``edm``, as
the install performs a ``python setup.py install`` rather than a ``develop``,
so changes in your code will not be automatically mirrored in the test
environment.  You can update with a command like::

    edm run --environment ... -- python setup.py install

You can run all three tasks at once with::

    python etstool.py test_clean --runtime=...

which will create, install, run tests, and then clean-up the environment.  And
you can run tests in all supported runtimes::

    python etstool.py test_all

Currently supported runtime value is``3.6``.  Not all
runtimes will work, but the tasks will fail with a clear error if that is the
case.

Tests can still be run via the usual means in other environments if that suits
a developer's purpose.

Changing This File
------------------

To change the packages installed during a test run, change the dependencies
variable below.  To install a package from github, or one which is not yet
available via EDM, add it to the `ci-src-requirements.txt` file (these will be
installed by `pip`).

Other changes to commands should be a straightforward change to the listed
commands for each task. See the EDM documentation for more information about
how to run commands within an EDM enviornment.

Build changelog
---------------

To create a first-cut changelog from the news fragments, use this command::

    python etstool.py changelog build

This will update the changelog file. You should review and edit it.
"""

import glob
import os
import subprocess
import sys
from shutil import rmtree, copy as copyfile
from tempfile import mkdtemp
from contextlib import contextmanager

import click

DEFAULT_RUNTIME = "3.6"

supported_runtimes = [
    '3.6',
]

dependencies = {
    "flake8",
    "flake8_ets",
    "traitsui",
    "configobj",
    "coverage",
    "importlib_resources>=1.1.0",
    "pytables",
    "pandas",
    "pyface",
    "enthought_sphinx_theme",
    "sphinx",
}


# Dependencies we install from source for cron tests
source_dependencies = {
    "pyface",
    "traits",
    "traitsui",
}


github_url_fmt = "git+http://github.com/enthought/{0}.git#egg={0}"


# Location of documentation files
HERE = os.path.dirname(__file__)
DOCS_DIR = os.path.join(HERE, "docs")

# Location of news fragment for creating changelog.
NEWS_FRAGMENT_DIR = os.path.join(DOCS_DIR, "releases", "upcoming")

# Location of the Changelog file.
CHANGELOG_PATH = os.path.join(HERE, "CHANGES.txt")


@click.group()
def cli():
    pass


@cli.command()
@click.option('--runtime', default=DEFAULT_RUNTIME)
@click.option('--environment', default=None)
@click.option(
    "--source/--no-source",
    default=False,
    help="Install ETS packages from source",
)
def install(runtime, environment, source):
    """ Install project and dependencies into a clean EDM environment.

    """
    parameters = get_parameters(runtime, environment)
    packages = ' '.join(dependencies)
    # edm commands to setup the development environment
    commands = [
        "edm environments create {environment} --force --version={runtime}",
        "edm install -y -e {environment} " + packages,
        "edm run -e {environment} -- pip install -r ci-src-requirements.txt"
        " --no-dependencies",
        "edm run -e {environment} -- python setup.py clean --all",
        "edm run -e {environment} -- python setup.py develop"
    ]
    # pip install pyqt5 and pyside2, because we don't have them in EDM yet

    click.echo("Creating environment '{environment}'".format(**parameters))
    execute(commands, parameters)

    if source:
        # Remove EDM ETS packages and install them from source
        cmd_fmt = (
            "edm plumbing remove-package "
            "--environment {environment} --force "
        )
        commands = [cmd_fmt + source_pkg for source_pkg in source_dependencies]
        execute(commands, parameters)
        source_pkgs = [
            github_url_fmt.format(pkg) for pkg in source_dependencies
        ]
        commands = [
            "python -m pip install {pkg} --no-deps".format(pkg=pkg)
            for pkg in source_pkgs
        ]
        commands = [
            "edm run -e {environment} -- " + command for command in commands
        ]
        execute(commands, parameters)
    click.echo('Done install')


@cli.command()
@click.option('--runtime', default=DEFAULT_RUNTIME)
@click.option('--environment', default=None)
def test(runtime, environment):
    """ Run the test suite in a given environment.

    """
    parameters = get_parameters(runtime, environment)
    environ = {}
    environ['PYTHONUNBUFFERED'] = "1"
    commands = [
        "edm run -e {environment} -- python -W default -m coverage run -p -m "
        "unittest discover -v apptools"
    ]

    # We run in a tempdir to avoid accidentally picking up wrong apptools
    # code from a local dir.  We need to ensure a good .coveragerc is in
    # that directory, plus coverage has a bug that means a non-local coverage
    # file doesn't get populated correctly.
    click.echo("Running tests in '{environment}'".format(**parameters))
    with do_in_tempdir(files=['.coveragerc'], capture_files=['./.coverage*']):
        os.environ.update(environ)
        execute(commands, parameters)
    click.echo('Done test')


@cli.command()
@click.option('--runtime', default=DEFAULT_RUNTIME)
@click.option('--environment', default=None)
def docs(runtime, environment):
    """ Build HTML documentation. """

    parameters = get_parameters(runtime, environment)
    parameters["docs_source"] = "docs/source"
    parameters["docs_build"] = "docs/build"
    parameters["docs_source_api"] = "docs/source/api"
    parameters["docs_api_templates"] = "docs/source/api/templates"

    apidoc_command = (
        "edm run -e {environment} -- python -m sphinx.ext.apidoc "
        "--separate --no-toc -o {docs_source_api} -t {docs_api_templates} "
        "apptools */tests"
    )
    html_build_command = (
        "edm run -e {environment} -- python -m sphinx -b html "
        "{docs_source} {docs_build}"
    )

    commands = [apidoc_command, html_build_command]
    execute(commands, parameters)


@cli.command()
@click.option('--runtime', default=DEFAULT_RUNTIME)
@click.option('--environment', default=None)
def cleanup(runtime, environment):
    """ Remove a development environment.

    """
    parameters = get_parameters(runtime, environment)
    commands = [
        "edm run -e {environment} -- python setup.py clean",
        "edm environments remove {environment} --purge -y"]
    click.echo("Cleaning up environment '{environment}'".format(**parameters))
    execute(commands, parameters)
    click.echo('Done cleanup')


@cli.command()
@click.option('--runtime', default=DEFAULT_RUNTIME)
@click.option('--environment', default=None)
def flake8(runtime, environment):
    """ Run a flake8 check in a given environment.

    """
    parameters = get_parameters(runtime, environment)
    targets = [
        "apptools",
        "docs",
        "etstool.py",
        "setup.py",
        "examples",
        "integrationtests",
    ]
    commands = [
        "edm run -e {environment} -- python -m flake8 " + " ".join(targets)
    ]
    execute(commands, parameters)


@cli.command(name='test-clean')
@click.option('--runtime', default=DEFAULT_RUNTIME)
def test_clean(runtime):
    """ Run tests in a clean environment, cleaning up afterwards

    """
    args = ['--runtime={}'.format(runtime)]
    try:
        install(args=args, standalone_mode=False)
        test(args=args, standalone_mode=False)
    finally:
        cleanup(args=args, standalone_mode=False)


@cli.command()
@click.option('--runtime', default=DEFAULT_RUNTIME)
@click.option('--environment', default=None)
def update(runtime, environment):
    """ Update/Reinstall package into environment.

    """
    parameters = get_parameters(runtime, environment)
    commands = [
        "edm run -e {environment} -- python setup.py install"]
    click.echo("Re-installing in  '{environment}'".format(**parameters))
    execute(commands, parameters)
    click.echo('Done update')


@cli.command(name='test-all')
def test_all():
    """ Run test_clean across all supported runtimes.

    """
    failed_command = False
    for runtime in supported_runtimes:
        args = [
            '--runtime={}'.format(runtime)
        ]
        try:
            test_clean(args, standalone_mode=True)
        except SystemExit:
            failed_command = True
    if failed_command:
        sys.exit(1)


@cli.group("changelog")
@click.pass_context
def changelog(ctx):
    """ Group of commands related to creating changelog."""

    ctx.obj = {
        # Mapping from news fragment type to their description in
        # the changelog.
        "type_to_description": {
            "feature": "Features",
            "bugfix": "Fixes",
            "deprecation": "Deprecations",
            "removal": "Removals",
            "doc": "Documentation changes",
            "test": "Test suite",
            "build": "Build System",
        }
    }


@changelog.command("create")
@click.pass_context
def create_news_fragment(ctx):
    """ Create a news fragment for your PR."""

    pr_number = click.prompt('Please enter the PR number', type=int)
    type_ = click.prompt(
        "Choose a fragment type:",
        type=click.Choice(ctx.obj["type_to_description"])
    )

    filepath = os.path.join(
        NEWS_FRAGMENT_DIR, f"{pr_number}.{type_}.rst"
    )

    if os.path.exists(filepath):
        click.echo("FAILED: File {} already exists.".format(filepath))
        ctx.exit(1)

    content = click.prompt(
        "Describe the changes to the END USERS.\n"
        "Example: 'Remove subpackage xyz.'\n",
        type=str,
    )
    if not os.path.exists(NEWS_FRAGMENT_DIR):
        os.makedirs(NEWS_FRAGMENT_DIR)
    with open(filepath, "w", encoding="utf-8") as fp:
        fp.write(content + f" (#{pr_number})")

    click.echo("Please commit the file created at: {}".format(filepath))


@changelog.command("build")
@click.pass_context
def build_changelog(ctx):
    """ Build Changelog created from all the news fragments."""
    # This is a rather simple first-cut generation of the changelog.
    # It removes the laborious concatenation, but the end results might
    # still require some tweaking.
    contents = []

    # Collect news fragment files as we go, and then optionally remove them.
    handled_file_paths = []

    for type_, description in ctx.obj["type_to_description"].items():
        pattern = os.path.join(NEWS_FRAGMENT_DIR, f"*.{type_}.rst")
        file_paths = sorted(glob.glob(pattern))

        if file_paths:
            contents.append("")
            contents.append(description)
            contents.append("-" * len(description))

        for filename in file_paths:
            with open(filename, "r", encoding="utf-8") as fp:
                contents.append("* " + fp.read())
            handled_file_paths.append(filename)

    # Prepend content to the changelog file.

    with open(CHANGELOG_PATH, "r", encoding="utf-8") as fp:
        original_changelog = fp.read()

    with open(CHANGELOG_PATH, "w", encoding="utf-8") as fp:
        if contents:
            print(*contents, sep="\n", file=fp)
        fp.write(original_changelog)

    click.echo(f"Changelog is updated. Please review it at {CHANGELOG_PATH}")

    # Optionally clean up collected news fragments.
    should_clean = click.confirm(
        "Do you want to remove the news fragments?"
    )
    if should_clean:
        for file_path in handled_file_paths:
            os.remove(file_path)

        # Report any leftover for developers to inspect.
        leftovers = sorted(glob.glob(os.path.join(NEWS_FRAGMENT_DIR, "*")))
        if leftovers:
            click.echo("These files are not collected:")
            click.echo("\n  ".join([""] + leftovers))

    click.echo("Done")


# ----------------------------------------------------------------------------
# Utility routines
# ----------------------------------------------------------------------------


def get_parameters(runtime, environment):
    """ Set up parameters dictionary for format() substitution """
    parameters = {'runtime': runtime, 'environment': environment}
    if environment is None:
        parameters['environment'] = 'apptools-test-{runtime}'.format(
            **parameters
        )
    return parameters


@contextmanager
def do_in_tempdir(files=(), capture_files=()):
    """ Create a temporary directory, cleaning up after done.

    Creates the temporary directory, and changes into it.  On exit returns to
    original directory and removes temporary dir.

    Parameters
    ----------
    files : sequence of filenames
        Files to be copied across to temporary directory.
    capture_files : sequence of filenames
        Files to be copied back from temporary directory.
    """
    path = mkdtemp()
    old_path = os.getcwd()

    # send across any files we need
    for filepath in files:
        click.echo('copying file to tempdir: {}'.format(filepath))
        copyfile(filepath, path)

    os.chdir(path)
    try:
        yield path
        # retrieve any result files we want
        for pattern in capture_files:
            for filepath in glob.iglob(pattern):
                click.echo('copying file back: {}'.format(filepath))
                copyfile(filepath, old_path)
    finally:
        os.chdir(old_path)
        rmtree(path)


def execute(commands, parameters):
    for command in commands:
        click.echo("[EXECUTING] {}".format(command.format(**parameters)))
        try:
            subprocess.check_call([arg.format(**parameters)
                                   for arg in command.split()])
        except subprocess.CalledProcessError as exc:
            click.echo(str(exc))
            sys.exit(1)


if __name__ == '__main__':
    cli()
