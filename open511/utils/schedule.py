from collections import namedtuple
import datetime
import heapq

from open511.utils import timezone

from open511.utils import memoize_method

Period = namedtuple('Period', 'start end')


def text_to_date(s):
    return datetime.date(*[int(x) for x in s.split('-')]) if s else None

def text_to_time(s):
    return datetime.time(*[int(x) for x in s.split(':')]) if s else None

def _time_text_to_period(t):
    (start, _, end) = t.partition('-')
    return Period(
        text_to_time(start),
        text_to_time(end)
    )

class Schedule(object):
    """
    Class for working with schedule components of an Open511 event.

    The constructor requires two arguments: an lxml Element for the <schedule> tag,
    and a tzinfo object (ideally from pytz) for the timezone of the event.
    """

    def __init__(self, root, timezone):
        assert root.tag == 'schedules'
        self.root = root
        self.timezone = timezone
        self.recurring_schedules = [
            RecurringScheduleComponent(el, timezone)
            for el in root.xpath('schedule')
            if el.xpath('start_date')
        ]

    @property
    @memoize_method
    def specific_dates(self):
        """A dict of dates -> [Period time tuples] representing exceptions
        to the base recurrence pattern."""
        ex = {}
        for sd in self.root.xpath('schedule/specific_dates/specific_date'):
            bits = unicode(sd.text).split(' ')
            date = text_to_date(bits.pop(0))
            ex.setdefault(date, []).extend([
                _time_text_to_period(t)
                for t in bits
            ])
        return ex

    def specific_dates_periods(self, range_start=datetime.date.min, range_end=datetime.date.max):
        """Returns a list of Period tuples for each period represented in a <specific_dates>
        schedule that falls between range_start and range_end."""
        periods = []
        for exception_date, exception_times in self.specific_dates.iteritems():
            if exception_date >= range_start and exception_date <= range_end:
                for exception_time in exception_times:
                    periods.append(
                        Period(
                            self.timezone.localize(datetime.datetime.combine(exception_date, exception_time.start)),
                            self.timezone.localize(datetime.datetime.combine(exception_date, exception_time.end))
                        )
                    )

        periods.sort()
        return periods        

    def to_timezone(self, dt):
        """Converts a datetime to the timezone of this Schedule."""
        if timezone.is_aware(dt):
            return dt.astimezone(self.timezone)
        else:
            return timezone.make_aware(dt, self.timezone)

    def includes(self, query):
        """Does this schedule include the provided time?
        query should be a datetime (naive or timezone-aware)"""
        query = self.to_timezone(query)
        query_date = query.date()
        query_time = query.time()

        # Is the provided time an exception for this schedule?
        specific = self.specific_dates.get(query_date)
        if specific is not None:
            if not query_time:
                return True
            for period in specific:
                if query_time >= period.start and query_time <= period.end:
                    return True

        # It's not an exception. Is it within a recurring schedule?
        return any(sched.includes(query_date, query_time) for sched in self.recurring_schedules)

    def active_within_range(self, query_start, query_end):
        """Is this event ever active between query_start and query_end,
        which are (aware or naive) datetimes?"""

        query_start = self.to_timezone(query_start)
        query_end = self.to_timezone(query_end)

        for range in self.daily_periods(range_start=query_start.date(), range_end=query_end.date()):
            if (
                    ((range.start < query_start) and (range.end > query_end))
                    or (query_start <= range.start <= query_end)
                    or (query_start <= range.end <= query_end)):
                return True
        return False

    def has_remaining_periods(self, after=None):
        """Is this schedule ever in effect at or after the given time?
        If no time is given, uses the current time."""
        if after is None:
            after = timezone.now()
        after = self.to_timezone(after)
        periods = self.daily_periods(range_start=after.date())
        return any(p for p in periods if p.end > after)

    def next_period(self, after=None):
        """Returns the next Period this event is in effect, or None if the event
        has no remaining periods."""
        if after is None:
            after = timezone.now()
        after = self.to_timezone(after)
        return next((p for p in self.periods(range_start=after.date()) if p.end > after), None)

    def daily_periods(self, range_start=datetime.date.min, range_end=datetime.date.max):
        """Returns an iterator of Period tuples for every day this event is in effect, between range_start
        and range_end."""
        specific = set(self.specific_dates.keys())

        return heapq.merge(self.specific_dates_periods(range_start, range_end), *[
            sched.daily_periods(range_start=range_start, range_end=range_end, exclude_dates=specific)
            for sched in self.recurring_schedules
        ])

    def periods(self, range_start=datetime.date.min,
            range_end=datetime.date.max, max_continuous_days=60):
        """Returns an iterator of Period tuples for continuous stretches of time during
        which this event is in effect, between range_start and range_end.

        daily_periods returns one (or more) Period per day; if this event is continuously
        in effect for several days, this method will return a single Period for that time.
        However, Periods will be broken apart after max_continuous_days. This is because
        the algorithm currently works day-by-day, and so the algorithm would become (nearly)
        infinitely slow for events without an end date."""

        current_period = None

        for period in self.daily_periods(range_start, range_end):
            if current_period is None:
                current_period = period
            else:
                if ( ((period.start < current_period.end)
                        or (period.start - current_period.end) <= datetime.timedelta(minutes=1))
                        and (current_period.end - current_period.start) < datetime.timedelta(days=max_continuous_days)):
                    # Merge
                    current_period = Period(current_period.start, period.end)
                else:
                    yield current_period
                    current_period = period
        if current_period:
            yield current_period


