from __future__ import with_statement
import re
import json
import time
import datetime

ERROR_NOT_AN_EVENT = "This thread is not an RSVPBot event!. Type `rsvp init` to make it into an event."
ERROR_NOT_AUTHORIZED_TO_DELETE = "Oops! You cannot cancel this event! You're not this event's original creator! Only he can cancel it."
ERROR_ALREADY_AN_EVENT = "Oops! This thread is already an RSVPBot event!"
ERROR_TIME_NOT_VALID = "Oops! **%02d:%02d** is not a valid time!"
ERROR_DATE_NOT_VALID = "Oops! **%02d/%02d/%04d** is not a valid date in the **future**!"
ERROR_INVALID_COMMAND = "`rsvp set %s` is not a valid RSVPBot command! Type `rsvp help` for the correct syntax."
ERROR_LIMIT_REACHED = "Oh no! The **limit** for this event has been reached!"

MSG_INIT_SUCCESSFUL = 'This thread is now an RSVPBot event! Type `rsvp help` for more options.'
MSG_DATE_SET = 'The date for this event has been set to **%02d/%02d/%04d**!\n`rsvp help` for more options.'
MSG_TIME_SET = 'The time for this event has been set to **%02d:%02d**!.\n`rsvp help` for more options.'
MSG_STRING_ATTR_SET = "The %s for this event has been set to **%s**!\n`rsvp help` for more options."
MSG_ATTENDANCE_LIMIT_SET = "The attendance limit for this event has been set to **%d**! Hurry up and `rsvp yes` now!.\n`rsvp help` for more options"
MSG_EVENT_CANCELED = "The event has been canceled!"
MSG_YES_NO_CONFIRMED = u'@**%s** is %s attending!'

