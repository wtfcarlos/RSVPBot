# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import datetime
from time import mktime
import random

from pytimeparse.timeparse import timeparse
import parsedatetime

import calendar_events
import strings
import util
from zulip_users import ZulipUsers


ISOWEEKDAY = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday',
              5: 'Friday', 6: 'Saturday', 7: 'Sunday'}


class RSVPMessage(object):
  """Class that represents a response from an RSVPCommand.

  Every call to an RSVPCommand instance's execute() method is expected to return an instance
  of this class.
  """
  def __init__(self, msg_type, body, to=None, subject=None):
    self.type = msg_type
    self.body = body
    self.to = to
    self.subject = subject

  def __getitem__(self, attr):
    self.__dict__[attr]

  def __str__(self):
    attr_string = ""
    for key in dir(self):
      attr_string += key + ":" + str(getattr(self, key)) + ", "
    return attr_string


class RSVPCommandResponse(object):
  def __init__(self, events, *args):
    self.events = events
    self.messages = []
    for arg in args:
      if isinstance(arg, RSVPMessage):
        self.messages.append(arg)


class RSVPCommand(object):
  """Base class for an RSVPCommand."""
  regex = None

  def __init__(self, prefix, *args, **kwargs):
    # prefix is the command start the bot listens to, typically 'rsvp'
    self.prefix = r'^' + prefix + r' '
    self.regex = self.prefix + self.regex

  def match(self, input_str):
    return re.match(self.regex, input_str, flags=re.DOTALL | re.I)

  def execute(self, events, *args, **kwargs):
    """execute() is just a convenience wrapper around __run()."""
    return self.run(events, *args, **kwargs)


class RSVPEventNeededCommand(RSVPCommand):
  """Base class for a command where an event needs to exist prior to execution."""
  def execute(self, events, *args, **kwargs):
    event = kwargs.get('event')
    sender_email = kwargs.get('sender_email')
    if event:
      return self.run(events, *args, **kwargs)
    return RSVPCommandResponse(events, RSVPMessage('private', strings.ERROR_NOT_AN_EVENT, sender_email))


class RSVPInitCommand(RSVPCommand):
  regex = r'init$'

  def run(self, events, *args, **kwargs):
    sender_id   = kwargs.pop('sender_id')
    event_id    = kwargs.pop('event_id')
    subject    = kwargs.pop('subject')
    sender_email = kwargs.pop('sender_email')

    body = strings.MSG_INIT_SUCCESSFUL

    if events.get(event_id):
      # Event already exists, error message, we can't initialize twice.
      body = strings.ERROR_ALREADY_AN_EVENT
      response = RSVPCommandResponse(events, RSVPMessage('private', body, sender_email))
    else:
      # Update the dictionary with the new event and commit.
      events.update(
        {
          event_id: {
            'name': subject,
            'description': None,
            'place': None,
            'creator': sender_id,
            'yes': [sender_email],
            'no': [],
            'maybe': [],
            'time': None,
            'limit': None,
            'date': '%s' % datetime.date.today(),
            'calendar_event': None,
            'duration': None,
          }
        }
      )
      response = RSVPCommandResponse(events, RSVPMessage('stream', body))

    return response


class RSVPSetDurationCommand(RSVPEventNeededCommand):
  regex = r'set duration (?P<duration>.+)$'

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    event_id = kwargs.pop('event_id')
    duration = kwargs.pop('duration')
    sender_email = kwargs.pop('sender_email')

    parsed_duration_in_seconds = timeparse(duration, granularity='minutes')
    event['duration'] = parsed_duration_in_seconds
    body = strings.MSG_DURATION_SET % (event_id, datetime.timedelta(seconds=parsed_duration_in_seconds))
    calendar_event_id = event.get('calendar_event') and event['calendar_event']['id']
    if calendar_event_id:
      try:
        calendar_events.update_gcal_event(event, event_id)
      except calendar_events.KeyfilePathNotSpecifiedError:
        pass

    return RSVPCommandResponse(events, RSVPMessage('private', body, sender_email))


