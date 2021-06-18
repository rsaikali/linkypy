.. _devguide:

===============================================
Linky Python reader developer guide
===============================================

'Linky Python reader' (linkypy v0.1.0) is a project created by Roland SAIKALI.

Cookiecutter was used to build this project skeleton.
It is based on open source projects and libraries to help you start with a clean default Python project:

* `click <https://click.palletsprojects.com/en/7.x/>`_ Python library for command line and console scripts.
* `YAML <https://pyyaml.org/wiki/PyYAMLDocumentation>`_ Python library for YAML (used here for easy configuration).
* `daiquiri <https://daiquiri.readthedocs.io/en/latest/>`_ Python library for logging management.

This project is also configured with the following features:

* `tox <https://tox.readthedocs.org/en/latest/>`_ for unittests.
* `pep8 <https://www.python.org/dev/peps/pep-0008/>`_ as a style guide for Python code.
* `coverage <http://coverage.readthedocs.org/en/latest/>`_ for measuring code coverage.
* `Sphinx <http://sphinx-doc.org/>`_ for project documentation.


Working on the project
======================

You can use the automaticaly generated virtualenv, handled via ``virtualenvwrapper``, on which you will find all the Python packages requirements::

    # Go into your project directory
    cd linkypy

    # Work on the generated virtual environment
    workon linkypy

A default ``requirements.txt`` file is also generated for you, with default Python libraries installed.

.. seealso:: Virtualenvwrapper `documentation <https://virtualenvwrapper.readthedocs.org/en/latest/index.html>`_


Launching the default console script
====================================

Cookiecutter also generates a default console script for your project.

You can test the client with the following options:

.. code-block:: shell

    # Help on your console script
    linkypy --help

    # Normal mode with subcommand
    linkypy run

.. seealso::

    Full documentation for `click Python library <https://click.palletsprojects.com/en/7.x/>`_.

Add a new console script
========================

To add a new console script, you will need first to add an entry point in your ``setup.cfg`` file into the ``[entry_points]/console_scripts`` section:

.. code-block:: properties
   :emphasize-lines: 5

    (...)
    [entry_points]
    console_scripts  =
        linkypy = linkypy.console.cli:linkypy
        another-cli  = linkypy.console.newcli:another_cli
    (...)

.. note::

    As you can see, the console script name can be different from the Python module name.

    For readability purposes and to ease comprehension, it is recommended to keep a coherent naming between names.
    Please understand that names choosen here are just for demonstration.

Finally, the following command will create a shell script into your ``virtualenv`` bin directory from the name you gave in the ``[entry_points]/console_scripts``:

.. code-block:: shell

    python setup.py develop

From there, your new console script should be available.

.. seealso::

    Full documentation for `click Python library <https://click.palletsprojects.com/en/7.x/>`_.
    You will also find information on how to handle command line parameters through the ``click`` library.


Handling parameters and configuration file
==========================================

A default configuration file is generated under yout project ``etc/linkypy/linkypy.yaml``

This file is a YAML file, so you can easily structure your different configuration variables.

.. code-block:: yaml

    weather_demo:
        debug: False
        color_of_shirts: indigo
        number_of_shirts: 42

To read this configuration from Python, you can find an example in the console script ``linkypy/console/cli.py``:

.. code-block:: python

    from linkypy import CONF

    (...)
    logger.debug("debug: %s" % CONF.linkypy.debug)
    logger.info("color_of_shirts: %s" % CONF.linkypy.color_of_shirts)
    logger.warn("number_of_shirts: %s" % CONF.linkypy.number_of_shirts)
    (...)

Launching tests and syntax checks
=================================

'Linky Python reader' uses `tox <https://tox.readthedocs.org/en/latest/>`_ for unit testing and PEP syntax checking.
You can launch Python tests and PEP8 syntax checking with:

.. code-block:: shell

    # Launch all tests suites
    tox

    # Launch only python2.7 unittests
    tox -e py27

    # Launch only pep8 checks
    tox -e pep8


Observe tests coverage
======================

Unittests will create a coverage report available in the console output but also in HTML format.

You can watch for unittests coverage with:

.. code-block:: shell

    open doc/build/coverage/index.html

There you can click on each project file to see which lines are tested, and which lines are not tested.


Generating documentation
========================

You can generate the 'Linky Python reader' documentation using the following command:

.. code-block:: shell

    tox -e docs

To look at the documentation:

.. code-block:: shell

    # Project documentation
    open doc/build/html/index.html

    # API documentation
    open doc/build/html/apidoc.html

    # Developer Guide (the one you're currently reading)
    open doc/build/html/devguide.html

Check out :ref:`api-doc` and read the code.
