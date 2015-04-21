import re

class RSVP(object):

	def process_message(self, message):
		return self.route(message)


	def route(self, message):

		content = message['content']
		content = self.normalize_whitespace(content)

		# Match against the most basic command:
		# rsvp init.

		if re.match(r'^rsvp init$', content):
			return self.cmd_rsvp_init(message)

		return None
		
	def create_message_from_message(self, message, body):
		return {
    	'subject': message['subject'],
      'display_recipient': message['display_recipient'],
      'body': body
    }

	def cmd_rsvp_init(self, message):
		return self.create_message_from_message(message, "ACK rsvp init")

	def normalize_whitespace(self, content):
		# Strips trailing and leading whitespace, and normalizes contiguous 
		# Whitespace with a single space.
		content = content.strip()
		content = re.sub(r'\s+', ' ', content)
		return content