class RSVPCreateCalendarEventCommand(RSVPEventNeededCommand):
  regex = r'add to calendar$'

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    event_id = kwargs.pop('event_id')

    try:
      cal_event = calendar_events.add_rsvpbot_event_to_gcal(event, event_id)
    except calendar_events.KeyfilePathNotSpecifiedError:
      body = strings.ERROR_CALENDAR_ENVS_NOT_SET
    except calendar_events.DateAndTimeNotSuppliedError:
      body = strings.ERROR_DATE_AND_TIME_NOT_SET
    except calendar_events.DurationNotSuppliedError:
      body = strings.ERROR_DURATION_NOT_SET
    else:
      event['calendar_event'] = {}
      event['calendar_event']['id'] = cal_event.get('id')
      event['calendar_event']['html_link'] = cal_event.get('htmlLink')
      body = strings.MSG_ADDED_TO_CALENDAR.format(
          calendar_name=cal_event.get('calendar_name'),
          url=cal_event.get('htmlLink'))

    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPHelpCommand(RSVPCommand):
  regex = r'help$'

  with open('README.md', 'r') as readme_file:
      readme_contents = readme_file.read()
      _, commands_table = readme_contents.split("## Commands\n")

  def run(self, events, *args, **kwargs):
    sender_email = kwargs.pop('sender_email')
    return RSVPCommandResponse(events, RSVPMessage('private', self.commands_table, sender_email))


class RSVPCancelCommand(RSVPEventNeededCommand):
  regex = r'cancel$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    sender_id = kwargs.pop('sender_id')
    event = kwargs.pop('event')

    # Check if the issuer of this command is the event's original creator.
    # Only they can delete the event.
    creator = event['creator']

    if creator == sender_id:
      body = strings.MSG_EVENT_CANCELED
      events.pop(event_id)
    else:
      body = strings.ERROR_NOT_AUTHORIZED_TO_DELETE

    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPMoveCommand(RSVPEventNeededCommand):
  regex = r'move (?P<destination>.+)$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    sender_id = kwargs.pop('sender_id')
    event = kwargs.pop('event')
    destination = kwargs.pop('destination')
    success_msg = None

    # Check if the issuer of this command is the event's original creator.
    # Only she can modify the event.
    creator = event['creator']

    # check and make sure a valid Zulip stream/topic URL is passed
    if not destination:
      body = strings.ERROR_MISSING_MOVE_DESTINATION
    elif creator != sender_id:
      body = strings.ERROR_NOT_AUTHORIZED_TO_DELETE
    else:
      # split URL into components
      stream, topic = util.narrow_url_to_stream_topic(destination)

      if stream is None or topic is None:
        body = strings.ERROR_BAD_MOVE_DESTINATION % destination
      else:
        new_event_id = stream + "/" + topic

        if new_event_id in events:
          body = strings.ERROR_MOVE_ALREADY_AN_EVENT % new_event_id
        else:
          body = strings.MSG_EVENT_MOVED % (new_event_id, destination)

          old_event = events.pop(event_id)

          # need to make sure that there's no duplicate here!
          # also, ideally we'd make sure the stream/topic existed & create it if not.
          # AND send an 'init' notification to that new stream/toipic. Hm. what's the
          # best way to do that? Allow for a parameterized init? It's always a reply, not a push.
          # Can we return MULTIPLE messages instead of just one?

          old_event.update({'name': topic})

          events.update(
            {
              new_event_id: old_event
            }
          )

          success_msg = RSVPMessage('stream', strings.MSG_INIT_SUCCESSFUL, stream, topic)

    return RSVPCommandResponse(events, RSVPMessage('stream', body), success_msg)


class LimitReachedException(Exception):
  pass


