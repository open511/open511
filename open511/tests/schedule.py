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

