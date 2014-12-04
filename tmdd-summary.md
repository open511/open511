# TMDD Converter Summary

This module attempts to convert data from the [Traffic Management Data Dictionary](http://www.ite.org/standards/tmdd/) XML serialization to Open511, in XML or JSON.

Either the [web-based](http://validator.open511.org/) or commandline (`open511-convert`) converters should be able to process TMDD data. However, because TMDD is an exceedingly large format and most users use a small, custom subset, it is quite possible that the converter won't work on data from a source we haven't previously tested with. If that's the case for you, please get in touch!

The following is a brief description of the conversion algorithm and data sources.

### Event model

Every TMDD `FEU/event-element-details/event-element-detail` is mapped to an Open511 event. This means that a single TMDD `FEU` can be split into multiple Open511 events.

### Status

If the TMDD `active_flag` is `no`, uses Open511 `ARCHIVED`. Otherwise, the event is labelled as active.

### Created & updated timestamps

Uses TMDD `event-reference/update-time`.

### Headline

Uses TMDD `event-name`. If not provided, generates a simple headline based on the event type and, if present, the road name.

### Description

Uses the concatenated values of TMDD `event-descriptions/event-description/additional-text/description`. If not available, uses TMDD `full-report-texts/description`.

### Roads

Loops through every TMDD `event-locations/event-location/locations-on-link` to search for road data.

Draws road names from TMDD `link-name` or `primary-location/link-name`.

Draws "from"/"nearby" text for the road from TMDD `primary-location/cross-street-name/cross-street-name-item` or `primary-location/linear-reference`.

If TMDD provides a `secondary-location` in `location-on-link`, checks if the secondary location's `link-name` matches that of the primary location. If it does, and the secondary location also provides a `cross-street-name`, puts that cross street name in the Open511 "to" value for that road. If the secondary location's name differs from the primary location, adds that `link-name` as a new Open511 road entry.

Road direction comes from TMDD `link-direction`.

Attempts to convert lane data from TMDD `event-lanes`, but mismatches between the TMDD and Open511 data models for this data make this a difficult task in many cases. Lane data will be converted if:

* The TMDD road data converts to a single Open511 <road>
* The lane data concerns only a single direction of the road
* Each TMDD `event-lane` provides `lane-status`, `lanes-total-affected`, and `lanes-total-original`

### Geography

Geospatial points are assembled from TMDD `event-locations/event-location/location-on-link/primary-location/geo-location`, `event-locations/event-location/location-on-link/secondary-location/geo-location`, and `event-locations/event-location/geo-location`. The Open511 value will be either a Point or a MultiPoint.

### Severity

Collects all `event-indicator/event-severity` values, and all `event-indicator/event-impact` values. TMDD severities of `none` or `minor` become Open511 `MINOR`, `major` and `natural-disaster` become `MAJOR`, and `none` becomes `UNKNOWN`. TMDD impacts of 0 become `UNKNOWN`, 1-3 become `MINOR`, 4-7 become `MODERATE`, and 7-10 `MAJOR`. If more than one severity/impact is found, the highest value becomes the Open511 severity.

### Event type

Uses `event-indicators/event-indicator/planned-event-class`. `other` is converted to Open511 `SPECIAL_EVENT`.

### Jurisdiction

Must be provided as a configuration value to the converter. The converter requires the `OPEN511_JURISDICTION_URL`, `OPEN511_JURISDICTION_ID`, and `OPEN511_EVENTS_URL` environment variables; it uses dummy example data if the environment variables are not present.

### Schedule

Currently, only supports simple schedules with a start time and, optionally, an end time.

The start time is drawn from the first available among `event-times/start-time`, `event-times/expected-start-time`, `event-times/alternate-start-time`, `event-times/update-time`, `event-reference/update-time`. The end time is drawn from the first available among `event-times/expected-end-time`, `event-times/valid-period/expected-end-time`, and `event-times/alternate-end-time`.

### Event subtypes

Draws from TMDD `event-headline/headline/accidents-and-incidents` to see if Open511's `ACCIDENT` or `SPILL` are warranted.

### Certainty

Drawn from TMDD `confidence-level`. TMDD values are converted into 1-10, according to their order in the TMDD enumeration. 1 becomes Open511 `POSSIBLE`, 2-4 `LIKELY`, 5-10 `OBSERVED`.

### Grouped events

Drawn from TMDD 'responsible-event', 'related-event', 'merged-event', and 'sibling-event', as well as Open511 events split from a single TMDD event (see "Event model"). Assumes server uses the best-practice, but not officially required, URL layout of Open North's Open511 server.

### Detour

TMDD's highly complex structure would need to go through a natural-language-generation algorithm to convert this into the Open511 free-text field. Since none of our sample source data used this TMDD field, we have not yet implemented this.