class RSVPConfirmCommand(RSVPEventNeededCommand):

  yes_answers = (
    "ye(s+?)",
    "yea(h+?)",
    "in",
    "yep",
    "ya(s+?)",
    ":thumbs_?up:",
    "y",
    ":\+1:"
  )
  no_answers = (
    "n(o+?)",
    "out",
    "nope",
    "na(h+?)",
    ":thumbs_?down:",
    "n",
    ":-1:"
  )

  regex_yes = '(?P<yes_decision>%s)' % format('|'.join(yes_answers))
  regex_no = '(?P<no_decision>%s)' % format('|'.join(no_answers))
  regex_maybe = '(?P<maybe_decision>maybe)'

  # We're using a negative lookahead/lookbehind to make sure that whatever is
  # matched is a word on its own, i.e. we want to match "yes" but not
  # "yesterday". We can't use simple word boundaries here ("\b") if we want to
  # support emojis like :thumbsup: because ':' is not a word character.
  regex = r'.*?(?<!\w)({yes}|{no}|{maybe})(?!\w)'.format(
    yes=regex_yes,
    no=regex_no,
    maybe=regex_maybe)

  responses = {
    "yes": "**You** are attending **%s**!",
    "no": "You are **not** attending **%s**!",
    "maybe": "You **might** be attending **%s**. It's complicated.",
  }

  funky_yes_prefixes = [
    "GET EXCITED!! ",
    "AWWW YISS!! ",
    "YASSSSS HENNY! ",
    "OMG OMG OMG ",
    "HYPE HYPE HYPE HYPE HYPE ",
    "WOW THIS IS AWESOME: ",
    "YEAAAAAAHHH!!!! :tada: ",
  ]

  funky_no_postfixes = [
    " :confounded:",
    " Bummer!",
    " Oh no!!",
  ]

  def generate_response(self, decision, event_id, funkify=False):
      response_string = self.responses.get(decision) % event_id
      if not funkify:
          return response_string
      if decision == 'yes':
        return random.choice(self.funky_yes_prefixes) + response_string
      elif decision == 'no':
        return response_string + random.choice(self.funky_no_postfixes)
      return response_string

  def confirm(self, event, event_id, sender_email, decision):
    # Temporary kludge to add a 'maybe' array to legacy events. Can be removed after
    # all currently logged events have passed.
    if ('maybe' not in event.keys()):
      event['maybe'] = []

    # If they're in a different response list, take them out of it.
    for response in self.responses.keys():
      # prevent duplicates if replying multiple times
      if (response == decision):
        # if they're already in that list, nothing to do
        if (sender_email not in event[response]):
          event[response].append(sender_email)
      # else, remove all instances of them from other response lists.
      elif sender_email in event[response]:
        event[response] = [value for value in event[response] if value != sender_email]
      calendar_event_id = event.get('calendar_event') and event['calendar_event']['id']
      if calendar_event_id:
        try:
          calendar_events.update_gcal_event(event, event_id)
        except calendar_events.KeyfilePathNotSpecifiedError:
          pass

    return event

  def attempt_confirm(self, event, event_id, sender_email, decision, limit):
    if decision == 'yes' and limit:
      available_seats = limit - len(event['yes'])
      # In this case, we need to do some extra checking for the attendance limit.
      if (available_seats - 1 < 0):
        raise LimitReachedException()

    return self.confirm(event, event_id, sender_email, decision)

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    event = kwargs.pop('event')
    yes_decision = kwargs.pop('yes_decision')
    no_decision = kwargs.pop('no_decision')
    decision = 'yes' if yes_decision else ('no' if no_decision else 'maybe')
    sender_name = kwargs.pop('sender_full_name')
    sender_email = kwargs.pop('sender_email')

    limit = event['limit']

    try:
      event = self.attempt_confirm(event, event_id,  sender_email, decision, limit)

      # Update the events dict with the new event.
      events[event_id] = event
      # 1 in 10 chance of generating a funky response
      response = self.generate_response(decision, event_id, funkify=(random.random() < 0.1))
    except LimitReachedException:
      response = strings.ERROR_LIMIT_REACHED
    return RSVPCommandResponse(events, RSVPMessage('private', response, sender_email))


