Some utilities for the [Open511 API](http://www.open511.org/) format. Includes a validator, a tool to convert between Open511 serializations, a Web interface for validation and conversion, and some utility/parsing code.

[![Build Status](https://travis-ci.org/opennorth/open511.png)](https://travis-ci.org/opennorth/open511)

## Installation

Clone this repository, then run `python setup.py install`

## Usage

    open511-validate filename.xml
    
    open511-validate http://demo.open511.org/api/events/

    open511-convert filename.xml > filename.json

    open511-convert filename.json > filename.xml

# Web interface

A Web interface, available at http://validator.open511.org/, is in open511/webtools/__init__.py. Install the dependencies (listed in requirements.txt, or run `easy_install Flask requests`), then run `python open511/webtools/__init__.py` to start up a local server.