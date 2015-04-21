import re

class RSVP(object):

	def process_event(self, event):
		return self.route(event)


	def route(self, event):

		message = event['message']
		content = message['content']
		content = self.normalize_whitespace(content)

		# Match against the most basic command:
		# rsvp init.

		if re.match(r'^rsvp init$', content):
			return self.cmd_rsvp_init(event)
		
	def create_message_from_event(self, event, body):
		return {
    	'subject': event['message']['subject'],
      'display_recipient': event['message']['display_recipient'],
      'body': body
    }

	def cmd_rsvp_init(self, event):
		return self.create_message_from_event(event, "ACK rsvp init")

	def normalize_whitespace(self, content):
		# Strips trailing and leading whitespace, and normalizes contiguous 
		# Whitespace with a single space.
		content = content.strip()
		content = re.sub(r'\s+', ' ', content)
		return content