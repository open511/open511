Some utilities for the [Open511 API](http://www.open511.org/) format. Includes a validator, a tool to convert between Open511 serializations, a Web interface for validation and conversion, and some utility/parsing code.

[![Build Status](https://travis-ci.org/opennorth/open511.png)](https://travis-ci.org/opennorth/open511)

## Requirements

Python 2.7 or 3.4, libxml2. Linux or MacOS. (It might work on Windows, but hasn't been tested. We'd be happy to work with anyone interested in running this on Windows.)

## Installation

This package is a Python application. The current best practice is to install into an isolated Python environment, created with the `virtualenv` package for Python 2, or `pyvenv` for Python 3. Things should still work if you don't create an environment, but you may need to run the setup commands below as root.

Clone this repository, then run `python setup.py install`. Or, to install the latest released version, run `easy_install open511`.

## Usage

    open511-validate filename.xml
    
    open511-validate http://demo.open511.org/api/events/

    open511-convert --help

    open511-convert filename.xml > filename.json

    open511-convert filename.json > filename.xml

## Conversions

Available output formats: Open511 JSON (`json`), Open511 XML (`xml`), [MASAS](https://www.masas-x.ca/en/)-compatible Atom (`atom`), [KML](https://developers.google.com/kml/) (`kml`)

Input formats: Open511 XML or JSON, and [Traffic Management Data Dictionary](http://www.ite.org/standards/tmdd/) (TMDD) XML

You can convert from any input format to any output format, e.g. `open511-convert input.tmdd -f kml output.kml`

## TMDD

Due to the size and complexity of the TMDD specification, some input files may not be supported. Please contact us if you have problems with a particular TMDD input file, and we'll try to get it working!

To produce production-ready Open511 XML from TMDD, you need to specify provide some information on your Open511 deployment via environment variables. Set `OPEN511_EVENTS_URL` to the URL to your Open511 events endpoint, `OPEN511_JURISDICTION_URL` to the URL of the appropriate Open511 jurisdiction resource, and `OPEN511_JURISDICTION_ID` to the Open511 ID of your jurisdiction. If these are not set, example values will be used.

More details on the conversion algorithm is in [docs](docs).

# Web interface

A Web interface, available at http://validator.open511.org/, is in open511/webtools/__init__.py. Install the dependencies (listed in requirements.txt, or run `easy_install Flask requests`), then run `python open511/webtools/__init__.py` to start up a local server.
