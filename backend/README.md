# Events API

Flask backend using Supabase Postgres. The database setup is in `schema.sql`.
This API intentionally has no authentication or authorization. Anyone who can
reach the API can supply any `user_id`; the events, registrations, and attendee
list are public. In particular, `GET /api/events/<id>/registrations` cannot
enforce the diagram's “organizer only” rule until authentication and
authorization are added.

## Setup

1. Install dependencies: `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and set `SUPABASE_URL` and
   `SUPABASE_PUBLISHABLE_KEY`.
3. Run `schema.sql` in the Supabase SQL Editor.
4. Insert user rows before creating events or registrations. Create event rows
   with `organizer_id`, `title`, and `capacity`.
5. Start the server with `flask --app app run`.

## Deploy on Render

The included `render.yaml` configures a Python web service with Gunicorn and a
`/healthz` health check. Gunicorn reads Render's `PORT` in
`gunicorn.conf.py` and binds to `0.0.0.0`. Push this folder to a Git repository, create a new
Blueprint in Render connected to that repository, and provide `SUPABASE_URL`
and `SUPABASE_PUBLISHABLE_KEY` when Render prompts for the unsynced values.
Render then installs `requirements.txt` and starts
`gunicorn app:app --config gunicorn.conf.py`.

For an existing Render Web Service, use build command
`pip install -r requirements.txt` and start command
`gunicorn app:app --config gunicorn.conf.py`. Add `SUPABASE_URL` and
`SUPABASE_PUBLISHABLE_KEY` in the service's Environment settings.

The database schema creates the diagram's three tables, foreign keys, and
registration uniqueness rule. `POST /api/registrations` calls a narrow SQL
function so duplicate and capacity checks happen atomically. It returns `409`
for an existing registration or a full event. The function is the only anon
write path to registrations; direct inserts are not granted.

## Endpoints

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET | `/api/events` | List events |
| GET | `/api/events/<id>` | Get one event; `404` when missing |
| POST | `/api/registrations` | Register with JSON `{"user_id":"...", "event_id":"..."}`; `201` or `409` |
| GET | `/api/me/registrations?user_id=<uuid>` | List registrations for the supplied user ID, including event details |
| GET | `/api/events/<id>/registrations` | List attendees, including public user fields |

Invalid UUIDs or request bodies return `400`. The current user's route accepts
`user_id` as a query parameter because there is no authenticated identity to
derive from a session.
