#!/usr/bin/python
# -*- coding: latin-1 -*-

__author__ = 'anton.doxid@gmail.com'
__credit__ = 'api.rboyd@gmail.com (Ryan Boyd)', 'http://code.google.com/p/gdata-python-client/source/browse/samples/calendar/calendarExample.py'

import gdata.calendar.data
import gdata.calendar.client
import gdata.acl.data
import sys, time, re, pynotify

sys.setdefaultencoding('latin-1')

def swe(s):
	if s:
		s = s.decode('utf-8', 'ignore')
	return s

def cleanDate(s):
	return re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2}", s)[0]

def strftotime(s):
	return time.mktime(time.strptime(cleanDate(s), "%Y-%m-%d"))

def accountofmail(s):
	return s.split('@',1)[0]

def getmail(s):
	return re.findall('[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{1,4}', s)[0]

class Calendar:
	def __init__(self, email, password):
		self.cal_client = gdata.calendar.client.CalendarClient(source='Google-Calendar_Python_Sample-1.0')
		self.cal_client.ClientLogin(email, password, self.cal_client.source);

		self.allcalendars = self.cal_client.GetAllCalendarsFeed()
		self.user = self.allcalendars.title.text

	def getReminders(self):
		start_date = time.strftime('%Y-%m-%d')#'2001-01-01'
		end_date = '2013-01-30'
		weekday = time.strftime("%a")

		nextsunday = 86401
		if weekday.lower() == 'sunday':
			weekday = time.strftime("%a", time.localtime(time.time()+nextsunday))

		while weekday.lower() != 'sun':
			nextsunday += 28800
			weekday = time.strftime("%a", time.localtime(time.time()+nextsunday))

		end_date = time.strftime("%Y-%m-%d", time.localtime(time.time()+nextsunday))

		query = gdata.calendar.client.CalendarEventQuery(start_min=start_date, start_max=end_date)
		feed = self.cal_client.GetCalendarEventFeed(q=query)
		for i, an_event in zip(xrange(len(feed.entry)), feed.entry):
			for a_when in an_event.when:
				t, s, e = swe(an_event.title.text), a_when.start, a_when.end
				if time.time() - strftotime(s) <= 86400*3: # 3 days
					pynotify.init("CalRem")
					Hello=pynotify.Notification('[' + cleanDate(s) + ']', t)
					Hello.show()

if __name__ == '__main__':
	if len(sys.argv) < 3:
		print 'Requires to be run with: ./calrem.py <g-user> <g-pass>'
	else:
		user, pw = sys.argv[1:3]
		cal = Calendar(user, pw)
		cal.getReminders()