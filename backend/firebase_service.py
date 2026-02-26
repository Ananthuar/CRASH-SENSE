"""
CrashSense — Firebase Service (Backend)
========================================

Initialises Firebase Admin SDK and provides Firestore CRUD helpers
for user profile documents stored in the `users` collection.

Architecture:
    init_firebase()            — Called once by create_app(); idempotent.
    create_user_profile(uid, data)  → writes users/{uid}
    get_user_profile(uid)           → reads  users/{uid}
    update_user_profile(uid, data)  → updates fields in users/{uid}
    list_all_users()                → returns all documents from `users`

Dependencies:
    firebase-admin  — Admin SDK for Firestore access
    python-dotenv   — loads .env for SERVICE_ACCOUNT path resolution
"""

import os
import logging

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

_db = None  # Firestore client singleton
_firebase_app = None


def init_firebase():
    """
    Initialise the Firebase Admin SDK.

    Looks for the service account JSON at backend/firebase_service_account.json
    relative to this file. Safe to call multiple times (idempotent).
    """
    global _db, _firebase_app

    if _firebase_app is not None:
        return  # Already initialised

    sa_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "firebase_service_account.json")

    if not os.path.exists(sa_path):
        logger.warning(
            "firebase_service_account.json not found at %s. "
            "Firestore features will be unavailable.", sa_path
        )
        return

    try:
        cred = credentials.Certificate(sa_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        _db = firestore.client()
        logger.info("Firebase Admin SDK initialised successfully.")
    except Exception as exc:
        logger.error("Failed to initialise Firebase: %s", exc)


def _get_db():
    """Return the Firestore client, or raise if not initialised."""
    if _db is None:
        raise RuntimeError("Firebase is not initialised. Call init_firebase() first.")
    return _db


def get_db():
    """Public alias — used by OTP endpoints and other routes."""
    return _get_db()


# ── User Profile CRUD ────────────────────────────────────────────

def create_user_profile(uid: str, data: dict) -> dict:
    """
    Write a new user profile document to users/{uid}.

    Args:
        uid:  Firebase Auth UID.
        data: Dict with keys: display_name, email, role, joined ISO string.

    Returns:
        The written data dict.
    """
    db = _get_db()
    doc_ref = db.collection("users").document(uid)
    doc_ref.set(data)
    logger.info("Created Firestore profile for uid=%s", uid)
    return data


def get_user_profile(uid: str) -> dict | None:
    """
    Read a user profile from users/{uid}.

    Returns:
        Profile dict, or None if the document does not exist.
    """
    db = _get_db()
    doc = db.collection("users").document(uid).get()
    if doc.exists:
        return doc.to_dict()
    return None


def update_user_profile(uid: str, data: dict) -> dict:
    """
    Merge-update fields in users/{uid}.

    Args:
        uid:  Firebase Auth UID.
        data: Fields to update (partial update via merge=True).

    Returns:
        Updated fields dict.
    """
    db = _get_db()
    db.collection("users").document(uid).set(data, merge=True)
    logger.info("Updated Firestore profile for uid=%s, fields=%s", uid, list(data.keys()))
    return data


def get_user_settings(uid: str) -> dict | None:
    """Read a user's settings from users/{uid}/settings/config."""
    db = _get_db()
    doc = db.collection("users").document(uid).collection("settings").document("config").get()
    if doc.exists:
        return doc.to_dict()
    return None


def update_user_settings(uid: str, data: dict) -> dict:
    """Merge-update a user's settings in users/{uid}/settings/config."""
    db = _get_db()
    db.collection("users").document(uid).collection("settings").document("config").set(data, merge=True)
    logger.info("Updated Firestore settings for uid=%s, fields=%s", uid, list(data.keys()))
    return data


def list_all_users() -> list[dict]:
    """
    Return all user profile documents from the `users` collection.

    Returns:
        List of profile dicts, each enriched with an 'uid' key.
    """
    db = _get_db()
    docs = db.collection("users").stream()
    users = []
    for doc in docs:
        profile = doc.to_dict()
        profile["uid"] = doc.id
        users.append(profile)
    return users
