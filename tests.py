import unittest
import rsvp
import os
import datetime

def testRSVP():
	return rsvp.RSVP(filename='test.json')

class RSVPTest(unittest.TestCase):

	def setUp(self):
		self.rsvp = rsvp.RSVP()
		self.issue_command('rsvp init')
		self.event = self.get_test_event()

	def tearDown(self):
		try:
			os.remove('test.json')
		except OSError:
			pass

	def create_input_message(self, content='', subject='Testing', display_recipient='test-stream', sender_id='12345'):
		return {
			'content': content,
			'subject': subject,
			'display_recipient': display_recipient,
			'sender_id': sender_id
		}

	def issue_command(self, command):
		message = self.create_input_message(content=command)
		return self.rsvp.process_message(message)
		
	def get_test_event(self):
		return self.rsvp.events['test-stream/Testing']




	def test_event_init(self):
		self.assertIn('test-stream/Testing', self.rsvp.events)
		self.assertEqual('12345', self.event['creator'])

	def test_cannot_double_init(self):
		output = self.issue_command('rsvp init')

		self.assertIn('is already an RSVPBot event', output['body'])

	def test_event_cancel(self):
		output = self.issue_command('rsvp cancel')

		self.assertNotIn('test-stream/Testing', self.rsvp.events)
		self.assertIn('has been canceled', output['body'])

	def test_cannot_double_cancel(self):
		self.issue_command('rsvp cancel')

		output = self.issue_command('rsvp cancel')
		self.assertEqual(None, output)

	def test_set_time(self):
		output = self.issue_command('rsvp set time 10:30')

		self.assertIn('has been set to **10:30**', output['body'])
		self.assertEqual('10:30', self.event['time'])

	def test_set_time_fail(self):
		self.issue_command('rsvp init')

		output = self.issue_command('rsvp set time 99:99')

		self.assertIn('is not a valid time', output['body'])
		self.assertNotEqual('99:99', self.event['time'])


	def test_new_event_is_today(self):
		today = str(datetime.date.today())
		self.assertEqual(today, self.event['date'])

	def test_set_date(self):
		future_date = datetime.date.today() + datetime.timedelta(days=1)
		self.issue_command('rsvp set date %02d/%02d/%s' % (future_date.month, future_date.day, future_date.year))
		print self.event
		self.assertEqual(str(future_date), self.event['date'])



if __name__ == '__main__':
    unittest.main()