class RecurringScheduleComponent(object):

    def __init__(self, root, timezone):
        assert root.tag == 'schedule'
        self.root = root
        self.timezone = timezone

    def includes(self, query_date, query_time):
        """Does this schedule include the provided time?
        query_date and query_time are date and time objects, interpreted
        in this schedule's timezone"""

        if self.start_date and query_date < self.start_date:
            return False
        if self.end_date and query_date > self.end_date:
            return False
        if query_date.weekday() not in self.weekdays:
            return False

        if not query_time:
            return True

        if query_time >= self.period.start and query_time <= self.period.end:
            return True

        return False

    def daily_periods(self, range_start=datetime.date.min, range_end=datetime.date.max, exclude_dates=tuple()):
        """Returns an iterator of Period tuples for every day this schedule is in effect, between range_start
        and range_end."""
        tz = self.timezone
        period = self.period
        weekdays = self.weekdays

        current_date = max(range_start, self.start_date)
        end_date = range_end
        if self.end_date:
            end_date = min(end_date, self.end_date)

        while current_date <= end_date:
            if current_date.weekday() in weekdays and current_date not in exclude_dates:
                yield Period(
                    tz.localize(datetime.datetime.combine(current_date, period.start)),
                    tz.localize(datetime.datetime.combine(current_date, period.end)) 
                )
            current_date += datetime.timedelta(days=1)

    @property
    @memoize_method
    def period(self):
        """A Period tuple representing the daily start and end time."""
        start_time = self.root.findtext('start_time')
        if start_time:
            return Period(text_to_time(start_time), text_to_time(self.root.findtext('end_time')))
        return Period(datetime.time(0, 0), datetime.time(23, 59))

    @property
    def weekdays(self):
        """A set of integers representing the weekdays the schedule recurs on,
        with Monday = 0 and Sunday = 6."""
        if not self.root.xpath('days'):
            return set(range(7))
        return set(int(d) - 1 for d in self.root.xpath('days/day/text()'))

    @property
    @memoize_method
    def start_date(self):
        """Start date of event recurrence, as datetime.date or None."""
        return text_to_date(self.root.findtext('start_date'))

    @property
    @memoize_method
    def end_date(self):
        """End date of event recurrence, as datetime.date or None."""
        return text_to_date(self.root.findtext('end_date'))        
