import re

class RSVP(object):

	def process_message(self, message):
		return self.route(message)


	def route(self, message):

		content = message['content']
		content = self.normalize_whitespace(content)

		# Match against the most basic command:
		# rsvp init.

		print 'The content of the message is: ', content

		if re.match(r'^rsvp init$', content):
			return self.cmd_rsvp_init(message)
		elif re.match(r'^rsvp help$', content):
			return self.cmd_rsvp_help(message)

		return None
		
	def create_message_from_message(self, message, body):
		return {
    	'subject': message['subject'],
      'display_recipient': message['display_recipient'],
      'body': body
    }

	def cmd_rsvp_init(self, message):

		subject = message['subject']

		body = 'This thread is now an RSVPBot event! Type `rsvp help` for more options.'

		return self.create_message_from_message(message, body)

	def cmd_rsvp_help(self, message):

		body = """**Command**|**Description**\n--- | ---\n**`rsvp yes`**|Marks **you** as attending this event.\n**`rsvp no`**|Marks you as **not** attending this event.\n`rsvp init`|Initializes a thread as an RSVPBot event. Must be used before any other command.\n`rsvp help`|Shows this handy table.|\n`rsvp set time HH:mm`|Sets the time for this event (24-hour format) (optional)|\n`rsvp set date mm/dd/yyyy`|Sets the date for this event (optional)|\n`rsvp set place PLACE_NAME`|Sets the place for this event to PLACE_NAME (optional)\n`rsvp cancel`|Cancels this event (can only be called by the caller of `rsvp init`)\n`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.\n"""

		return self.create_message_from_message(message, body)

	def normalize_whitespace(self, content):
		# Strips trailing and leading whitespace, and normalizes contiguous 
		# Whitespace with a single space.
		content = content.strip()
		content = re.sub(r'\s+', ' ', content)
		return content