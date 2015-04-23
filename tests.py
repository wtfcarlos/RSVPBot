import unittest
import rsvp
import os
import datetime
from collections import Counter

def testRSVP():
	return rsvp.RSVP(filename='test.json')

class RSVPTest(unittest.TestCase):

	def setUp(self):
		self.rsvp = rsvp.RSVP(filename='test.json')
		self.issue_command('rsvp init')
		self.event = self.get_test_event()

	def tearDown(self):
		try:
			os.remove('test.json')
		except OSError:
			pass

	def create_input_message(self, content='', sender_full_name='Tester', subject='Testing', display_recipient='test-stream', sender_id='12345'):
		return {
			'content': content,
			'subject': subject,
			'display_recipient': display_recipient,
			'sender_id': sender_id,
			'sender_full_name': sender_full_name,
		}

	def issue_command(self, command):
		message = self.create_input_message(content=command)
		return self.rsvp.process_message(message)

	def issue_custom_command(self, command, **kwargs):
		message = self.create_input_message(content=command, **kwargs)
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
		self.assertIn('is not an RSVPBot event', output['body'])


	def test_rsvp_yes_with_no_prior_reservation(self):
		output = self.issue_command('rsvp yes')

		self.assertIn('is  attending!', output['body'])
		self.assertIn('Tester', self.event['yes'])
		self.assertNotIn('Tester', self.event['no'])

	def test_rsvp_no_with_no_prior_reservation(self):
		output = self.issue_command('rsvp no')

		self.assertIn('is **not** attending!', output['body'])
		self.assertNotIn('Tester', self.event['yes'])
		self.assertIn('Tester', self.event['no'])

	def test_rsvp_yes_with_prior_reservation(self):
		self.issue_command('rsvp yes')
		output = self.issue_command('rsvp yes')

		count_dict = Counter(self.event['yes'])

		self.assertEqual(1, count_dict['Tester'])

	def test_rsvp_no_with_prior_cancelation(self):
		self.issue_command('rsvp no')
		output = self.issue_command('rsvp no')

		count_dict = Counter(self.event['no'])

		self.assertEqual(1, count_dict['Tester'])

	def test_set_limit(self):
		output = self.issue_command('rsvp set limit 1')

		self.assertIn('has been set to **1**', output['body'])
		self.assertEqual(1, self.event['limit'])

	def test_cannot_rsvp_on_a_full_event(self):
		self.issue_command('rsvp set limit 1')
		self.issue_command('rsvp yes')
		output = self.issue_custom_command('rsvp yes', sender_full_name='Tester 2')

		self.assertIn('The **limit** for this event has been reached!', output['body'])

	def test_set_date(self):
		output = self.issue_command('rsvp set date 02/25/2100')

		self.assertIn(
			'The date for this event has been set to **02/25/2100**!',
			output['body']
		)

		self.assertEqual(
			'2100-02-25',
			self.event['date']
		)

	def test_set_date(self):
		output = self.issue_command('rsvp set date 02/25/1000')

		self.assertIn(
			'Oops! **02/25/1000** is not a valid date in the **future**!',
			output['body']
		)

		self.assertNotEqual(
			'1000-02-25',
			self.event['date']
		)



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



if __name__ == '__main__':
    unittest.main()