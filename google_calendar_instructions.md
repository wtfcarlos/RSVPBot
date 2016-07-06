# RSVPBot + Google Calendar
RSVPBot has an optional feature that allows users to create an event on a Google Calendar.
Once added to the calendar, changes to the event (things like `date`, `time`, `duration`,
`location`) will be reflected on the calendar. Additionally, people who have replied with
`rsvp yes` or a similar affirmative rsvp will be added as attendees for the calendar event
with a status of attending. Similarly, people who have rsvp'd with `rsvp maybe` will be added
as attendees who are maybe attending.

In order to set this up, you'll have to:

* Set up a Google Service Account
* Set two environment variables
* Give an email address from your Google Service permission to create events on the
Google Calendar.

## Google Application Credentials
1. Go to the [Google Developer Console](
https://console.developers.google.com/projectselector/permissions/serviceaccounts)
and create a new project if needed.
2. Click the **Create Service Account** button to create a new project and service account.
3. When you're creating the new service account, make sure to check the box to
**download a new private key file as a JSON file**.
4. Download the key file, and put it somewhere safe.
5. Set the path to this file in an environment variable:
`export GOOGLE_APPLICATION_CREDENTIALS="/path/to/file"`
6. Also note the **Service account ID**, which will look like an email address and will be
needed later.

## Calendar
### Calendar ID Environment Variable
1. Go to the calendar you want the bot to be able to add events to.
2. Go to the **Calendar Settings** of this calendar.
3. Look for the **Calendar Address** section, where you.ll find something like:
`(Calendar ID: cal_id@group.calendar.google.com)`
4. Set this value in an environment variable:
`export GOOGLE_CALENDAR_ID="cal_id@group.calendar.google.com"`

### Permissions
1. Go to the "Share this Calendar" tab of the same Calendar Settings page used previously
2. Go to the "Share with specific people" section.
3. For the person's email address, use the Service account ID from earlier.
4. For permissions, select "Make changes to events".
5. Click "Add Person".
