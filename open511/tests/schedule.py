import datetime
from unittest import TestCase

from lxml import etree
import pytz

from open511.utils.schedule import Schedule

class BaseScheduleTest(TestCase):

    tzname = 'America/Montreal'

    def setUp(self):
        self.timezone = pytz.timezone(self.tzname)
        self.elem = etree.fromstring(self.data)
        assert self.elem.tag == 'schedules'
        self.sched = Schedule(self.elem, self.timezone)

class SimpleScheduleTest(BaseScheduleTest):

    data = """<schedules>
<schedule>
    <start_date>2013-01-01</start_date>
</schedule></schedules>"""
    
    def test_basics(self):
        sc = self.sched
        assert sc.specific_dates == {}
        assert sc.has_remaining_periods()
        n = sc.next_period(after=datetime.datetime(2014,1,1,10,30))
        self.assertEquals(n.start.date(), datetime.date(2014,1,1))
        self.assertEquals(n.end.date(), datetime.date(2014,3,2))
        assert sc.includes(datetime.datetime.now())


class AncientScheduleTest(BaseScheduleTest):

    data = """<schedules><schedule><start_date>2010-01-01</start_date><end_date>2010-02-01</end_date></schedule></schedules>"""

    def test_not_current(self):
        assert not self.sched.has_remaining_periods()
        assert not list(self.sched.daily_periods(range_start=datetime.date.today()))
        assert self.sched.next_period() is None
        assert not self.sched.includes(datetime.datetime.now())

class FutureScheduleTest(BaseScheduleTest):

    data = """<schedules><schedule><start_date>2050-01-01</start_date><end_date>2050-02-01</end_date></schedule></schedules>"""

    def test_not_now(self):
        sc = self.sched
        assert sc.has_remaining_periods()
        assert sc.next_period().start.date() == datetime.date(2050,1,1)
        assert not sc.includes(datetime.datetime.now())

class SpecificDatesScheduleTest(BaseScheduleTest):
    data = """<schedules><schedule><start_date>2010-01-01</start_date></schedule><schedule><specific_dates><specific_date>2010-01-02 09:00-10:00 11:00-12:00</specific_date><specific_date>%s</specific_date></specific_dates></schedule></schedules>
        """ % datetime.date.today()

    def test_not_now(self):
        sc = self.sched
        assert sc.has_remaining_periods()
        assert sc.next_period().start.date() == datetime.date.today() + datetime.timedelta(days=1)
        assert not sc.includes(datetime.datetime.now())
        assert sc.includes(datetime.datetime.now() + datetime.timedelta(days=1))
        assert not sc.active_within_range(datetime.datetime.now(), datetime.datetime.now() + datetime.timedelta(seconds=1))
        assert sc.active_within_range(datetime.datetime.now(), datetime.datetime.now() + datetime.timedelta(days=1))

        assert sc.includes(datetime.datetime(2010,1,2,9,30))
        assert not sc.includes(datetime.datetime(2010,1,2,10,30))
        assert not sc.active_within_range(datetime.datetime(2010,1,2,14,0), datetime.datetime(2010,1,2,15,0))
        assert sc.active_within_range(datetime.datetime(2010,1,2,8,0), datetime.datetime(2010,1,2,9,30))
        assert sc.active_within_range(datetime.datetime(2010,1,2,8,0), datetime.datetime(2010,1,2,12,30))
        assert sc.active_within_range(datetime.datetime(2010,1,2,9,30), datetime.datetime(2010,1,2,12,0))
        assert sc.active_within_range(datetime.datetime(2010,1,2,9,30), datetime.datetime(2010,1,2,9,40))
        assert sc.next_period(datetime.datetime(2010,1,2,8,30)).end.time() == datetime.time(10,0)



