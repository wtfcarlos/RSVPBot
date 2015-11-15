#! /usr/local/bin/python
import zulip
import json
import requests
import random
import os

import rsvp


class bot():
    ''' bot takes a zulip username and api key, a word or phrase to respond to, a search string for giphy,
        an optional caption or list of captions, and a list of the zulip streams it should be active in.
        it then posts a caption and a randomly selected gif in response to zulip messages.
     '''
    def __init__(self, zulip_username, zulip_api_key, key_word, subscribed_streams=[], zulip_site=None):
        self.username = zulip_username
        self.api_key = zulip_api_key
        self.site = zulip_site
        self.key_word = key_word.lower()
        self.subscribed_streams = subscribed_streams
        self.client = zulip.Client(zulip_username, zulip_api_key, site=zulip_site)
        self.subscriptions = self.subscribe_to_streams()
        self.rsvp = rsvp.RSVP(key_word)


    @property
    def streams(self):
        ''' Standardizes a list of streams in the form [{'name': stream}]
        '''
        if not self.subscribed_streams:
            streams = [{'name': stream['name']} for stream in self.get_all_zulip_streams()]
            return streams
        else: 
            streams = [{'name': stream} for stream in self.subscribed_streams]
            return streams


    def get_all_zulip_streams(self):
        ''' Call Zulip API to get a list of all streams
        '''
        response = requests.get(self.client.base_url + 'v1/streams', auth=(self.username, self.api_key))
        if response.status_code == 200:
            return response.json()['streams']
        elif response.status_code == 401:
            raise RuntimeError('check yo auth')
        else:
            raise RuntimeError(':( we failed to GET streams.\n(%s)' % response)


    def subscribe_to_streams(self):
        ''' Subscribes to zulip streams
        '''
        self.client.add_subscriptions(self.streams)


    def respond(self, message):
        ''' Now we have an event dict, we should analyze it completely.
        '''
        message = self.rsvp.process_message(message)

        if message:
            self.send_message(message)
            
    def send_message(self, msg):
        ''' Sends a message to zulip stream
        '''

        self.client.send_message({
            "type": "stream",
            "subject": msg["subject"],
            "to": msg['display_recipient'],
            "content": msg['body']
        })


    def main(self):
        ''' Blocking call that runs forever. Calls self.respond() on every event received.
        '''
        self.client.call_on_each_message(lambda msg: self.respond(msg))


''' The Customization Part!
    
    Create a zulip bot under "settings" on zulip.
    Zulip will give you a username and API key
    key_word is the text in Zulip you would like the bot to respond to. This may be a 
        single word or a phrase.
    search_string is what you want the bot to search giphy for.
    caption may be one of: [] OR 'a single string' OR ['or a list', 'of strings']
    subscribed_streams is a list of the streams the bot should be active on. An empty 
        list defaults to ALL zulip streams

'''

zulip_username = os.environ['ZULIP_RSVP_EMAIL']
zulip_api_key = os.environ['ZULIP_RSVP_KEY']
zulip_site = os.getenv('ZULIP_RSVP_SITE', None)
key_word = 'rsvp'

sandbox_stream =  os.getenv('ZULIP_RSVP_SANDBOX_STREAM', 'test-bot')
subscribed_streams = [sandbox_stream]

new_bot = bot(zulip_username, zulip_api_key, key_word, subscribed_streams, zulip_site=zulip_site)
new_bot.main()