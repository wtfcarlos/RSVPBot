#! /usr/local/bin/python
import os

import zulip

import rsvp
import zulip_users


class Bot():
    """ bot takes a zulip username and api key, a word or phrase to respond to, a search string for giphy,
        an optional caption or list of captions, and a list of the zulip streams it should be active in.
        it then posts a caption and a randomly selected gif in response to zulip messages.
     """
    def __init__(self, zulip_username, zulip_api_key, key_word, subscribed_streams=None, zulip_site=None):
        self.key_word = key_word.lower()
        self.subscribed_streams = subscribed_streams or []
        self.client = zulip.Client(zulip_username, zulip_api_key, site=zulip_site)
        self.client._register('get_users', method='GET', url='users')
        self.subscriptions = self.subscribe_to_streams()
        self.rsvp = rsvp.RSVP(key_word)

    @property
    def streams(self):
        """Standardizes a list of streams in the form [{'name': stream}]."""
        if not self.subscribed_streams:
            streams = [{'name': stream['name']} for stream in self.get_all_zulip_streams()]
            return streams
        else:
            streams = [{'name': stream} for stream in self.subscribed_streams]
            return streams

    def get_all_zulip_streams(self):
        """Call Zulip API to get a list of all streams."""
        response = self.client.get_streams()
        if response['result'] == 'success':
            return response['streams']
        else:
            raise RuntimeError('check yo auth')

    def subscribe_to_streams(self):
        """Subscribes to zulip streams."""
        self.client.add_subscriptions(self.streams)

    def process(self, event):
        if event['type'] == 'realm_user':
            zulip_users.update_zulip_user_dict(event['person'], self.client)
        elif event['type'] == 'message':
            self.respond(event['message'])

    def respond(self, message):
        """Now we have an event dict, we should analyze it completely."""

        replies = self.rsvp.process_message(message)

        for reply in replies:
            if reply:
                self.send_message(reply)

    def send_message(self, msg):
        """Sends a message to zulip stream or user."""
        msg_to = msg['display_recipient']
        if msg['type'] == 'private':
            msg_to = msg.get('sender_email') or msg_to

        self.client.send_message({
            "type": msg['type'],
            "subject": msg["subject"],
            "to": msg_to,
            "content": msg['body']
        })

    def main(self):
        """Blocking call that runs forever. Calls self.respond() on every event received."""
        self.client.call_on_each_event(self.process, ['message', 'realm_user'])


""" The Customization Part!

    Create a zulip bot under "settings" on zulip.
    Zulip will give you a username and API key
    key_word is the text in Zulip you would like the bot to respond to. This may be a
        single word or a phrase.
    search_string is what you want the bot to search giphy for.
    caption may be one of: [] OR 'a single string' OR ['or a list', 'of strings']
    subscribed_streams is a list of the streams the bot should be active on. An empty
        list defaults to ALL zulip streams

"""
if __name__ == "__main__":
    ZULIP_USERNAME = os.environ['ZULIP_RSVP_EMAIL']
    ZULIP_API_KEY = os.environ['ZULIP_RSVP_KEY']
    ZULIP_SITE = os.getenv('ZULIP_RSVP_SITE', 'https://recurse.zulipchat.com')
    KEY_WORD = os.getenv('ZULIP_KEY_WORD', 'rsvp')
    SANDBOX_STREAM = os.getenv('ZULIP_RSVP_SANDBOX_STREAM', None)
    SUBSCRIBED_STREAMS = []
    new_bot = Bot(
        ZULIP_USERNAME,
        ZULIP_API_KEY,
        KEY_WORD,
        SUBSCRIBED_STREAMS,
        ZULIP_SITE,
    )
    new_bot.main()
