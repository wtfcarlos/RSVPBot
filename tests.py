from collections import Counter
from datetime import date, timedelta
import os
import unittest

from mock import Mock, patch

import calendar_events
import rsvp
import rsvp_commands
from zulip_users import ZulipUsers


class CalendarEventTest(unittest.TestCase):

    def test_add_to_gcal_with_missing_date_throws_exception(self):
        rsvp_bot_event = {
            u'name': 'Testing',
            u'description': 'A very fun party',
            u'date': None,
            u'time': u'10:30',
            u'duration': 1800,
            u'place': 'Hopper!',
            u'calendar_event': None,
            u'yes': [],
            u'no': [],
            u'maybe': [],
            u'limit': None,
        }

        with self.assertRaises(calendar_events.DateAndTimeNotSuppliedError):
            calendar_events.add_rsvpbot_event_to_gcal(rsvp_bot_event, 'test/test')

    def test_add_to_gcal_with_missing_time_throws_exception(self):
        rsvp_bot_event = {
            u'name': 'Testing',
            u'description': 'A very fun party',
            u'date': '2100-02-25',
            u'time': None,
            u'duration': 1800,
            u'place': 'Hopper!',
            u'calendar_event': None,
            u'yes': [],
            u'no': [],
            u'maybe': [],
            u'limit': None,
        }

        with self.assertRaises(calendar_events.DateAndTimeNotSuppliedError):
            calendar_events.add_rsvpbot_event_to_gcal(rsvp_bot_event, 'test/test')

    def test_add_to_gcal_with_missing_duration_throws_exception(self):
        rsvp_bot_event = {
            u'name': 'Testing',
            u'description': 'A very fun party',
            u'date': '2100-02-25',
            u'time': u'10:30',
            u'duration': None,
            u'place': 'Hopper!',
            u'calendar_event': None,
            u'yes': [],
            u'no': [],
            u'maybe': [],
            u'limit': None,
        }

        with self.assertRaises(calendar_events.DurationNotSuppliedError):
            calendar_events.add_rsvpbot_event_to_gcal(rsvp_bot_event, 'test/test')

    @patch('calendar_events.create_event_on_calendar')
    def test_add_to_calendar_with_slash_in_topic_works(self, mock):
        rsvp_bot_event = {
            u'name': 'Testing',
            u'description': 'A very fun party',
            u'date': '2100-02-25',
            u'time': u'10:30',
            u'duration': 1800,
            u'place': 'Hopper!',
            u'calendar_event': None,
            u'yes': [],
            u'no': [],
            u'maybe': [],
            u'limit': None,
        }

        calendar_events.add_rsvpbot_event_to_gcal(
            rsvp_bot_event,
            '455 Broadway/Practical web app security 6/22')

        event_dict = {
            'start': {
                'timeZone': 'America/New_York',
                'dateTime': '2100-02-25T10:30:00'},
            'end': {
                'timeZone': 'America/New_York',
                'dateTime': '2100-02-25T11:00:00'},
            'location': 'Hopper!',
            'summary': 'Testing',
            'description': 'A very fun party\r\rFor more information or to RSVP, see https://zulip.com#narrow/stream/455.20Broadway/topic/Practical.20web.20app.20security.206.2F22',
            'attendees': [],
        }

        mock.assert_called_once_with(
            event_dict,
            calendar_events.GOOGLE_CALENDAR_ID,
        )

    @patch('calendar_events.create_event_on_calendar')
    def test_add_to_gcal_with_complete_event_works(self, mock):
        rsvp_bot_event = {
            u'name': 'Testing',
            u'description': 'A very fun party',
            u'date': '2100-02-25',
            u'time': u'10:30',
            u'duration': 1800,
            u'place': 'Hopper!',
            u'calendar_event': None,
            u'yes': [],
            u'no': [],
            u'maybe': [],
            u'limit': None,
        }

        calendar_events.add_rsvpbot_event_to_gcal(rsvp_bot_event, 'test/test')

        event_dict = {
            'start': {
                'timeZone': 'America/New_York',
                'dateTime': '2100-02-25T10:30:00'},
            'end': {
                'timeZone': 'America/New_York',
                'dateTime': '2100-02-25T11:00:00'},
            'location': 'Hopper!',
            'summary': 'Testing',
            'description': 'A very fun party\r\rFor more information or to RSVP, see https://zulip.com#narrow/stream/test/topic/test',
            'attendees': [],
        }

        mock.assert_called_once_with(
            event_dict,
            calendar_events.GOOGLE_CALENDAR_ID,
        )


