RSVPBot
=======
[![Build Status](https://travis-ci.org/kokeshii/RSVPBot.svg?branch=master)](https://travis-ci.org/kokeshii/RSVPBot)

This is a simple Zulip bot that converts a Zulip conversation into an event context.
People can then use simple commands to rsvp to an event, set the hour, time, place, and easily ping every person who RSVP'ed.

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
