RSVPBot
=======
[![Build Status](https://travis-ci.org/kokeshii/RSVPBot.svg?branch=master)](https://travis-ci.org/kokeshii/RSVPBot)

This is a simple Zulip bot that converts a Zulip conversation into an event context.
People can then use simple commands to rsvp to an event, set the hour, time, place, and easily ping every person who RSVP'ed.

## Contributing

* Make your pull requests to the `dev` branch
* Write tests for any new command or feature introduced
* Make sure the requirements.txt file is kept up to date
* Make sure any new messages that the bot sends publicly or privately follow the [RC Social Rules](https://www.recurse.com/manual#sub-sec-social-rules). It takes a village, people!
* New features are TOTALLY AWESOME, but RSVPBot has a few [open issues](https://github.com/kokeshii/RSVPBot/issues) you can take a look at if you want to get familiarized with the code or you're looking for ideas on how to contribute.
* HAVE FUN PEOPLE YAY

## Environment Variables

```
# Required
export ZULIP_RSVP_EMAIL="<bot-email>"
export ZULIP_RSVP_KEY="<bot-key>"

# Optional
export ZULIP_RSVP_SITE="https://your-zulip-site.com"  # default is https://zulip.com
export ZULIP_KEY_WORD="rsvp"                          # default is rsvp
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/file" # default is None
export GOOGLE_CALENDAR_ID="abd123@group.calendar.com" # default is None
```

To get set up with Google Application Credentials, see [the Google Credentials Setup Instructions](/google_calendar_instructions.md#google-application-credentials).

## Running
First, make sure python requirements are installed:

`pip install -r requirements.txt`

Then, to run the bot:

`python bot.py`

#### Updating User Email mapping
RSVPBot stores a mapping of email addresses to names, which is updated every time a
`realm_user` event is received. Since rsvp responses are stored by email address, this
mapping is used to convert the email addresses into names for commands like `rsvp ping`
and `rsvp summary`. If running this bot for the first time, you can run

```
python zulip_users.py
```

which will download all users/email addresses from zulip and populate the json
file dictionary. This command is safe to run multiple times.

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
`rsvp move <destination_url>`|Moves this event to another stream/topic. Requires full URL for the destination (e.g.'https://zulip.com/#narrow/stream/announce/topic/All.20Hands.20Meeting') (can only be called by the caller of `rsvp init`)
`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.
`rsvp credits`|Lists all the awesome people that made RSVPBot a reality.