class RSVPTest(unittest.TestCase):

    def setUp(self):
        self.rsvp = rsvp.RSVP('rsvp', filename='test.json')
        self.issue_command('rsvp init')
        self.event = self.get_test_event()

    def tearDown(self):
        try:
            os.remove('test.json')
        except OSError:
            pass

    def create_input_message(
            self,
            content='',
            sender_full_name='Tester',
            subject='Testing',
            display_recipient='test-stream',
            sender_id='12345',
            message_type='stream',
            sender_email='a@example.com'):

        return {
            'content': content,
            'subject': subject,
            'display_recipient': display_recipient,
            'sender_id': sender_id,
            'sender_full_name': sender_full_name,
            'sender_email': sender_email,
            'type': message_type,
        }

    def issue_command(self, command):
        message = self.create_input_message(content=command)
        return self.rsvp.process_message(message)

    def issue_custom_command(self, command, **kwargs):
        message = self.create_input_message(content=command, **kwargs)
        return self.rsvp.process_message(message)

    def get_test_event(self):
        return self.rsvp.events['test-stream/Testing']


class RSVPInitTest(RSVPTest):
    def test_event_init(self):
        self.assertIn('test-stream/Testing', self.rsvp.events)
        self.assertEqual('12345', self.event['creator'])

    def test_cannot_double_init(self):
        output = self.issue_command('rsvp init')

        self.assertIn('is already an RSVPBot event', output[0]['body'])


class RSVPCancelTest(RSVPTest):
    def test_event_cancel(self):
        output = self.issue_command('rsvp cancel')

        self.assertNotIn('test-stream/Testing', self.rsvp.events)
        self.assertIn('has been canceled', output[0]['body'])

    def test_cannot_double_cancel(self):
        self.issue_command('rsvp cancel')

        output = self.issue_command('rsvp cancel')
        self.assertIn('is not an RSVPBot event', output[0]['body'])


class RSVPMoveTest(RSVPTest):
    def test_move_event(self):
        output = self.issue_command('rsvp move http://testhost/#narrow/stream/test-move/subject/MovedTo')

        # current stream is no longer an event
        self.assertNotIn('test-stream/Testing', self.rsvp.events)
        self.assertEqual(2, len(output))

        self.assertIn("This event has been moved to [test-move/MovedTo]", output[0]['body'])
        self.assertIn("#narrow/stream/test-move/subject/MovedTo", output[0]['body'])
        self.assertIn("test-stream", output[0]['display_recipient'])
        self.assertIn("Testing", output[0]['subject'])

        # moved to IS now an event & was told so.
        self.assertIn('test-move/MovedTo', self.rsvp.events)
        self.assertIn("This thread is now an RSVPBot event! Type `rsvp help` for more options.", output[1]['body'])
        self.assertIn("test-move", output[1]['display_recipient'])
        self.assertIn("MovedTo", output[1]['subject'])

    def test_move_to_already_existing_event(self):
        self.issue_command('rsvp init')
        output = self.issue_command('rsvp move http://testhost/#narrow/stream/test-stream/subject/Testing')

        #attempted move to thread that's already an event (in this case, self)
        self.assertEqual(1, len(output))
        self.assertIn('test-stream/Testing', self.rsvp.events)
        self.assertIn("Oops! `test-stream/Testing` is already an RSVPBot event", output[0]['body'])
        self.assertIn("test-stream", output[0]['display_recipient'])
        self.assertIn("Testing", output[0]['subject'])


