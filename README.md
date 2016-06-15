RSVPBot
=======
[![Build Status](https://travis-ci.org/kokeshii/RSVPBot.svg?branch=master)](https://travis-ci.org/kokeshii/RSVPBot)

This is a simple Zulip bot that converts a Zulip conversation into an event context.
People can then use simple commands to rsvp to an event, set the hour, time, place, and easily ping every person who RSVP'ed.


## Environment Variables

```
# Required
export ZULIP_RSVP_EMAIL="<bot-email>"
export ZULIP_RSVP_KEY="<bot-key>"

# Optional
export ZULIP_RSVP_SITE="https://your-zulip-site.com"  # default is https://zulip.com
export ZULIP_KEY_WORD="rsvp"                          # default is rsvp

export GOOGLE_CALENDAR_ID="abd123@group.calendar.com" # default is None

# this is a json dump of all but the private key from the downloaded google credentials
export GOOGLE_CREDENTIALS='{"client_x509_cert_url": "xxx", "auth_uri": "xxx", "client_email": "xxx@email.com", "private_key_id": "xxx", "client_id": "xxx", "token_uri": "xxx", "project_id": "xxx", "type": "service_account", "auth_provider_x509_cert_url": "xxx"}'

# the private key from the downloaded google creds.
# Note: this must be entered on multiple lines, rather than one line with \n line breaks.
export GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
sfsjkdfsjhjfhjshajfhsjhfjdskahfjldahsjflhasjflhjslhfjslafhjklsax
fjdkslfjksdljfasdfhjsalhjflhjsdlahfjdlasfhjlahjfkldahjfklhjksdjd
jakflsfdsajklsdfslslskx=
-----END PRIVATE KEY-----
"
```

## Running

`
python bot.py
`

## Testing
`
python tests.py
`

## Commands
**Command**|**Description**
--- | ---
**`rsvp yes`**|Marks **you** as attending this event.
**`rsvp no`**|Marks you as **not** attending this event.
`rsvp init`|Initializes a thread as an RSVPBot event. Must be used before any other command.
`rsvp help`|Shows this handy table.
`rsvp ping`|Pings everyone that has RSVP'd so far.
`rsvp set time HH:mm`|Sets the time for this event (24-hour format) (optional)
`rsvp set date mm/dd/yyyy`|Sets the date for this event (optional, if not explicitly set, the date for the event is the date of the creation of the event, i.e. the call to `rsvp init`)
`rsvp set description DESCRIPTION`|Sets this event's description to DESCRIPTION (optional)
`rsvp set place PLACE_NAME`|Sets the place for this event to PLACE_NAME (optional)
`rsvp set limit LIMIT`|Set the attendance limit for this event to LIMIT. Set LIMIT as 0 for infinite attendees.
`rsvp cancel`|Cancels this event (can only be called by the caller of `rsvp init`)
`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.
`rsvp credits`|Lists all the awesome people that made RSVPBot a reality.
