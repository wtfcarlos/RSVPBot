import re

class RSVP(object):

	def process_event(self, event):
		
		message = event['message']
		content = message['content']
		content = self.normalize_whitespace(content)

		# Now, let's capture all the things!
		route = self.get_route_for_string(content)

		if route:
			route(self, content)
		else:
			# Don't respond if a route could not be found.
			return None


	def get_route_for_string(self, content):

		# Match against the most basic command:
		# rsvp init.

		if re.match(r'^rsvp init$', content):
			return self.cmd_rsvp_init(content)
		

	def cmd_rsvp_init(self, content):
		pass

	def normalize_whitespace(self, content):
		# Strips trailing and leading whitespace, and normalizes contiguous 
		# Whitespace with a single space.
		content = content.strip()
		content = re.sub(r'\s+', ' ', content)
		return content