class RSVPDecisionTest(RSVPTest):

    event_id = 'Test/Test'

    def test_generate_response_yes(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        response = command.generate_response(decision='yes', event_id=self.event_id)
        self.assertEqual("**You** are attending **{}**!".format(self.event_id), response)

    def test_generate_response_no(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        response = command.generate_response(decision='no', event_id=self.event_id)
        self.assertEqual("You are **not** attending **{}**!".format(self.event_id), response)

    def test_generate_response_maybe(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        response = command.generate_response(decision='maybe', event_id=self.event_id)
        self.assertEqual("You **might** be attending **{}**. It's complicated.".format(self.event_id), response)

    def test_generate_funky_response_yes(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        normal_response = command.generate_response(decision='yes', event_id=self.event_id)
        possible_expected_responses = [prefix + normal_response for prefix in command.funky_yes_prefixes]
        response = command.generate_response(decision='yes', event_id=self.event_id, funkify=True)
        self.assertIn(response, possible_expected_responses)

    def test_generate_funky_response_no(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        normal_response = command.generate_response(decision='no', event_id=self.event_id)
        possible_expected_responses = [normal_response + postfix for postfix in command.funky_no_postfixes]
        response = command.generate_response(decision='no', event_id=self.event_id, funkify=True)
        self.assertIn(response, possible_expected_responses)

    def test_rsvp_yes_with_no_prior_reservation(self):
        output = self.issue_command('rsvp yes')

        self.assertEqual(None, self.event['limit'])
        self.assertIn('**You** are attending', output[0]['body'])
        self.assertIn('a@example.com', self.event['yes'])
        self.assertNotIn('a@example.com', self.event['no'])
        self.assertNotIn('a@example.com', self.event['maybe'])

    def test_rsvp_maybe_with_no_prior_reservation(self):
        output = self.issue_command('rsvp maybe')

        self.assertEqual(None, self.event['limit'])
        self.assertIn("You **might** be attending", output[0]['body'])
        self.assertIn('a@example.com', self.event['maybe'])
        self.assertNotIn('a@example.com', self.event['no'])
        self.assertNotIn('a@example.com', self.event['yes'])

    def test_rsvp_no_with_no_prior_reservation(self):
        output = self.issue_command('rsvp no')

        self.assertIn('You are **not** attending', output[0]['body'])
        self.assertNotIn('a@example.com', self.event['yes'])
        self.assertNotIn('a@example.com', self.event['maybe'])
        self.assertIn('a@example.com', self.event['no'])

    def test_rsvp_yes_with_prior_reservation(self):
        self.issue_command('rsvp yes')
        count_dict = Counter(self.event['yes'])

        self.assertEqual(1, count_dict['a@example.com'])

        self.issue_command('rsvp yes')
        count_dict = Counter(self.event['yes'])
        self.assertEqual(1, count_dict['a@example.com'])

    def test_rsvp_maybe_with_prior_reservation(self):
        self.issue_command('rsvp maybe')
        output = self.issue_command('rsvp maybe')

        count_dict = Counter(self.event['maybe'])

        self.assertEqual(1, count_dict['a@example.com'])

    def test_rsvp_no_with_prior_cancelation(self):
        self.issue_command('rsvp no')
        output = self.issue_command('rsvp no')

        count_dict = Counter(self.event['no'])

        self.assertEqual(1, count_dict['a@example.com'])

    def test_rsvp_changing_response(self):
        output = self.issue_command('rsvp maybe')
        count_dict = Counter(self.event['maybe'])
        self.assertEqual(1, count_dict['a@example.com'])
        self.assertIn("You **might** be attending", output[0]['body'])

        # NOT in the yes or no lists
        count_dict = Counter(self.event['yes'])
        self.assertEqual(0, count_dict['a@example.com'])
        count_dict = Counter(self.event['no'])
        self.assertEqual(0, count_dict['a@example.com'])

        output = self.issue_command('rsvp no')
        count_dict = Counter(self.event['no'])
        self.assertEqual(1, count_dict['a@example.com'])
        self.assertIn('You are **not** attending', output[0]['body'])

        # NOT in the yes or maybe lists
        count_dict = Counter(self.event['yes'])
        self.assertEqual(0, count_dict['a@example.com'])
        count_dict = Counter(self.event['maybe'])
        self.assertEqual(0, count_dict['a@example.com'])

        output = self.issue_command('rsvp yes')
        count_dict = Counter(self.event['yes'])
        self.assertEqual(1, count_dict['a@example.com'])
        self.assertIn('**You** are attending', output[0]['body'])

        # NOT in the no or maybe lists
        count_dict = Counter(self.event['no'])
        self.assertEqual(0, count_dict['a@example.com'])
        count_dict = Counter(self.event['maybe'])
        self.assertEqual(0, count_dict['a@example.com'])

    def general_yes_with_no_prior_reservation(self, msg):
        output = self.issue_command(msg)

        self.assertEqual(None, self.event['limit'])
        self.assertIn('are attending', output[0]['body'])
        self.assertIn('a@example.com', self.event['yes'])
        self.assertNotIn('a@example.com', self.event['no'])

    def test_rsvp_hell_yes(self):
        self.general_yes_with_no_prior_reservation('rsvp hell yes')

    def test_rsvp_hell_yes_with_no(self):
        self.general_yes_with_no_prior_reservation('rsvp hell to the yes I have no plans!')

    def test_rsvp_yes_plz(self):
        self.general_yes_with_no_prior_reservation('rsvp yes plz!')

    def test_rsvp_yes_with_nose_in_it(self):
        self.general_yes_with_no_prior_reservation('rsvp yes, after my nose job')

    def test_rsvp_yes_no(self):
        self.general_yes_with_no_prior_reservation('rsvp yes no')

    def test_rsvp_yessssssssssss(self):
        self.general_yes_with_no_prior_reservation('rsvp yesssssssssss')

    def test_rsvp_yassssssssssss(self):
        self.general_yes_with_no_prior_reservation('rsvp yasssssssssss')

    def test_rsvp_thumbsup(self):
        self.general_yes_with_no_prior_reservation('rsvp :thumbsup:')

    def test_rsvp_thumbs_up(self):
        self.general_yes_with_no_prior_reservation('rsvp :thumbs_up:')

    def test_rsvp_thumbsdown(self):
        self.general_no_with_no_prior_reservation('rsvp :thumbsdown:')

    def test_rsvp_thumbs_down(self):
        self.general_no_with_no_prior_reservation('rsvp :thumbs_down:')

    def general_no_with_no_prior_reservation(self, msg):
        output = self.issue_command(msg)

        self.assertEqual(None, self.event['limit'])
        self.assertNotIn('are attending', output[0]['body'])
        self.assertIn('are **not** attending', output[0]['body'])
        self.assertNotIn('a@example.com', self.event['yes'])
        self.assertIn('a@example.com', self.event['no'])

    def test_rsvp_hell_no(self):
        self.general_no_with_no_prior_reservation('rsvp hell no!')

    def test_rsvp_no_way(self):
        self.general_no_with_no_prior_reservation('rsvp no, i\'m busy')

    def test_rsvp_nah(self):
        self.general_no_with_no_prior_reservation("rsvp nah can't make it :(!")

    def test_rsvp_noooooo(self):
        self.general_no_with_no_prior_reservation('rsvp nooooooooooooo!')

    def test_rsvp_no_yes(self):
        self.general_no_with_no_prior_reservation('rsvp no, yes i was there yesterday.')

    def rsvp_word_contains_command(self, msg):
        output = self.issue_command(msg)
        self.assertEqual(None, self.event['limit'])
        self.assertIn('is not a valid RSVPBot command!', output[0]['body'])
        self.assertNotIn('are attending', output[0]['body'])
        self.assertNotIn('are **not** attending', output[0]['body'])
        self.assertNotIn('a@example.com', self.event['no'])

    def test_rsvp_nose(self):
        self.rsvp_word_contains_command('rsvp nose jobs')

    def test_rsvp_yesterday(self):
        self.rsvp_word_contains_command('rsvp yesterday')

    def test_rsvp_eyes(self):
        self.rsvp_word_contains_command('rsvp eyes')

    def test_rsvp_no_eyes(self):
        self.general_no_with_no_prior_reservation('rsvp no eyes')

    def test_rsvp_yes_exclamation_no_plans(self):
        self.general_yes_with_no_prior_reservation('rsvp yes! i couldn\'t say no')

    def test_rsvp_NO(self):
        self.general_no_with_no_prior_reservation('rsvp hell NO!')

    def test_RSVP_yes_way(self):
        self.general_yes_with_no_prior_reservation('RSVP yes plz')


class RSVPLimitTest(RSVPTest):
    def test_set_limit(self):
        output = self.issue_command('rsvp set limit 1')

        self.assertIn('has been set to **1**', output[0]['body'])
        self.assertEqual(1, self.event['limit'])

    def test_cannot_rsvp_on_a_full_event(self):
        self.issue_command('rsvp set limit 1')
        self.issue_command('rsvp yes')
        output = self.issue_custom_command('rsvp yes', sender_full_name='Tester 2')

        self.assertIn('The **limit** for this event has been reached!', output[0]['body'])

    def test_limit_actually_works(self):
        self.issue_command('rsvp set limit 500')
        self.issue_command('rsvp yes')
        output = self.issue_custom_command(
            'rsvp yes',
            sender_full_name='Sender B',
            sender_email='b@example.com'
        )

        self.assertIn('are attending', output[0]['body'])
        self.assertIn('b@example.com', self.event['yes'])
        self.assertEqual(498, self.event['limit'] - len(self.event['yes']))


class RSVPDurationTest(RSVPTest):
    def test_set_duration(self):
        output = self.issue_command('rsvp set duration 30m')

        self.assertIn(
            'has been set to **0:30:00**!',
            output[0]['body']
        )


class RSVPCalendarTest(RSVPTest):
    def test_create_calendar_event_without_required_params_returns_error_message(self):
        ouput = self.issue_command('rsvp add to calendar')

        self.assertIn(
            "Oops! The `date` and `time` are required to add this to the calendar!",
            ouput[0]['body'])

    @patch('calendar_events.create_event_on_calendar')
    def test_create_calendar_event_with_params_returns_success_message(self, mock):
        self.issue_command('rsvp set date 02/25/2100')
        self.issue_command('rsvp set time 10:30')
        self.issue_command('rsvp set place Hopper!')
        self.issue_command('rsvp set duration 30m')

        mock.return_value = {
            'id': 1, 'htmlLink': 'www.google.com',
            'calendar_name': 'Test'
        }

        output = self.issue_command('rsvp add to calendar')

        self.assertIn(
            'Event [added to Test Calendar](www.google.com)!',
            output[0]['body']
        )


class RSVPDateTest(RSVPTest):
    def test_set_date(self):
        output = self.issue_command('rsvp set date 02/25/2099')

        self.assertIn(
            'has been set to **02/25/99**!',
            output[0]['body']
        )

        self.assertEqual(
            '2099-02-25',
            self.event['date']
        )

    def test_set_date_parses_human_dates(self):
        output = self.issue_command('rsvp set date tomorrow')

        tomorrow = date.today() + timedelta(days=1)

        self.assertEqual(
            str(tomorrow),
            self.event['date']
        )

    def test_set_date_prefers_future_when_date_is_ambiguous(self):
        """
        When passing an ambiguous weekday we should privilege dates from the
        future, e.g. if we're on Wednesday and I say `rsvp set date tuesday`
        then the date should be set to next Tuesday and not yesterday.
        """
        next_week_date = date.today() + timedelta(days=6)
        weekday = next_week_date.strftime("%A")

        output = self.issue_command('rsvp set date %s' % weekday)


        self.assertEqual(
            str(next_week_date),
            self.event['date']
        )

    def test_set_past_date(self):
        output = self.issue_command('rsvp set date 02/25/1000')

        self.assertIn(
            'Oops! **02/25/1000** is not a valid date in the **future**!',
            output[0]['body']
        )

        self.assertNotEqual(
            '1000-02-25',
            self.event['date']
        )

    def test_new_event_is_today(self):
        today = str(date.today())
        self.assertEqual(today, self.event['date'])


class RSVPTimeTest(RSVPTest):
    def test_set_time(self):
        output = self.issue_command('rsvp set time 10:30')

        self.assertIn('has been set to **10:30**', output[0]['body'])
        self.assertEqual('10:30', self.event['time'])

    def test_set_time_fail(self):
        self.issue_command('rsvp init')

        output = self.issue_command('rsvp set time 99:99')

        self.assertIn('is not a valid time', output[0]['body'])
        self.assertNotEqual('99:99', self.event['time'])

    def test_new_event_is_all_day(self):
        self.assertEqual(self.event['time'], None)

    def test_set_event_all_day(self):
        self.issue_command('rsvp set time 10:30')
        output = self.issue_command('rsvp set time allday')
        self.assertEqual(self.event['time'], None)
        self.assertIn('all day long event.', output[0]['body'])


class RSVPDescriptionTest(RSVPTest):
    def test_set_description(self):
        output = self.issue_command('rsvp set description This is the description of the event!')
        self.assertEqual(self.event['description'], 'This is the description of the event!')
        self.assertIn('The description for this event has been set', output[0]['body'])
        self.assertIn(self.event['description'], output[0]['body'])

    def test_add_description_with_message_including_yeah(self):
        output = self.issue_command('rsvp set description This is the description of the event! yeah!')
        self.assertEqual(self.event['description'], 'This is the description of the event! yeah!')
        self.assertIn('The description for this event has been set', output[0]['body'])
        self.assertIn(self.event['description'], output[0]['body'])

    def test_rsvp_description_containing_yes(self):
        output = self.issue_command('rsvp set description lets do this yes!')
        self.assertEqual(self.event['description'], 'lets do this yes!')
        self.assertIn('The description for this event has been set', output[0]['body'])
        self.assertIn(self.event['description'], output[0]['body'])
        self.assertNotIn('are attending', output[0]['body'])


class RSVPPlaceTest(RSVPTest):
    def test_set_place(self):
        output = self.issue_command('rsvp set place Hopper!')
        self.assertEqual(self.event['place'], 'Hopper!')
        self.assertIn('The place for this event has been set', output[0]['body'])
        self.assertIn(self.event['place'], output[0]['body'])

    def test_set_location(self):
        # location should work as an alias for place
        output = self.issue_command('rsvp set location Hopper!')
        self.assertEqual(self.event['place'], 'Hopper!')
        self.assertIn('The place for this event has been set', output[0]['body'])
        self.assertIn(self.event['place'], output[0]['body'])


class RSVPSummaryTest(RSVPTest):
    def test_summary_shows_duration(self):
        self.issue_command('rsvp set duration 1h')
        output = self.issue_command('rsvp summary')
        self.assertIn('**Duration**|1:00:00', output[0]['body'])

    def test_summary_does_not_include_duration_if_duration_not_set(self):
        output = self.issue_command('rsvp summary')
        self.assertNotIn('**Duration**', output[0]['body'])

    def test_summary_shows_place(self):
        self.issue_command('rsvp set place Hopper!')
        output = self.issue_command('rsvp summary')
        self.assertIn('**Where**|Hopper!', output[0]['body'])

    def test_summary_does_not_include_place_if_place_not_set(self):
        output = self.issue_command('rsvp summary')
        self.assertNotIn('**Where**', output[0]['body'])

    def test_summary_shows_description(self):
        self.issue_command('rsvp set description test description')
        output = self.issue_command('rsvp summary')
        self.assertIn('**What**|test description', output[0]['body'])

    def test_summary_does_not_include_what_section_if_description_not_set(self):
        output = self.issue_command('rsvp summary')
        self.assertNotIn('**What**', output[0]['body'])

    def test_summary_shows_allday_for_allday_event(self):
        output = self.issue_command('rsvp summary')
        self.assertIn('(All day)', output[0]['body'])

    def test_summary_shows_date(self):
        self.issue_command('rsvp set date 02/25/2100')
        output = self.issue_command('rsvp summary')
        self.assertIn('**When**|2100-02-25', output[0]['body'])

    def test_summary_shows_limit(self):
        self.issue_command('rsvp set limit 1')
        output = self.issue_command('rsvp summary')
        self.assertIn('**Limit**|0/1', output[0]['body'])

    def test_summary_does_not_shows_limit_if_limit_not_set(self):
        output = self.issue_command('rsvp summary')
        self.assertNotIn('**Limit**', output[0]['body'])

    def test_summary_shows_time(self):
        self.issue_command('rsvp set time 10:30')
        output = self.issue_command('rsvp summary')
        self.assertIn('10:30', output[0]['body'])

    def test_summary_shows_thread_name(self):
        output = self.issue_command('rsvp summary')
        self.assertIn('Testing', output[0]['body'])


class RSVPPingTest(RSVPTest):
    def test_ping_yes(self):
        users = [
            ('yes', 'A', 'a@example.com'),
            ('yes', 'B', 'b@example.com'),
            ('yes', 'C', 'c@example.com'),
            ('yes', 'D', 'd@example.com'),
            ('no', 'E', 'e@example.com'),
            ('no', 'F', 'f@example.com'),
            ('no', 'G', 'g@example.com'),
            ('no', 'H', 'h@example.com'),
            ('maybe', 'W', 'w@example.com'),
            ('maybe', 'X', 'x@example.com'),
            ('maybe', 'Y', 'y@example.com'),
            ('maybe', 'Z', 'z@example.com'),
        ]
        for user in users:
            command = 'rsvp {response}'.format(response=user[0])
            sender_full_name = user[1]
            sender_email = user[2]
            self.issue_custom_command(
                command,
                sender_full_name=sender_full_name,
                sender_email=sender_email
            )

        users_dict = {email: name for (_, name, email) in users}

        # no actual zulip_client in tests, so we have to mock the response
        return_val = ZulipUsers('test_users_file.json')
        return_val.zulip_users = users_dict

        with patch.object(rsvp_commands.RSVPPingCommand,
                          'get_users_dict',
                          return_value=return_val):

            output = self.issue_command('rsvp ping')

        # yeses
        self.assertIn('@**A**', output[0]['body'])
        self.assertIn('@**B**', output[0]['body'])
        self.assertIn('@**C**', output[0]['body'])
        self.assertIn('@**D**', output[0]['body'])

        # maybes
        self.assertIn('@**W**', output[0]['body'])
        self.assertIn('@**X**', output[0]['body'])
        self.assertIn('@**Y**', output[0]['body'])
        self.assertIn('@**Z**', output[0]['body'])

        self.assertNotIn('@**E**', output[0]['body'])
        self.assertNotIn('@**F**', output[0]['body'])
        self.assertNotIn('@**G**', output[0]['body'])
        self.assertNotIn('@**H**', output[0]['body'])

    def test_ping_message(self):
        self.issue_custom_command('rsvp yes', sender_full_name='A', sender_email='a@example.com')

        users_dict = {'a@example.com': 'A'}

        return_val = ZulipUsers('test_users_file.json')
        return_val.zulip_users = users_dict

        with patch.object(rsvp_commands.RSVPPingCommand,
                          'get_users_dict',
                          return_value=return_val):

            output = self.issue_command('rsvp ping message!!!')

        self.assertIn('@**A**', output[0]['body'])
        self.assertIn('message!!!', output[0]['body'])

    def test_rsvp_ping_with_yes(self):
        self.issue_custom_command('rsvp yes', sender_full_name='B', sender_email='b@example.com')
        users_dict = {'b@example.com': 'B'}

        return_val = ZulipUsers('test_users_file.json')
        return_val.zulip_users = users_dict

        with patch.object(rsvp_commands.RSVPPingCommand,
                          'get_users_dict',
                          return_value=return_val):
            output = self.issue_command('rsvp ping we\'re all going to the yes concert')

        self.assertEqual(None, self.event['limit'])
        self.assertNotIn('@**Tester** is attending!', output[0]['body'])
        self.assertNotIn('a@example.com', self.event['no'])
        self.assertIn('@**B**', output[0]['body'])
        self.assertIn('we\'re all going to the yes concert', output[0]['body'])


class RSVPHelpTest(RSVPTest):

    def test_rsvp_help_generates_markdown_table(self):
        output = self.issue_custom_command('rsvp help')
        header = """
**Command**|**Description**
--- | ---
        """.strip()
        self.assertIn(header, output[0]['body'])

    def test_rsvp_help_contains_help_for_all_commands(self):
        # FIXME: currently enumerating commands manually, which is brittle.
        # Being able to get a list of all commands
        commands = (
            "yes",
            "no",
            "init",
            "help",
            "ping",
            "move",
            "set time",
            "set date",
            "set place",
            "set limit",
            "summary",
            "credits"
        )
        output = self.issue_custom_command('rsvp help')
        for command in commands:
            self.assertIn("`rsvp %s" % command, output[0]['body'])



class RSVPMessageTypesTest(RSVPTest):
    def test_rsvp_private_message(self):
        output = self.issue_custom_command('rsvp yes', message_type='private')
        self.assertEqual('private', output[0]['type'])
        self.assertEqual('a@example.com', output[0]['display_recipient'])

    def test_rsvp_help_replies_privately(self):
        output = self.issue_command('rsvp help')
        self.assertEqual(output[0]['display_recipient'], 'a@example.com')
        self.assertEqual(output[0]['type'], 'private')


class RSVPMultipleCommandsTest(RSVPTest):
    def test_rsvp_multiple_commands(self):
        commands = """
rsvp set time 10:30
rsvp set date 02/25/2099
"""

        output = self.issue_command(commands)
        self.assertIn(
            'has been set to **10:30**',
            output[0]['body'])

        self.assertEqual('10:30', self.event['time'])

        self.assertIn(
            'has been set to **02/25/99**!',
            output[1]['body']
        )
        self.assertEqual( '2099-02-25', self.event['date'])

    def test_rsvp_multiple_commands_with_other_text(self):
        commands = """
rsvp set time 10:30
Looking forward to this!
rsvp set date 02/25/2099
"""

        output = self.issue_command(commands)
        self.assertIn(
            'has been set to **10:30**',
            output[0]['body'])

        self.assertEqual('10:30', self.event['time'])

        self.assertEqual(None, output[1])

        self.assertIn(
            'has been set to **02/25/99**!',
            output[2]['body']
        )
        self.assertEqual('2099-02-25', self.event['date'])


if __name__ == '__main__':
    unittest.main()
