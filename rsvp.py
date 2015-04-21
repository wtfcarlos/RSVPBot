from __future__ import with_statement
import re
import json

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

    # Match against the most basic command:
    # rsvp init.


    if re.match(r'^rsvp init$', content):
      body = self.cmd_rsvp_init(message)
    elif re.match(r'^rsvp help$', content):
      body = self.cmd_rsvp_help(message)
    elif re.match(r'^rsvp cancel$', content):
      body = self.cmd_rsvp_cancel(message)

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

  def cmd_rsvp_init(self, message):

    subject = message['subject']
    body = 'This thread is now an RSVPBot event! Type `rsvp help` for more options.'
    event = self.get_this_event(message)

    if event:
      # Event already exists, error message, we can't initialize twice.
      body = "Oops! This thread is already an RSVPBot event!"
    else:
      # Update the dictionary with the new event and commit.
      self.events.update(
        {
          self.event_id(message): {
            'name': subject,
            'creator': message['sender_id']
          }
        }
      )
      self.commit_events()

    return body

  def cmd_rsvp_help(self, message):
    body = """**Command**|**Description**\n--- | ---\n**`rsvp yes`**|Marks **you** as attending this event.\n**`rsvp no`**|Marks you as **not** attending this event.\n`rsvp init`|Initializes a thread as an RSVPBot event. Must be used before any other command.\n`rsvp help`|Shows this handy table.|\n`rsvp set time HH:mm`|Sets the time for this event (24-hour format) (optional)|\n`rsvp set date mm/dd/yyyy`|Sets the date for this event (optional)|\n`rsvp set place PLACE_NAME`|Sets the place for this event to PLACE_NAME (optional)\n`rsvp cancel`|Cancels this event (can only be called by the caller of `rsvp init`)\n`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.\n\nIf the event has a date and time, RSVPBot will automatically remind everyone who RSVP'd yes 10 minutes before the event gets started."""
    return body


  def cmd_rsvp_cancel(self, message):

    event = self.get_this_event(message)
    event_id = self.event_id(message)

    print 'this is cancel!', event

    if not event:
      # The event does not exist. We cannot cancel it!
      body = "This thread is not an RSVPBot event!"
    else:

      # Check if the issuer of this command is the event's original creator.
      # Only he can delete the event.

      creator = event['creator']

      if creator == message['sender_id']:
        body = "The event has been canceled!"
        self.events.pop(event_id)
        self.commit_events()
      else:
        body = "Oops! You cannot cancel this event! You're not this event's original creator! Only he can cancel it."
      # TODO: Notify everyone.

    return body




  def normalize_whitespace(self, content):
    # Strips trailing and leading whitespace, and normalizes contiguous 
    # Whitespace with a single space.
    content = content.strip()
    content = re.sub(r'\s+', ' ', content)
    return content