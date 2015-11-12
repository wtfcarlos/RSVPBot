from __future__ import unicode_literals
import re
import datetime
import random

ERROR_INTERNAL                 = "We're having technical difficulties. Please try again later."
ERROR_NOT_AN_EVENT             = "This thread is not an RSVPBot event!. Type `rsvp init` to make it into an event."
ERROR_NOT_AUTHORIZED_TO_DELETE = "Oops! You cannot cancel this event! You're not this event's original creator! Only he can cancel it."
ERROR_ALREADY_AN_EVENT         = "Oops! This thread is already an RSVPBot event!"
ERROR_TIME_NOT_VALID           = "Oops! **%02d:%02d** is not a valid time!"
ERROR_DATE_NOT_VALID           = "Oops! **%02d/%02d/%04d** is not a valid date in the **future**!"
ERROR_INVALID_COMMAND          = "`rsvp set %s` is not a valid RSVPBot command! Type `rsvp help` for the correct syntax."
ERROR_LIMIT_REACHED            = "Oh no! The **limit** for this event has been reached!"

MSG_INIT_SUCCESSFUL            = 'This thread is now an RSVPBot event! Type `rsvp help` for more options.'
MSG_DATE_SET                   = 'The date for this event has been set to **%02d/%02d/%04d**!\n`rsvp help` for more options.'
MSG_TIME_SET                   = 'The time for this event has been set to **%02d:%02d**!.\n`rsvp help` for more options.'
MSG_TIME_SET_ALLDAY            = 'This is now an all day long event.'
MSG_STRING_ATTR_SET            = "The %s for this event has been set to **%s**!\n`rsvp help` for more options."
MSG_ATTENDANCE_LIMIT_SET       = "The attendance limit for this event has been set to **%d**! Hurry up and `rsvp yes` now!.\n`rsvp help` for more options"
MSG_EVENT_CANCELED             = "The event has been canceled!"

"""

Class that represents a response from an RSVPCommand.
Every call to an RSVPCommand instance's execute() method is expected to return an instance
of this class.

"""
class RSVPCommandResponse(object):
  def __init__(self, body, events):
    self.body = body
    self.events = events


"""
Base class for an RSVPCommand
"""
class RSVPCommand(object):
  regex = None

  def __init__(self, prefix, *args, **kwargs):
    # prefix is the command start the bot listens to, typically 'rsvp'
    self.prefix = r'^' + prefix + r' '
    self.regex = self.prefix + self.regex

  def match(self, input_str):
    return re.match(self.regex, input_str, flags=re.DOTALL)

  def execute(self, events, *args, **kwargs):
    """
    execute() is just a convenience wrapper around __run()
    """
    return self.run(events, *args, **kwargs)

"""
Base class for a command where an event needs to exist prior to execution
"""
class RSVPEventNeededCommand(RSVPCommand):

  def execute(self, events, *args, **kwargs):
    event = kwargs.get('event')
    if event:
      return self.run(events, *args, **kwargs)
    return RSVPCommandResponse(ERROR_NOT_AN_EVENT, events)


class RSVPInitCommand(RSVPCommand):
  regex = r'init$'

  def run(self, events, *args, **kwargs):
    sender_id   = kwargs.pop('sender_id')
    event_id    = kwargs.pop('event_id')
    subject    = kwargs.pop('subject')

    body = MSG_INIT_SUCCESSFUL

    if events.get(event_id):
      # Event already exists, error message, we can't initialize twice.
      body = ERROR_ALREADY_AN_EVENT
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

    return RSVPCommandResponse(body, events)

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
    body += "`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.\n"
    body += "`rsvp credits`|Lists all the awesome people that made RSVPBot a reality.\n"

    return RSVPCommandResponse(body, events)


class RSVPCancelCommand(RSVPEventNeededCommand):
  regex = r'cancel$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    sender_id = kwargs.pop('sender_id')
    event = kwargs.pop('event')

    # Check if the issuer of this command is the event's original creator.
    # Only he can delete the event.
    creator = event['creator']

    if creator == sender_id:
      body = MSG_EVENT_CANCELED
      events.pop(event_id)
    else:
      body = ERROR_NOT_AUTHORIZED_TO_DELETE

    return RSVPCommandResponse(body, events)

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
  ]

  vip_yes_prefixes = [
    "GET EXCITED!! ",
    "AWWW YISS!! ",
    "YASSSSS HENNY! ",
    "OMG OMG OMG "
  ]

  vip_no_postfixes = [
    " :confounded:",
    " Bummer!",
    " Oh no!!"
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
    decision = kwargs.pop('decision')
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
      return RSVPCommandResponse(response_string, events)

    except LimitReachedException:
      return RSVPCommandResponse(ERROR_LIMIT_REACHED, events)

class RSVPSetLimitCommand(RSVPEventNeededCommand):
  regex = r'set limit (?P<limit>\d+)$'

  def run(self, events, *args, **kwargs):

    event = kwargs.pop('event')
    attendance_limit = int(kwargs.pop('limit'))
    event['limit'] = attendance_limit
    return RSVPCommandResponse(MSG_ATTENDANCE_LIMIT_SET % (attendance_limit), events)


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
      body = MSG_DATE_SET % (month, day, year)
    else:
      body = ERROR_DATE_NOT_VALID % (month, day, year)

    return RSVPCommandResponse(body, events)


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
      body = MSG_TIME_SET % (hours, minutes)
    else:
      body = ERROR_TIME_NOT_VALID % (hours, minutes)
      
    return RSVPCommandResponse(body, events)

class RSVPSetTimeAllDayCommand(RSVPEventNeededCommand):
  regex = r'set time allday$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    events[event_id]['time'] = None
    return RSVPCommandResponse(MSG_TIME_SET_ALLDAY, events)

class RSVPSetStringAttributeCommand(RSVPEventNeededCommand):
  regex = r'set (?P<attribute>(place|description)) (?P<value>.+)$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    attribute = kwargs.pop('attribute')
    value = kwargs.pop('value')

    events[event_id][attribute] = value

    body = MSG_STRING_ATTR_SET % (attribute, value)
    return RSVPCommandResponse(body, events)


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
      body += "@*%s* " % participant

    if message:
      body += ('\n' + message)

    return RSVPCommandResponse(body, events)



class RSVPCreditsCommand(RSVPEventNeededCommand):
  regex = r'credits$'

  def run(self, events, *args, **kwargs):

    contributors = ["Mudit Ameta (SP2'15)", "Diego Berrocal (F2'15)", "Shad William Hopson (F1'15)", 
    "Tom Murphy (F2'15)", "Miriam Shiffman (F2'15)", "Anjana Sofia Vakil (F2'15)",
    "Steven McCarthy (SP2'15)]","Kara McNair (F2'15)"]
    testers = ["Nikki Bee (SP2'15)", "Anthony Burdi (SP1'15)", "Noella D'sa (SP2'15)", "Mudit Ameta (SP2'15)"]

    body = "RSVPBot was created by @**Carlos Flores (SP2'15)**\nWith **contributions** from:\n"

    body += ', '.join(contributors)

    body += "\n and invaluable test feedback from:\n"
    body += ', '.join(testers)

    body += "\nThe code for **RSVPBot** is available at https://github.com/kokeshii/RSVPBot"

    return RSVPCommandResponse(body, events)

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
    return RSVPCommandResponse(body, events)

