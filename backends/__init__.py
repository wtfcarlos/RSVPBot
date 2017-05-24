import json

__all__ = ['AbstractBackend', 'FileBackend']

class AbstractBackend(object):

    def __init__(self, *args, **kwargs):
        super(AbstractBackend, self).__init__(*args, **kwargs)

    def get_all_events(self):
        """
        Must return a dictionary with the form:

        {
            "<thread_name_1>": {
                "name": "<event_name>",
                "description": "<description_1>",
                "yes": ["<email_1>", "<email_2>", ...],
                "no": ["<email_1>", "<email_2>", ...],
                "maybe": ["<email_1>", "<email_2>", ...],
                "creator": int(<creator_user_id>),
                "duration": int(<duration_seconds>) or None,
                "place": "<place_name>" or None,
                "time": "<%H:%m>" or None, # refer to http://strftime.org/ for % meaning.
                "date": "<%Y-%m-%d>" or None,
                "limit": int(<max_limit_people>) or None
                "calendar_event": {
                    "html_link": "<cal_event_url>",
                    "id": "<cal_event_id>",
                } or None,
            },
            "<thread_name_2>": {...}
        } or {}
        """
        raise NotImplementedError('You must override the get_all_events method.')


    def commit_events(self, events):
        """
        Should write the events to any long-term storage by any means necessary.
        """
        raise NotImplementedError('You must override the commit_events method.')


class FileBackend(AbstractBackend):

    filename = None

    def __init__(self, filename, *args, **kwargs):
        self.filename = filename
        super(FileBackend, self).__init__(*args, **kwargs)


    def get_all_events(self):
        events = {}
        try:
            with open(self.filename, "r") as f:
                try:
                    events = json.load(f)
                except ValueError as v_exc:
                    pass
        except IOError as io_exc:
            pass

        return events


    def commit_events(self, events):
        """Write the whole events dictionary to the filename file."""
        with open(self.filename, 'w+') as f:
            json.dump(events, f)
