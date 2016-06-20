import json
import os

import zulip


def _get_zulip_client():
    username = os.environ['ZULIP_RSVP_EMAIL']
    api_key = os.environ['ZULIP_RSVP_KEY']
    site = os.getenv('ZULIP_RSVP_SITE', 'https://zulip.com')

    client = zulip.Client(username, api_key, site=site)
    client._register('get_users', method='GET', url='users')
    return client


class ZulipUsers(object):
    def __init__(self, filename='zulip_users.json'):
        self.filename = filename

        with open(self.filename, 'r') as users_file:
            try:
                self.zulip_users = json.load(users_file)
            except ValueError:
                self.zulip_users = {}

    def save(self):
        """Write the whole users dictionary to the filename file."""
        with open(self.filename, 'w+') as f:
            json.dump(self.zulip_users, f)

    def convert_email_to_pingable_name(self, email):
        """Looks up email address and returns the user's "pingable name" if they exist
        in the dict, otherwise, just returns the email address."""
        user = self.zulip_users.get(email)
        return user or email


def update_zulip_user_dict(updated_info=None, zulip_client=None):
    """Updates the `zulip_users.json` file.

    If `updated_info` is not provided, it'll make a call to Zulip's /users
    endpoint to get all users and update them all.

    If `updated_info` is provided, it should be the person dict returned by the
    Zulip API in a `realm_user` event. The required keys are `email` and `full_name`.
    """
    zusers = ZulipUsers()
    if updated_info:
        new_entry = {updated_info['email']: updated_info['full_name']}
        zusers.zulip_users.update(new_entry)
    else:
        client = zulip_client or _get_zulip_client()
        users_response = client.get_users()
        if users_response['result'] == 'success':
            users_from_zulip_api = users_response['members']
            for user in users_from_zulip_api:
                new_entry = {user['email']: user['full_name']}
                zusers.zulip_users.update(new_entry)
    zusers.save()
    return zusers


if __name__ == '__main__':
    update_zulip_user_dict()