class RSVPSetLimitCommand(RSVPEventNeededCommand):
  regex = r'set limit (?P<limit>\d+)$'

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    attendance_limit = int(kwargs.pop('limit'))
    event['limit'] = attendance_limit
    return RSVPCommandResponse(events, RSVPMessage('stream', strings.MSG_ATTENDANCE_LIMIT_SET % attendance_limit))


class RSVPSetDateCommand(RSVPEventNeededCommand):
  cal = parsedatetime.Calendar()
  regex = r'set date (?P<date>.*)$'

  def _is_in_the_future(self, event_date):
    today = datetime.date.today()
    return event_date >= today

  def _parse_date(self, raw_date):
    time_struct, parse_status = self.cal.parse(raw_date)
    return datetime.date.fromtimestamp(mktime(time_struct))

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    event_id = kwargs.pop('event_id')
    sender_email = kwargs.pop('sender_email')
    raw_date = kwargs.pop('date')
    try:
      event_date = self._parse_date(raw_date)
    except ValueError:
      event_date = None

    if event_date and self._is_in_the_future(event_date):
      event['date'] = str(event_date)
      events[event_id] = event
      body = strings.MSG_DATE_SET % (event_id, event_date.strftime("%x"))
      calendar_event_id = event.get('calendar_event') and event['calendar_event']['id']
      if calendar_event_id:
        try:
          calendar_events.update_gcal_event(event, event_id)
        except calendar_events.KeyfilePathNotSpecifiedError:
          pass
    else:
      body = strings.ERROR_DATE_NOT_VALID % raw_date

    return RSVPCommandResponse(events, RSVPMessage('private', body, sender_email))


class RSVPSetTimeCommand(RSVPEventNeededCommand):
  regex = r'set time (?P<hours>\d{1,2})\:(?P<minutes>\d{1,2})$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    hours, minutes = int(kwargs.pop('hours')), int(kwargs.pop('minutes'))
    sender_email = kwargs.pop('sender_email')

    if hours in range(0, 24) and minutes in range(0, 60):
      event = events[event_id]
      event['time'] = '%02d:%02d' % (hours, minutes)
      body = strings.MSG_TIME_SET % (event_id, hours, minutes)
      calendar_event_id = event.get('calendar_event') and event['calendar_event']['id']
      if calendar_event_id:
        try:
          calendar_events.update_gcal_event(event, event_id)
        except calendar_events.KeyfilePathNotSpecifiedError:
          pass
    else:
      body = strings.ERROR_TIME_NOT_VALID % (hours, minutes)

    return RSVPCommandResponse(events, RSVPMessage('private', body, sender_email))


class RSVPSetTimeAllDayCommand(RSVPEventNeededCommand):
  regex = r'set time allday$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    sender_email = kwargs.pop('sender_email')
    events[event_id]['time'] = None
    return RSVPCommandResponse(events, RSVPMessage('private', strings.MSG_TIME_SET_ALLDAY % event_id, sender_email))


class RSVPSetStringAttributeCommand(RSVPEventNeededCommand):
  regex = r'set (?P<attribute>(location|place|description)) (?P<value>.+)$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    sender_email = kwargs.pop('sender_email')
    attribute = kwargs.pop('attribute')
    if attribute == "location":
      attribute = "place"
    value = kwargs.pop('value')

    event = events[event_id]
    event[attribute] = value
    calendar_event_id = event.get('calendar_event') and event['calendar_event']['id']
    if calendar_event_id:
      try:
        calendar_events.update_gcal_event(event, event_id)
      except calendar_events.KeyfilePathNotSpecifiedError:
        pass
    body = strings.MSG_STRING_ATTR_SET % (attribute, value)
    return RSVPCommandResponse(events, RSVPMessage('private', body, sender_email))


