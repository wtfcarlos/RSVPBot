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


def update_zulip_user_dict(updated_info=None, zulip_client=None):
    """Updates the `zulip_users.json` file.

    If `updated_info` is not provided, it'll make a call to Zulip's /users
    endpoint to get all users and update them all.

    If `updated_info` is provided, it should be the person dict returned by the
    Zulip API in a `realm_user` event. The required keys are `email` and `full_name`.
    """

    with open('zulip_users.json', 'w+') as users_file:
        try:
            zulip_users = json.load(users_file)
        except ValueError:
            zulip_users = {}
        if updated_info:
            new_entry = {updated_info['email']: updated_info['full_name']}
            zulip_users.update(new_entry)
        else:
            client = zulip_client or _get_zulip_client()
            users_response = client.get_users()
            if users_response['result'] == 'success':
                users_from_zulip_api = users_response['members']
                for user in users_from_zulip_api:
                    new_entry = {user['email']: user['full_name']}
                    zulip_users.update(new_entry)
        json.dump(zulip_users, users_file)


def convert_email_to_pingable_name_(email):
    """Looks up email address in `zulip_users.json` file  and returns the user's
    name if they exist in the dict, otherwise, just returns the email address."""

    with open('zulip_users.json', 'r') as users_file:
        zulip_users = json.load(users_file)
    user = zulip_users.get(email)
    return user or email
