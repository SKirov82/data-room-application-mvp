from __future__ import annotations

import os
from functools import wraps
from http import HTTPStatus
from typing import Callable, Optional

from flask import Response, abort, jsonify, request, session
from pydantic import BaseModel, EmailStr, ValidationError
from sqlalchemy import select
from werkzeug.exceptions import BadRequest

from .models import User


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


def login_required(f: Callable) -> Callable:
    """Decorator to require authentication for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"detail": "Authentication required"}), HTTPStatus.UNAUTHORIZED
        return f(*args, **kwargs)
    return decorated_function


def get_current_user_id() -> Optional[int]:
    """Get the current logged-in user ID from session"""
    return session.get('user_id')


def register_auth_routes(app):
    """Register authentication routes on the Flask app"""
    from .database import SessionLocal

    @app.route("/auth/register", methods=["POST"])
    def register():
        try:
            payload = RegisterRequest.model_validate(request.get_json(force=True))
        except BadRequest:
            abort(HTTPStatus.BAD_REQUEST, description="Invalid JSON payload")
        except ValidationError as exc:
            abort(HTTPStatus.BAD_REQUEST, description=str(exc))

        db_session = SessionLocal()
        try:
            # Check if user already exists
            existing_user = db_session.execute(
                select(User).where(User.email == payload.email).limit(1)
            ).scalar_one_or_none()

            if existing_user:
                abort(HTTPStatus.CONFLICT, description="Email already registered")

            # Create new user
            user = User(email=payload.email)
            user.set_password(payload.password)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Log the user in
            session['user_id'] = user.id
            session.permanent = True

            return (
                jsonify({"id": user.id, "email": user.email}),
                HTTPStatus.CREATED,
            )
        finally:
            db_session.close()

    @app.route("/auth/login", methods=["POST"])
    def login():
        try:
            payload = LoginRequest.model_validate(request.get_json(force=True))
        except BadRequest:
            abort(HTTPStatus.BAD_REQUEST, description="Invalid JSON payload")
        except ValidationError as exc:
            abort(HTTPStatus.BAD_REQUEST, description=str(exc))

        db_session = SessionLocal()
        try:
            user = db_session.execute(
                select(User).where(User.email == payload.email).limit(1)
            ).scalar_one_or_none()

            if not user or not user.check_password(payload.password):
                abort(HTTPStatus.UNAUTHORIZED, description="Invalid email or password")

            if not user.is_active:
                abort(HTTPStatus.FORBIDDEN, description="Account is disabled")

            # Log the user in
            session['user_id'] = user.id
            session.permanent = True

            return jsonify({"id": user.id, "email": user.email})
        finally:
            db_session.close()

    @app.route("/auth/logout", methods=["POST"])
    def logout():
        session.pop('user_id', None)
        return Response(status=HTTPStatus.NO_CONTENT)

    @app.route("/auth/me", methods=["GET"])
    def get_current_user():
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"detail": "Not authenticated"}), HTTPStatus.UNAUTHORIZED

        db_session = SessionLocal()
        try:
            user = db_session.get(User, user_id)
            if not user:
                session.pop('user_id', None)
                return jsonify({"detail": "User not found"}), HTTPStatus.UNAUTHORIZED
            
            return jsonify({"id": user.id, "email": user.email})
        finally:
            db_session.close()
