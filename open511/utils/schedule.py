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

def text_to_datetime(s):
    d, _, t = s.partition('T')
    return datetime.datetime.combine(text_to_date(d), text_to_time(t))

def _time_text_to_period(t):
    (start, _, end) = t.partition('-')
    return Period(
        text_to_time(start),
        text_to_time(end)
    )

class Schedule(object):
    """Represent an Open511 <schedule>."""

    def __init__(self):
        raise Exception("Initialize via from_element, not directly")

    @staticmethod
    def from_element(root, timezone):
        """Return a Schedule object based on an lxml Element for the <schedule>
        tag. timezone is a tzinfo object, ideally from pytz."""
        assert root.tag == 'schedule'
        if root.xpath('intervals'):
            return _ScheduleIntervals(root, timezone)
        elif root.xpath('recurring_schedules'):
            return _ScheduleRecurring(root, timezone)
        raise NotImplementedError

    def to_timezone(self, dt):
        """Converts a datetime to the timezone of this Schedule."""
        if timezone.is_aware(dt):
            return dt.astimezone(self.timezone)
        else:
            return timezone.make_aware(dt, self.timezone)

    def intervals(self, range_start=datetime.datetime.min, range_end=datetime.datetime.max):
        """Returns a list of tuples of start/end datetimes for when the schedule
        is active during the provided range."""
        raise NotImplementedError

    def next_interval(self, after=None):
        """Returns the next Period this event is in effect, or None if the event
        has no remaining periods."""
        if after is None:
            after = timezone.now()
        after = self.to_timezone(after)
        return next(self.intervals(range_start=after), None)

    def active_within_range(self, query_start, query_end):
        """Is the event ever active within the given range?"""
        return any(self.intervals(query_start, query_end))

    def includes(self, query):
        """Does this schedule include the provided time?
        query should be a datetime (naive or timezone-aware)"""
        query = self.to_timezone(query)
        return any(self.intervals(range_start=query, range_end=query))

    def has_remaining_intervals(self, after=None):
        """Is this schedule ever in effect at or after the given time?
        If no time is given, uses the current time."""
        return bool(self.next_interval(after))

class _ScheduleIntervals(Schedule):
    """An Open511 <schedule> that uses <intervals>. Create via Schedule.from_element,
    not directly."""

    def __init__(self, root, timezone):
        self.root = root
        self.timezone = timezone
        self._intervals = []
        for interval_data in root.xpath('intervals/interval/text()'):
            start, end = interval_data.split('/')
            period = Period(
                text_to_datetime(start).replace(tzinfo=self.timezone),
                text_to_datetime(end).replace(tzinfo=self.timezone) if end else None
            )
            self._intervals.append(period)
        self._intervals.sort()

    def intervals(self, range_start=datetime.datetime.min, range_end=datetime.datetime.max):
        range_start = self.to_timezone(range_start)
        range_end = self.to_timezone(range_end)

        for period in self._intervals:
            if period.start <= range_end and (period.end is None or period.end >= range_start):
                yield period


class _ScheduleRecurring(Schedule):
    """An Open511 <schedule> that uses <recurring_schedules>. Create via Schedule.from_element,
    not directly."""

    def __init__(self, root, timezone):
        self.root = root
        self.timezone = timezone
        self._recurring_schedules = [
            RecurringScheduleComponent(el, timezone)
            for el in root.xpath('recurring_schedules/recurring_schedule')
        ]

    @property
    @memoize_method
    def exceptions(self):
        """A dict of dates -> [Period time tuples] representing exceptions
        to the base recurrence pattern."""
        ex = {}
        for sd in self.root.xpath('exceptions/exception'):
            bits = str(sd.text).split(' ')
            date = text_to_date(bits.pop(0))
            ex.setdefault(date, []).extend([
                _time_text_to_period(t)
                for t in bits
            ])
        return ex

    def exception_periods(self, range_start=datetime.date.min, range_end=datetime.date.max):
        """Returns a list of Period tuples for each period represented in an <exception>
        that falls between range_start and range_end."""
        periods = []
        for exception_date, exception_times in self.exceptions.items():
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

    def includes(self, query):
        """Does this schedule include the provided time?
        query should be a datetime (naive or timezone-aware)"""
        query = self.to_timezone(query)
        query_date = query.date()
        query_time = query.time()

        # Is the provided time an exception for this schedule?
        specific = self.exceptions.get(query_date)
        if specific is not None:
            if len(specific) == 0:
                # Not in effect on this day
                return False
            for period in specific:
                if query_time >= period.start and query_time <= period.end:
                    return True
            return False

        # It's not an exception. Is it within a recurring schedule?
        return any(sched.includes(query_date, query_time) for sched in self._recurring_schedules)

    def _daily_periods(self, range_start, range_end):
        """Returns an iterator of Period tuples for every day this event is in effect, between range_start
        and range_end."""
        specific = set(self.exceptions.keys())

        return heapq.merge(self.exception_periods(range_start, range_end), *[
            sched.daily_periods(range_start=range_start, range_end=range_end, exclude_dates=specific)
            for sched in self._recurring_schedules
        ])

    def intervals(self, range_start=datetime.datetime.min, range_end=datetime.datetime.max):
        """Returns an iterator of Period tuples for continuous stretches of time during
        which this event is in effect, between range_start and range_end."""

        # At the moment the algorithm works on periods split by calendar day, one at a time,
        # merging them if they're continuous; to avoid looping infinitely for infinitely long
        # periods, it splits periods as soon as they reach 60 days.
        # This algorithm could likely be improved to get rid of this restriction and improve
        # efficiency, so code should not rely on this behaviour.

        current_period = None
        max_continuous_days = 60

        range_start = self.to_timezone(range_start)
        range_end = self.to_timezone(range_end)

        for period in self._daily_periods(range_start.date(), range_end.date()):
            if period.end < range_start or period.start > range_end:
                continue
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
    """Represents an individual <recurring_schedule> within a <schedule>."""

    def __init__(self, root, timezone):
        assert root.tag == 'recurring_schedule'
        self.root = root
        self.timezone = timezone

    def includes(self, query_date, query_time=None):
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
        start_time = self.root.findtext('daily_start_time')
        if start_time:
            return Period(text_to_time(start_time), text_to_time(self.root.findtext('daily_end_time')))
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
