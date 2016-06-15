"""Module to add and update events on GOOGLE_CALENDAR_ID."""
import datetime
import os
import re

from apiclient import discovery
import httplib2
from oauth2client.service_account import ServiceAccountCredentials

from util import stream_topic_to_narrow_url

GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None)
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', None)


def add_rsvpbot_event_to_gcal(rsvpbot_event, rsvpbot_event_id):
    """Given an RSVPBot event dict, create a calendar event."""
    event_dict = _format_rsvpbot_event_for_gcal(rsvpbot_event, rsvpbot_event_id)

    return create_event_on_calendar(event_dict, GOOGLE_CALENDAR_ID)


def update_gcal_event(rsvpbot_event, rsvpbot_event_id):
    """Updates an existing calendar event based on an updated rsvpbot event

    It is expected that the rsvp_bot event has an existing calendar event
    id stored so it knows which event to update.
    """
    event_id = rsvpbot_event['calendar_event']['id']
    new_event_details = _format_rsvpbot_event_for_gcal(rsvpbot_event, rsvpbot_event_id)

    return update_event_on_calendar(event_id, new_event_details, GOOGLE_CALENDAR_ID)


def create_event_on_calendar(event_dict, calendar_id):
    """Creates `event_dict` on the given `calendar_id`."""
    service = _get_calendar_service()

    if service and calendar_id:
        calendar = service.calendars().get(calendarId=calendar_id).execute()
        result = {'calendar_name': calendar['summary']}

        event = service.events().insert(
            calendarId=calendar_id,
            body=event_dict,
        ).execute()

        result.update(event)
        return result
    else:
        return None


def update_event_on_calendar(event_id, event_dict, calendar_id):
    """Updates `event_id` on the given `calendar_id`."""
    service = _get_calendar_service()

    if service and calendar_id:
        event = service.events().patch(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_dict
        ).execute()
        return event
    else:
        return None


def _get_calendar_service():
    scopes = ['https://www.googleapis.com/auth/calendar']
    path_to_keyfile = GOOGLE_APPLICATION_CREDENTIALS
    if not path_to_keyfile:
        raise KeyfilePathNotSpecifiedError

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        path_to_keyfile, scopes=scopes)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    return service


def _format_rsvpbot_event_for_gcal(rsvpbot_event, event_id):
    """Convert an RSVPBot event dict into the format needed for
    the Google Calendar API."""

    name = rsvpbot_event.get('name')
    location = rsvpbot_event.get('place')
    description = rsvpbot_event.get('description') or ''

    stream, topic = event_id.split('/')
    description += '\r\rFor more information or to RSVP, see {zulip_url}'.format(
        zulip_url=stream_topic_to_narrow_url(stream, topic))

    date = rsvpbot_event.get('date')
    time = rsvpbot_event.get('time')
    if not (date and time):
        raise DateAndTimeNotSuppliedError

    full_date_string = '{date} {time}'.format(
        date=rsvpbot_event.get('date'),
        time=rsvpbot_event.get('time')
    )

    duration = rsvpbot_event.get('duration')
    if not duration:
        raise DurationNotSuppliedError

    duration = datetime.timedelta(seconds=duration)
    start_date = datetime.datetime.strptime(full_date_string, '%Y-%m-%d %H:%M')
    end_date = start_date + duration

    email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")

    rsvp_yes_attendee_list = [
        {'email': entity, 'response_status': 'accepted'} for entity in rsvpbot_event['yes']
        if email_regex.match(entity)
    ]

    rsvp_maybe_attendee_list = [
        {'email': entity, 'response_status': 'tentative'} for entity in rsvpbot_event['maybe']
        if email_regex.match(entity)
    ]

    calendar_event = {
        'summary': name,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_date.isoformat(),
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': end_date.isoformat(),
            'timeZone': 'America/New_York',
        },
        'attendees': rsvp_yes_attendee_list + rsvp_maybe_attendee_list,
    }
    return calendar_event


class DurationNotSuppliedError(Exception):
    pass


class DateAndTimeNotSuppliedError(Exception):
    pass


class KeyfilePathNotSpecifiedError(Exception):
    pass
