# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import datetime
import random

import strings
import util


class RSVPMessage(object):
  """
  Class that represents a response from an RSVPCommand.
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
  """
  Base class for an RSVPCommand
  """
  regex = None

  def __init__(self, prefix, *args, **kwargs):
    # prefix is the command start the bot listens to, typically 'rsvp'
    self.prefix = r'^' + prefix + r' '
    self.regex = self.prefix + self.regex

  def match(self, input_str):
    return re.match(self.regex, input_str, flags=re.DOTALL|re.I)

  def execute(self, events, *args, **kwargs):
    """
    execute() is just a convenience wrapper around __run()
    """
    return self.run(events, *args, **kwargs)


class RSVPEventNeededCommand(RSVPCommand):
  """
  Base class for a command where an event needs to exist prior to execution
  """
  def execute(self, events, *args, **kwargs):
    event = kwargs.get('event')
    if event:
      return self.run(events, *args, **kwargs)
    return RSVPCommandResponse(events, RSVPMessage('stream', strings.ERROR_NOT_AN_EVENT))


class RSVPInitCommand(RSVPCommand):
  regex = r'init$'

  def run(self, events, *args, **kwargs):
    sender_id   = kwargs.pop('sender_id')
    event_id    = kwargs.pop('event_id')
    subject    = kwargs.pop('subject')

    body = strings.MSG_INIT_SUCCESSFUL

    if events.get(event_id):
      # Event already exists, error message, we can't initialize twice.
      body = strings.ERROR_ALREADY_AN_EVENT
    else:
      # Update the dictionary with the new event and commit.
      events.update(
        {
          event_id: {
            'name': subject,
            'description': None,
            'place': None,
            'creator': sender_id,
            'yes': [],
            'no': [],
            'maybe': [],
            'time': None,
            'limit': None,
            'date': '%s' % datetime.date.today(),
          }
        }
      )

    response = RSVPCommandResponse(events, RSVPMessage('stream', body))
    return response


class RSVPHelpCommand(RSVPCommand):
  regex = r'help$'

  def run(self, events, *args, **kwargs):
    body = "**Command**|**Description**\n"
    body += "--- | ---\n"
    body += "**`rsvp yes`**|Marks **you** as attending this event.\n"
    body += "**`rsvp no`**|Marks you as **not** attending this event.\n"
    body += "`rsvp init`|Initializes a thread as an RSVPBot event. Must be used before any other command.\n"
    body += "`rsvp help`|Shows this handy table.\n"
    body += "`rsvp ping <message>`|Pings everyone that has RSVP'd so far. Optionally, sends a message, if provided.\n"
    body += "`rsvp set time HH:mm`|Sets the time for this event (24-hour format) (optional)\n"
    body += "`rsvp set date mm/dd/yyyy`|Sets the date for this event (optional, if not explicitly set, the date for the event is the date of the creation of the event, i.e. the call to `rsvp init`)\n"
    body += "`rsvp set description DESCRIPTION`|Sets this event's description to DESCRIPTION (optional)\n"
    body += "`rsvp set place PLACE_NAME`|Sets the place for this event to PLACE_NAME (optional)\n"
    body += "`rsvp set limit LIMIT`|Set the attendance limit for this event to LIMIT. Set LIMIT as 0 for infinite attendees.\n"
    body += "`rsvp cancel`|Cancels this event (can only be called by the caller of `rsvp init`)\n"
    body += "`rsvp move <destination_url>`|Moves this event to another stream/topic. Requires full URL for the destination (e.g.'https://zulip.com/#narrow/stream/announce/topic/All.20Hands.20Meeting') (can only be called by the caller of `rsvp init`)\n"
    body += "`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.\n"
    body += "`rsvp credits`|Lists all the awesome people that made RSVPBot a reality.\n"

    return RSVPCommandResponse(events, RSVPMessage('private', body))


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
  regex = r'.*?\b(?P<decision>(yes|no|maybe))\b'

  responses = {
    "yes": '@**%s** is attending!',
    "no": '@**%s** is **not** attending!',
    "maybe": '@**%s** might be attending. It\'s complicated.',
  }

  vips = [
    "James A. Keene (W1'14)",
    "Cole Murphy (SP2'15)",
    "Mudit Ameta (SP2'15)",
    "Tanoy Sinha (F1'14)",
    "Michelle Steigerwalt (SP1'15)",
    "Steven McCarthy (SP2'15)",
    "Chen Lin (W'14)",
    "Gonçalo Morais (SP1'15)",
    "David Albert",
    "Jesse Chen (SP2'15)",
    "Tim Sell (S1'15)",
    "Nicole Lehrer (S1'15)",
    "Agustín Benassi (SP1'15)",
    "Rachel Vincent",
    "Alex Takata (F1'15)",
    "Anjana Sofia Vakil (F2'15)",
    "Decky Coss (W'14)",
    "Pam Selle (SP1'15)",
    "Jamal Carvalho (S2'15)",
    "Sonali Sridhar",
    "Veronica Hanus (F2'15)",
    "Nick Bergson-Shilcock",
    "Luna Lunapiena (SP2'15)",
    "Benjamin Gilbert (F2'15)",
    "Barak Chamo (F1'15)",
    "Bradley Boccuzzi (S1'15)",
    "Diego Berrocal (F2'15)",
    "Eric Hambro (SP1'15)",
    "Ezekiel Benjamin Smithburg (F2'15)",
    "Giorgio Leveroni (S'14)",
    "Harry Truong (F2'15)",
    "John Hergenroeder (SP2'15)",
    "Kamal Marhubi (S1'15)",
    "Ken Pratt (SP2'15)",
    "Keyan Pishdadian (W2'15)",
    "Carlos Rey (SP2'15)",
    "Miriam Shiffman (F2'15)",
    "David Gomez Urquiza (W2'15)",
    "Andrew Drozdov (SP1'15)",
    "Andrew Desharnais (SP1'16)",
    "Nancy Thomas",
    "Nikki Bee (SP1'15)",
    "Ahmed Abdalla (SP2'15)",
    "Leah Steinberg (F2'15)",
    "Dan Luu (W'13)",
    "Julia Evans (F'13)",
    "Liene Verzemnieks (S2'15)",
    "Lindsey Jacks (F1'15)",
    "Margo Smith (F2'14)",
    "Mark Dominus",
    "Nat Welch (SP2'15)",
    "Nicholas Cassleman (F2'14)",
    "Samantha Goldstein (S1'15)",
    "Robert Malko (SP1'15)",
    "Dazhong John Xia (F1'15)",
    "Carlos Sánchez Serrano (S'14)",
    "Serena Peruzzo (SP1'15)",
    "Shad William Hopson (F1'15)",
    "Serban Porumbescu (SP1'15)",
    "Matthias Elliott (F2'15)",
  ]

  vip_yes_prefixes = [
    "GET EXCITED!! ",
    "AWWW YISS!! ",
    "YASSSSS HENNY! ",
    "OMG OMG OMG ",
    "HYPE HYPE HYPE HYPE HYPE ",
    "WOW THIS IS AWESOME: ",
    "YEAAAAAAHHH!!!! :tada: ",
  ]

  vip_no_postfixes = [
    " :confounded:",
    " Bummer!",
    " Oh no!!",
  ]

  def confirm(self, event, sender_full_name, decision):
    # Temporary kludge to add a 'maybe' array to legacy events. Can be removed after
    # all currently logged events have passed.
    if ('maybe' not in event.keys()):
      event['maybe'] = [];

    # If they're in a different response list, take them out of it.
    for response in self.responses.keys():
      # prevent duplicates if replying multiple times
      if (response == decision):
        # if they're already in that list, nothing to do
        if (sender_full_name not in event[response]):
          event[response].append(sender_full_name)
      # else, remove all instances of them from other response lists.
      elif sender_full_name in event[response]:
        event[response] = [value for value in event[response] if value != sender_full_name]

    return event

  def attempt_confirm(self, event, sender_full_name, decision, limit):
    if decision == 'yes' and limit:
      available_seats = limit - len(event['yes'])
      # In this case, we need to do some extra checking for the attendance limit.
      if (available_seats - 1 < 0):
        raise LimitReachedException()

    return self.confirm(event, sender_full_name, decision)

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    event = kwargs.pop('event')
    decision = kwargs.pop('decision').lower()
    sender_full_name = kwargs.pop('sender_full_name')

    limit = event['limit']

    vip_prefix = ''
    vip_postfix = ''

    # TODO:
    # if (this.yes_no_ambigous()):
    #   return RSVPCommandResponse("Yes no yes_no_ambigous", events)

    try:
      event = self.attempt_confirm(event, sender_full_name, decision, limit)

      if sender_full_name in self.vips:
        if decision == 'yes':
          vip_prefix = random.choice(self.vip_yes_prefixes)
        else:
          vip_postfix = random.choice(self.vip_no_postfixes)

      # Update the events dict with the new event.
      events[event_id] = event
      response_string = self.responses.get(decision) % sender_full_name
      response_string = vip_prefix + response_string + vip_postfix
      return RSVPCommandResponse(events, RSVPMessage('stream', response_string))

    except LimitReachedException:
      return RSVPCommandResponse(events, RSVPMessage('stream', strings.ERROR_LIMIT_REACHED))


class RSVPSetLimitCommand(RSVPEventNeededCommand):
  regex = r'set limit (?P<limit>\d+)$'

  def run(self, events, *args, **kwargs):

    event = kwargs.pop('event')
    attendance_limit = int(kwargs.pop('limit'))
    event['limit'] = attendance_limit
    return RSVPCommandResponse(events, RSVPMessage('stream', strings.MSG_ATTENDANCE_LIMIT_SET % attendance_limit))


class RSVPSetDateCommand(RSVPEventNeededCommand):
  regex = r'set date (?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<year>\d{4})$'

  def validate_future_date(self, day, month, year):
    today = datetime.date.today()

    try:
      date = datetime.date(year, month, day)
    except ValueError:
      return False

    return date >= today

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    event_id = kwargs.pop('event_id')
    day = kwargs.pop('day')
    month = kwargs.pop('month')
    year = kwargs.pop('year')

    day, month, year = int(day), int(month), int(year)

    if self.validate_future_date(day, month, year):
      event['date'] = str(datetime.date(year, month, day))
      events[event_id] = event
      body = strings.MSG_DATE_SET % (month, day, year)
    else:
      body = strings.ERROR_DATE_NOT_VALID % (month, day, year)

    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPSetTimeCommand(RSVPEventNeededCommand):
  regex = r'set time (?P<hours>\d{1,2})\:(?P<minutes>\d{1,2})$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    hours, minutes = int(kwargs.pop('hours')), int(kwargs.pop('minutes'))

    if hours in range(0, 24) and minutes in range(0, 60):
      """
      We'll store the time as the number of seconds since 00:00
      """
      events[event_id]['time'] = '%02d:%02d' % (hours, minutes)
      body = strings.MSG_TIME_SET % (hours, minutes)
    else:
      body = strings.ERROR_TIME_NOT_VALID % (hours, minutes)

    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPSetTimeAllDayCommand(RSVPEventNeededCommand):
  regex = r'set time allday$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    events[event_id]['time'] = None
    return RSVPCommandResponse(events, RSVPMessage('stream', strings.MSG_TIME_SET_ALLDAY))


class RSVPSetStringAttributeCommand(RSVPEventNeededCommand):
  regex = r'set (?P<attribute>(place|description)) (?P<value>.+)$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    attribute = kwargs.pop('attribute')
    value = kwargs.pop('value')

    events[event_id][attribute] = value

    body = strings.MSG_STRING_ATTR_SET % (attribute, value)
    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPPingCommand(RSVPEventNeededCommand):
  regex = r'^({key_word} ping)$|({key_word} ping (?P<message>.+))$'

  def __init__(self, prefix, *args, **kwargs):
    self.regex = self.regex.format(key_word=prefix)

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    message = kwargs.get('message')

    body = "**Pinging all participants who RSVP'd!!**\n"

    for participant in event['yes']:
      body += "@**%s** " % participant

    for participant in event['maybe']:
      body += "@**%s** " % participant

    if message:
      body += ('\n' + message)

    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPCreditsCommand(RSVPEventNeededCommand):
  regex = r'credits$'

  def run(self, events, *args, **kwargs):

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
    ]

    testers = ["Nikki Bee (SP2'15)", "Anthony Burdi (SP1'15)", "Noella D'sa (SP2'15)", "Mudit Ameta (SP2'15)"]

    body = "The RSVPBot was created by @**Carlos Rey (SP2'15)**\nWith **contributions** from:\n\n"

    body += '\n '.join(contributors)

    body += "\n\n and invaluable test feedback from:\n\n"
    body += '\n '.join(testers)

    body += "\n\nThe code for **RSVPBot** is available at https://github.com/kokeshii/RSVPBot"

    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPSummaryCommand(RSVPEventNeededCommand):
  regex = r'(summary$|status$)'

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')

    limit_str = 'No Limit!'

    if event['limit']:
      limit_str = '%d/%d spots left' % (event['limit'] - len(event['yes']), event['limit'])

    summary_table = '**%s**' % (event['name'])
    summary_table += '\t|\t\n:---:|:---:\n**What**|%s\n**When**|%s @ %s\n**Where**|%s\n**Limit**|%s\n'
    summary_table = summary_table % (
      event['description'] or 'N/A',
      event['date'],
      event['time'] or '(All day)',
      event['place'] or 'N/A',
      limit_str
    )

    confirmation_table = 'YES ({}) |NO ({}) |MAYBE({}) \n:---:|:---:|:---:\n'

    confirmation_table = confirmation_table.format(len(event['yes']), len(event['no']), len(event['maybe']))

    row_list = map(None, event['yes'], event['no'], event['maybe'])

    for row in row_list:
      confirmation_table += '{}|{}|{}\n'.format(
        '' if row[0] is None else row[0],
        '' if row[1] is None else row[1],
        '' if row[2] is None else row[2]
      )
    else:
      confirmation_table += '\t|\t'

    body = summary_table + '\n\n' + confirmation_table
    return RSVPCommandResponse(events, RSVPMessage('stream', body))
