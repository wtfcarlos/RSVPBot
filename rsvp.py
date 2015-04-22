from __future__ import with_statement
import re
import json

ERROR_NOT_AN_EVENT = "This thread is not an RSVPBot event!. Type `rsvp init` to make it into an event."
ERROR_NOT_AUTHORIZED_TO_DELETE = "Oops! You cannot cancel this event! You're not this event's original creator! Only he can cancel it."
ERROR_ALREADY_AN_EVENT = "Oops! This thread is already an RSVPBot event!"

class RSVP(object):

  def __init__(self):
    self.filename = 'events.json'

    with open(self.filename, "r") as f:
      try:
        self.events = json.load(f)
      except ValueError:
        self.events = {}

  def commit_events(self):
    with open(self.filename, 'w+') as f:
      json.dump(self.events, f)

  def __exit__(self, type, value, traceback):
    self.commit_events()

  def get_this_event(self, message):
    event_id = self.event_id(message)
    return self.events.get(event_id)

  def process_message(self, message):
    return self.route(message)

  def route(self, message):

    content = message['content']
    content = self.normalize_whitespace(content)
    body = None

    if re.match(r'^rsvp init$', content):
      body = self.cmd_rsvp_init(message)
    elif re.match(r'^rsvp help$', content):
      body = self.cmd_rsvp_help(message)
    elif re.match(r'^rsvp cancel$', content):
      body = self.cmd_rsvp_cancel(message)
    elif re.match(r'^rsvp yes$', content):
      body = self.cmd_rsvp_confirm(message, 'yes')
    elif re.match(r'^rsvp no$', content):
      body = self.cmd_rsvp_confirm(message, 'no')
    elif re.match(r'^rsvp summary$', content):
      body = self.cmd_rsvp_summary(message)

    if body:
      return self.create_message_from_message(message, body)
    else:
      return None
    
  def create_message_from_message(self, message, body):
    return {
      'subject': message['subject'],
      'display_recipient': message['display_recipient'],
      'body': body
    }


  def event_id(self, message):
    return u'{}/{}'.format(message['display_recipient'], message['subject'])

  def cmd_rsvp_summary(self, message):
    event = self.get_this_event(message)
    event_id = self.event_id(message)

    if event:
      confirmation_table = 'YES ({}) |NO ({}) \n:---:|:---:\n'
      confirmation_table = confirmation_table.format(len(event['yes']), len(event['no']))

      row_list = map(None, event['yes'], event['no'])

      for row in row_list:
        confirmation_table += '{}|{}\n'.format(
          '' if row[0] is None else row[0],
          '' if row[1] is None else row[1]
        )

      body = confirmation_table
    else:
      body = ERROR_NOT_AN_EVENT

    return body

  def cmd_rsvp_confirm(self, message, decision):
    # The event must exist.
    event = self.get_this_event(message)
    event_id = self.event_id(message)

    other_decision = 'no' if decision == 'yes' else 'yes'

    body = None

    if event:
      # Get the sender's name
      sender_name = message['sender_full_name']

      # Is he already in the list of attendees?
      if sender_name not in event[decision]:
        self.events[event_id][decision].append(sender_name)
        body = u'@**{}** is {} attending!'.format(sender_name, '' if decision == 'yes' else '**not**')

      # We need to remove him from the other decision's list, if he's there.
      if sender_name in event[other_decision]:
        self.events[event_id][other_decision].remove(sender_name)

      self.commit_events()
    else:
      body = ERROR_NOT_AN_EVENT

    return body

  def cmd_rsvp_init(self, message):

    subject = message['subject']
    body = 'This thread is now an RSVPBot event! Type `rsvp help` for more options.'
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
            'description': '',
            'creator': message['sender_id'],
            'yes': [],
            'no': []
          }
        }
      )
      self.commit_events()

    return body

  def cmd_rsvp_help(self, message):
    body = """**Command**|**Description**\n--- | ---\n**`rsvp yes`**|Marks **you** as attending this event.\n**`rsvp no`**|Marks you as **not** attending this event.\n`rsvp init`|Initializes a thread as an RSVPBot event. Must be used before any other command.\n`rsvp help`|Shows this handy table.|\n`rsvp set time HH:mm`|Sets the time for this event (24-hour format) (optional)|\n`rsvp set date mm/dd/yyyy`|Sets the date for this event (optional)|\n`rsvp set description DESCRIPTION`|Sets this event's description to DESCRIPTION (optional)\n`rsvp set place PLACE_NAME`|Sets the place for this event to PLACE_NAME (optional)\n`rsvp cancel`|Cancels this event (can only be called by the caller of `rsvp init`)\n`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.\n\nIf the event has a date and time, RSVPBot will automatically remind everyone who RSVP'd yes 10 minutes before the event gets started."""
    return body


  def cmd_rsvp_cancel(self, message):

    event = self.get_this_event(message)
    event_id = self.event_id(message)

    if not event:
      # The event does not exist. We cannot cancel it!
      body = ERROR_NOT_AN_EVENT
    else:

      # Check if the issuer of this command is the event's original creator.
      # Only he can delete the event.

      creator = event['creator']

      if creator == message['sender_id']:
        body = "The event has been canceled!"
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