class RSVP(object):

  def __init__(self, filename='events.json'):
    """
    When created, this instance will try to open self.filename. It will always
    keep a copy in memory of the whole events dictionary and commit it when necessary.
    """
    self.filename = filename

    try:
      with open(self.filename, "r") as f:
        try:
          self.events = json.load(f)
        except ValueError:
          self.events = {}
    except IOError:
      self.events = {}

  def commit_events(self):
    """
    Write the whole events dictionary to the filename file.
    """
    with open(self.filename, 'w+') as f:
      json.dump(self.events, f)

  def __exit__(self, type, value, traceback):
    """
    Before the program terminates, commit events.
    """
    self.commit_events()

  def get_this_event(self, message):
    """
    Returns the event relevant to this Zulip thread
    """
    event_id = self.event_id(message)
    return self.events.get(event_id)

  def process_message(self, message):
    """
    Processes the received message and returns a new message, to send back to the user.
    """
    body = self.route(message)
    return self.create_message_from_message(message, body)

  def route(self, message):
    """
    To be a valid rsvp command, the string must start with the string rsvp.
    To ensure that we can match things exactly, we must remove the extra whitespace.
    We then pattern-match it with every known command pattern.
    If there's absolutely no match, we return None, which, for the purposes of this program,
    means no reply.
    """
    content = message['content']
    content = self.normalize_whitespace(content)

    if content.startswith('rsvp'):

      """
      Only init and help don't need an RSVPBot context (event) to exist
      """

      if re.match(r'^rsvp init$', content):
        return self.cmd_rsvp_init(message)
      elif re.match(r'^rsvp help$', content):
        return self.cmd_rsvp_help()
      else:
        """
        All the other commands require an event to exist.
        """
        event = self.get_this_event(message)
        event_id = self.event_id(message)

        if event:
          if re.match(r'^rsvp cancel$', content):
            return self.cmd_rsvp_cancel(event_id, sender_id=message['sender_id'])
          elif re.match(r'^rsvp yes$', content):
            return self.cmd_rsvp_confirm(message, event_id, 'yes')
          elif re.match(r'^rsvp no$', content):
            return self.cmd_rsvp_confirm(message, event_id, 'no')
          elif re.match(r'^rsvp summary$', content):
            return self.cmd_rsvp_summary(event_id)
          elif re.match(r'^rsvp set', content):
            """
            The command doesn't match the 'simple' commands, time to match against composite commands.
            """
            content = content.replace('rsvp set ', '')
            match = re.match(r'^time (?P<hours>\d{1,2})\:(?P<minutes>\d{1,2})$', content)

            if match:
              return self.cmd_rsvp_set_time(
                event_id,
                hours=match.group('hours'),
                minutes=match.group('minutes')
              )

            match = re.match(r'^date (?P<month>\d+)/(?P<day>\d+)/(?P<year>\d{4})$', content)

            if match:
              return self.cmd_rsvp_set_date(
                event_id,
                day=match.group('day'),
                month=match.group('month'),
                year=match.group('year')
              )

            match = re.match(r'^limit (?P<limit>\d+)$', content)
            if match:
              return self.cmd_set_attendance_limit(
                event_id,
                attendance_limit=match.group('limit')
              )


            match = re.match(r'^(?P<attribute>(place|description)) (?P<argument>.*)', content, flags=re.DOTALL)
            
            if match:
              return self.cmd_rsvp_set_string_attribute(
                event_id,
                attribute=match.group('attribute'),
                argument=match.group('argument')
              )

            # ...
            return ERROR_INVALID_COMMAND % (content)

          else:
            return ERROR_NOT_AN_EVENT
    return None

    
  def create_message_from_message(self, message, body):
    """
    Convenience method for creating a zulip response message from a given zulip input message.
    """
    if body:
      return {
        'subject': message['subject'],
        'display_recipient': message['display_recipient'],
        'body': body
      }


  def event_id(self, message):
    """
    An event's identifier is the concatenation of the 'display_recipient'
    (zulip slang for the stream's name)
    and the message's subject (aka the thread's title.)
    """
    return u'{}/{}'.format(message['display_recipient'], message['subject'])


  def cmd_set_attendance_limit(self, event_id, attendance_limit=None):
    attendance_limit = int(attendance_limit)
    self.events[event_id]['limit'] = attendance_limit
    self.commit_events()
    return MSG_ATTENDANCE_LIMIT_SET % (attendance_limit)

  def cmd_rsvp_set_string_attribute(self, event_id, attribute=None, argument=None):
    self.events[event_id][attribute] = argument
    self.commit_events()
    return MSG_STRING_ATTR_SET % (attribute, argument)


  def cmd_rsvp_set_date(self, event_id, day='1', month='1', year='2000'):
    today = datetime.date.today()
    day, month, year = int(day), int(month), int(year)

    if day in range(1, 32) and month in range(1, 13):
      # TODO: Date validation according to month and day.
      if year >= today.year and month >= today.month and day >= today.day:
        date_string = str(datetime.date(year, month, day))
        self.events[event_id]['date'] = date_string
        self.commit_events()
        body = MSG_DATE_SET % (month, day, year)
      else:
        body = ERROR_DATE_NOT_VALID % (month, day, year)
    else:
      body = ERROR_DATE_NOT_VALID % (month, day, year)
    return body

  def cmd_rsvp_set_time(self, event_id, hours='00', minutes='00'):
    """
    Make sure the hours are in their valid range
    """
    hours, minutes = int(hours), int(minutes)

    if hours in range(0, 24) and minutes in range(0, 60):
      """
      We'll store the time as the number of seconds since 00:00
      """
      self.events[event_id]['time'] = '%02d:%02d' % (hours, minutes)
      self.commit_events()
      body = MSG_TIME_SET % (hours, minutes)
    else:
      body = ERROR_TIME_NOT_VALID % (hours, minutes)
    return body

  def cmd_rsvp_summary(self, event_id):
    event = self.events[event_id]

    limit_str = 'No Limit!'

    if event['limit']:
      limit_str = '%d/%d spots left' % (len(event['yes']), event['limit'])

    summary_table = '**%s**' % (event['name'])
    summary_table += '\t|\t\n:---:|:---:\n**What**|%s\n**When**|%s @ %s\n**Where**|%s\n**Limit**|%s\n'
    summary_table = summary_table % (
      event['description'] or 'N/A',
      event['date'],
      event['time'] or '(All day)',
      event['place'] or 'N/A',
      limit_str
    )


    confirmation_table = 'YES ({}) |NO ({}) \n:---:|:---:\n'
    confirmation_table = confirmation_table.format(len(event['yes']), len(event['no']))

    row_list = map(None, event['yes'], event['no'])

    for row in row_list:
      confirmation_table += '{}|{}\n'.format(
        '' if row[0] is None else row[0],
        '' if row[1] is None else row[1]
      )
    else:
      confirmation_table += '\t|\t'

    body = summary_table + '\n\n' + confirmation_table
    return body

  def cmd_rsvp_confirm(self, message, event_id, decision):
    event = self.events[event_id]

    other_decision = 'no' if decision == 'yes' else 'yes'
    # Get the sender's name
    sender_name = message['sender_full_name']

    # Is he already in the list of attendees?
    if sender_name not in event[decision]:

      if decision == 'yes':
        if event['limit']:
          if (len(event['yes']) + 1) <= event['limit']:
            body = MSG_YES_NO_CONFIRMED % (sender_name, '' if decision == 'yes' else '**not**')
            self.events[event_id][decision].append(sender_name)
          else:
            body = ERROR_LIMIT_REACHED
        else:
          self.events[event_id][decision].append(sender_name)
          body = MSG_YES_NO_CONFIRMED % (sender_name, '' if decision == 'yes' else '**not**')

      # We need to remove him from the other decision's list, if he's there.
      if sender_name in event[other_decision]:
        self.events[event_id][other_decision].remove(sender_name)
        self.commit_events()
      
      return body

  def cmd_rsvp_init(self, message):
    subject = message['subject']
    body = MSG_INIT_SUCCESSFUL
    event = self.get_this_event(message)

    if event:
      # Event already exists, error message, we can't initialize twice.
      body = ERROR_ALREADY_AN_EVENT
    else:
      # Update the dictionary with the new event and commit.
      self.events.update(
        {
          self.event_id(message): {
            'name': subject,
            'description': None,
            'place': None,
            'creator': message['sender_id'],
            'yes': [],
            'no': [],
            'time': None,
            'limit': None,
            'date': '%s' % datetime.date.today(),
          }
        }
      )
      self.commit_events()

    return body

  def cmd_rsvp_help(self):

    body = "**Command**|**Description**\n"
    body += "--- | ---\n"
    body += "**`rsvp yes`**|Marks **you** as attending this event.\n"
    body += "**`rsvp no`**|Marks you as **not** attending this event.\n"
    body += "`rsvp init`|Initializes a thread as an RSVPBot event. Must be used before any other command.\n"
    body += "`rsvp help`|Shows this handy table.\n"
    body += "`rsvp set time HH:mm`|Sets the time for this event (24-hour format) (optional)\n"
    body += "`rsvp set date mm/dd/yyyy`|Sets the date for this event (optional, if not explicitly set, the date for the event is the date of the creation of the event, i.e. the call to `rsvp init`)\n"
    body += "`rsvp set description DESCRIPTION`|Sets this event's description to DESCRIPTION (optional)\n"
    body += "`rsvp set place PLACE_NAME`|Sets the place for this event to PLACE_NAME (optional)\n"
    body += "`rsvp set limit LIMIT`|Set the attendance limit for this event to LIMIT."
    body += "`rsvp cancel`|Cancels this event (can only be called by the caller of `rsvp init`)\n"
    body += "`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.\n\n"
    body += "If the event has a date and time, RSVPBot will automatically remind everyone who RSVP'd yes 10 minutes before the event gets started."

    return body


  def cmd_rsvp_cancel(self, event_id, sender_id=None):
    event = self.events[event_id]
    # Check if the issuer of this command is the event's original creator.
    # Only he can delete the event.
    creator = event['creator']

    if creator == sender_id:
      body = MSG_EVENT_CANCELED
      self.events.pop(event_id)
      self.commit_events()
    else:
      body = ERROR_NOT_AUTHORIZED_TO_DELETE
    # TODO: Notify everyone.
    return body


  def normalize_whitespace(self, content):
    # Strips trailing and leading whitespace, and normalizes contiguous 
    # Whitespace with a single space.
    content = content.strip()
    content = re.sub(r'\s+', ' ', content)
    return content