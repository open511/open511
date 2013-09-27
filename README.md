A simple validator for the [Open511 API](http://www.open511.org/) format.

## Installation

Clone this repository, then run `python setup.py install`

## Usage

    open511-validate filename.xml
    
    open511-validate http://demo.open511.org/api/events/

    open511-convert filename.xml > filename.json

    open511-convert filename.json > filename.xml

# Web interface

A Web interface, available at http://validator.open511.org/, is in open511_validator/web.py. Install the dependencies (listed in requirements.txt, or run `easy_install Flask requests`), then run `python web.py` to start up a local server.