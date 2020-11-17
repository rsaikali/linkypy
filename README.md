# <img src="https://gitlab.com/uploads/-/system/project/avatar/11691930/LogoMakr_8qfVOf.png" alt="Logo" width="50"/> PyLinky

[![pipeline status](https://gitlab.com/roland.saikali/linkypy/badges/master/pipeline.svg)](https://gitlab.com/roland.saikali/linkypy/commits/master)

LinkyPy is intended to grab Linky information trough RaspberryPi USB port.

Data can then be managed through plugins:
  - LoggerPlugin (default): output realtime data on console.
  - InfluxDB plugin: stores data in an InfluxDB plugin.
  - ...

## Usage

Go to project directory:

```
    $ cd linkypy
```

Work on the Python virtual environment with:
```
    $ workon linkypy
```

Launch your client with:
```
    $ linkypy
```

## Tests

Launch your Python tests and PEP8 syntax checking with:
```
    $ tox                # Launch all
    $ tox -e py27        # Launch only Python 2.7 unittests
    $ tox -e py37        # Launch only Python 3.7 unittests
    $ tox -e pep8        # Launch only pep8 checks
```

## Documentation

Generate documentation:
```
    $ tox -e docs
```

Documentation source is available under `doc/source`

Documentation is generated under `doc/build`
