import os
from functools import lru_cache
from uuid import UUID

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from postgrest import APIError
from supabase import Client, create_client

load_dotenv()

app = Flask(__name__)


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Create the database client only when a route needs it."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be set")
    return create_client(url, key)


def json_error(message: str, status: int):
    return jsonify({"error": message}), status


def valid_uuid(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def database_error(error: APIError):
    """Translate known registration RPC errors; hide internal database details."""
    message = str(getattr(error, "message", ""))
    code = str(getattr(error, "code", ""))
    details = str(getattr(error, "details", ""))
    diagnostic = " ".join((message, details, code)).lower()
    if "registration_duplicate" in message:
        return json_error("User is already registered for this event", 409)
    if "event_full" in message:
        return json_error("Event has reached capacity", 409)
    if "event_not_found" in message:
        return json_error("Event not found", 404)
    if "user_not_found" in message:
        return json_error("User not found", 404)
    if code == "PGRST202" or "create_event_registration" in diagnostic or "permission denied for function" in diagnostic:
        app.logger.exception("Registration RPC is missing or unavailable: %s", diagnostic)
        return json_error(
            "Registration database setup is incomplete. Apply migrations/001_event_registration_rpc.sql in Supabase and grant EXECUTE to anon.",
            503,
        )
    app.logger.exception("Supabase request failed: %s", message)
    return json_error("Database request failed", 500)


@app.get("/")
def index():
    return jsonify({"name": "Events API", "endpoints": [
        "GET /api/events",
        "GET /api/events/<id>",
        "POST /api/registrations",
        "GET /api/me/registrations?user_id=<uuid>",
        "GET /api/events/<id>/registrations",
    ]})


@app.get("/healthz")
def health_check():
    return jsonify({"status": "ok"}), 200


@app.get("/api/events")
def list_events():
    try:
        response = get_supabase().table("events").select("*").order("title").execute()
        return jsonify(response.data), 200
    except RuntimeError as error:
        return json_error(str(error), 503)
    except APIError as error:
        return database_error(error)


@app.get("/api/events/<event_id>")
def get_event(event_id):
    event_id = valid_uuid(event_id)
    if not event_id:
        return json_error("id must be a valid UUID", 400)
    try:
        response = get_supabase().table("events").select("*").eq("id", event_id).maybe_single().execute()
        if response.data is None:
            return json_error("Event not found", 404)
        return jsonify(response.data), 200
    except RuntimeError as error:
        return json_error(str(error), 503)
    except APIError as error:
        return database_error(error)


@app.post("/api/registrations")
def create_registration():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return json_error("Request body must be a JSON object", 400)
    user_id = valid_uuid(body.get("user_id"))
    event_id = valid_uuid(body.get("event_id"))
    if not user_id or not event_id:
        return json_error("user_id and event_id must be valid UUIDs", 400)

    try:
        # The SQL RPC locks the event row, so concurrent requests cannot
        # overbook an event or create duplicate registrations.
        response = get_supabase().rpc("create_event_registration", {
            "p_user_id": user_id,
            "p_event_id": event_id,
        }).execute()
        registration = response.data
        if isinstance(registration, list):
            registration = registration[0] if registration else None
        if not registration:
            return json_error("Registration could not be created", 500)
        return jsonify(registration), 201
    except RuntimeError as error:
        return json_error(str(error), 503)
    except APIError as error:
        return database_error(error)


@app.get("/api/me/registrations")
def list_user_registrations():
    # With authentication intentionally omitted, the caller supplies user_id.
    user_id = valid_uuid(request.args.get("user_id"))
    if not user_id:
        return json_error("user_id query parameter must be a valid UUID", 400)
    try:
        response = (get_supabase().table("registrations")
                    .select("*, events(*)")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute())
        return jsonify(response.data), 200
    except RuntimeError as error:
        return json_error(str(error), 503)
    except APIError as error:
        return database_error(error)


@app.get("/api/events/<event_id>/registrations")
def list_event_registrations(event_id):
    # This route is public because no authentication/authorization is configured.
    event_id = valid_uuid(event_id)
    if not event_id:
        return json_error("id must be a valid UUID", 400)
    try:
        response = (get_supabase().table("registrations")
                    .select("*, users(id, email, role)")
                    .eq("event_id", event_id)
                    .order("created_at")
                    .execute())
        return jsonify(response.data), 200
    except RuntimeError as error:
        return json_error(str(error), 503)
    except APIError as error:
        return database_error(error)


@app.errorhandler(404)
def not_found(_error):
    return json_error("Endpoint not found", 404)


@app.errorhandler(405)
def method_not_allowed(_error):
    return json_error("Method not allowed", 405)


if __name__ == "__main__":
    # Keep `python app.py` production-safe too (some Render services use this
    # dashboard start command instead of the startCommand in render.yaml).
    os.execvp("gunicorn", ["gunicorn", "app:app", "--config", "gunicorn.conf.py"])
