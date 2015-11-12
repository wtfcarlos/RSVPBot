from __future__ import with_statement
import re
import json
import time
import datetime

import commands

ERROR_NOT_AN_EVENT             = "This thread is not an RSVPBot event!. Type `rsvp init` to make it into an event."
ERROR_NOT_AUTHORIZED_TO_DELETE = "Oops! You cannot cancel this event! You're not this event's original creator! Only they can cancel it."
ERROR_ALREADY_AN_EVENT         = "Oops! This thread is already an RSVPBot event!"
ERROR_TIME_NOT_VALID           = "Oops! **%02d:%02d** is not a valid time!"
ERROR_DATE_NOT_VALID           = "Oops! **%02d/%02d/%04d** is not a valid date in the **future**!"
ERROR_INVALID_COMMAND          = "`%s` is not a valid RSVPBot command! Type `rsvp help` for the correct syntax."
ERROR_LIMIT_REACHED            = "Oh no! The **limit** for this event has been reached!"
  
class RSVP(object):

  def __init__(self, key_word, filename='events.json'):
    """
    When created, this instance will try to open self.filename. It will always
    keep a copy in memory of the whole events dictionary and commit it when necessary.
    """
    self.key_word = key_word
    self.filename = filename
    self.command_list = (
      commands.RSVPInitCommand(key_word),
      commands.RSVPHelpCommand(key_word),
      commands.RSVPCancelCommand(key_word),
      commands.RSVPSetLimitCommand(key_word),
      commands.RSVPSetDateCommand(key_word),
      commands.RSVPSetTimeCommand(key_word),
      commands.RSVPSetTimeAllDayCommand(key_word),
      commands.RSVPSetStringAttributeCommand(key_word),
      commands.RSVPSummaryCommand(key_word),
      commands.RSVPPingCommand(key_word),
      commands.RSVPCreditsCommand(key_word),

      # This needs to be at last for fuzzy yes|no checking
      commands.RSVPConfirmCommand(key_word)
    )

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

    event_id = self.event_id(message)

    if content.startswith(self.key_word):
      for command in self.command_list:
        matches = command.match(content)
        if matches:
          kwargs = {
            'event': self.events.get(event_id),
            'event_id': event_id,
            'sender_full_name': message['sender_full_name'],
            'sender_id': message['sender_id'],
            'subject': message['subject'],
          }

          if matches.groupdict():
            kwargs.update(matches.groupdict())

          response = command.execute(self.events, **kwargs)

          self.events = response.events
          self.commit_events()
          return response.body

      return ERROR_INVALID_COMMAND % (content)


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

  def normalize_whitespace(self, content):
    # Strips trailing and leading whitespace, and normalizes contiguous
    # Whitespace with a single space.
    content = content.strip()
    content = re.sub(r'\s+', ' ', content)
    return content