class RSVPPingCommand(RSVPEventNeededCommand):
  regex = r'^({key_word} ping)$|({key_word} ping (?P<message>.+))$'

  def __init__(self, prefix, *args, **kwargs):
    self.regex = self.regex.format(key_word=prefix)

  def get_users_dict(self):
    return ZulipUsers()

  def run(self, events, *args, **kwargs):
    users = self.get_users_dict()

    event = kwargs.pop('event')
    message = kwargs.get('message')

    body = "**Pinging all participants who RSVP'd!!**\n"

    for participant in event['yes']:
      body += "@**%s** " % users.convert_email_to_pingable_name(participant)

    for participant in event['maybe']:
      body += "@**%s** " % users.convert_email_to_pingable_name(participant)

    if message:
      body += ('\n' + message)

    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPCreditsCommand(RSVPEventNeededCommand):
  regex = r'credits$'

  def run(self, events, *args, **kwargs):

    sender_email = kwargs.pop('sender_email')

    contributors = [
      "Mudit Ameta (SP2'15)",
      "Diego Berrocal (F2'15)",
      "Shad William Hopson (F1'15)",
      "Tom Murphy (F2'15)",
      "Miriam Shiffman (F2'15)",
      "Anjana Sofia Vakil (F2'15)",
      "Steven McCarthy (SP2'15)",
      "Kara McNair (F2'15)",
      "Pris Nasrat (SP2'16)",
      "Benjamin Gilbert (F2'15)",
      "Andrew Drozdov (SP1'15)",
      "Alex Wilson (S1'16)",
      "Jérémie Jost (S1'16)",
      "Amulya Reddy (S1'16)",
      "James J. Porter (S'13)",
      "Kracekumar (F2'16)",
    ]

    testers = ["Nikki Bee (SP2'15)", "Anthony Burdi (SP1'15)", "Noella D'sa (SP2'15)", "Mudit Ameta (SP2'15)"]

    body = "The RSVPBot was created by @**Carlos Rey (SP2'15)**\nWith **contributions** from:\n\n"

    body += '\n '.join(contributors)

    body += "\n\n and invaluable test feedback from:\n\n"
    body += '\n '.join(testers)

    body += "\n\nThe code for **RSVPBot** is available at https://github.com/kokeshii/RSVPBot"

    return RSVPCommandResponse(events, RSVPMessage('private', body, sender_email))


class RSVPSummaryCommand(RSVPEventNeededCommand):
  regex = r'(summary$|status$)'

  def get_users_dict(self):
    return ZulipUsers()

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    users = self.get_users_dict()

    summary_table = '**%s**' % (event['name'])
    summary_table += '\t|\t\n:---:|:---:\n'

    if event['description']:
        summary_table += '**What**|%s\n' % event['description']

    date = datetime.datetime.strptime(event['date'], '%Y-%m-%d').date()
    summary_table += '**When**|%s @ %s\n' % (event['date'], event['time'] or '(All day)')
    summary_table += '**Day**|%s \n' % (ISOWEEKDAY.get(date.isoweekday()))

    if event['duration']:
        summary_table += '**Duration**|%s\n' % datetime.timedelta(seconds=event['duration'])

    if event['place']:
        summary_table += '**Where**|%s\n' % event['place']

    if event['limit']:
        limit_str = '%d/%d spots left' % (event['limit'] - len(event['yes']), event['limit'])
        summary_table += '**Limit**|%s\n' % limit_str

    confirmation_table = 'YES ({}) |NO ({}) |MAYBE({}) \n:---:|:---:|:---:\n'

    confirmation_table = confirmation_table.format(len(event['yes']), len(event['no']), len(event['maybe']))

    row_list = map(None, event['yes'], event['no'], event['maybe'])

    for row in row_list:
      confirmation_table += '{}|{}|{}\n'.format(
        '' if row[0] is None else users.convert_email_to_pingable_name(row[0]),
        '' if row[1] is None else users.convert_email_to_pingable_name(row[1]),
        '' if row[2] is None else users.convert_email_to_pingable_name(row[2])
      )
    else:
      confirmation_table += '\t|\t'

    body = summary_table + '\n\n' + confirmation_table
    return RSVPCommandResponse(events, RSVPMessage('stream', body))
