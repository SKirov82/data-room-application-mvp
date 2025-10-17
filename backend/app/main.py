from __future__ import annotations

import os
from http import HTTPStatus
from typing import Dict, List, Optional
from uuid import uuid4

from flask import (
    Flask,
    Response,
    abort,
    g,
    jsonify,
    request,
    send_file,
)
from flask_cors import CORS
from pydantic import ValidationError
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from werkzeug.exceptions import BadRequest

from . import database
from .auth import register_auth_routes, login_required
from .database import Base, engine, get_session
from .models import File, Folder, User
from .paths import STORAGE_DIR
from .schemas import (
    FileBase,
    FileRenameRequest,
    FolderContents,
    FolderCreateRequest,
    FolderSummary,
    FolderUpdateRequest,
    DataroomCreateRequest,
)


def ensure_default_dataroom(session: Session) -> Folder:
    """Guarantee there is at least one top-level dataroom folder."""
    root = session.execute(
        select(Folder).where(Folder.parent_id.is_(None)).order_by(Folder.created_at).limit(1)
    ).scalar_one_or_none()
    if root is None:
        root = Folder(name="General Dataroom", parent=None)
        session.add(root)
        session.commit()
        session.refresh(root)
    return root


def folder_to_summary(folder: Folder) -> FolderSummary:
    return FolderSummary(id=folder.id, name=folder.name, created_at=folder.created_at)


def build_breadcrumbs(folder: Folder) -> List[FolderSummary]:
    breadcrumbs: List[FolderSummary] = []
    current: Optional[Folder] = folder
    while current is not None:
        breadcrumbs.append(folder_to_summary(current))
        current = current.parent
    breadcrumbs.reverse()
    return breadcrumbs


def serialize_summary(summary: FolderSummary) -> Dict[str, object]:
    return summary.model_dump()


def serialize_file(file: File) -> Dict[str, object]:
    return FileBase.model_validate(file, from_attributes=True).model_dump()


def serialize_contents(contents: FolderContents) -> Dict[str, object]:
    return contents.model_dump()


def get_db() -> Session:
    session = getattr(g, "db_session", None)
    if session is None:
        session = database.SessionLocal()
        g.db_session = session
    return session


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Configure CORS for development - update origins for production
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    CORS(app, resources={r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PATCH", "DELETE"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True,
    }})

    Base.metadata.create_all(bind=engine)
    with get_session() as session:
        ensure_default_dataroom(session)
    
    # Register authentication routes
    register_auth_routes(app)

    @app.before_request
    def before_request() -> None:
        get_db()

    @app.teardown_request
    def teardown_request(exception: Optional[Base]) -> None:
        session: Optional[Session] = g.pop("db_session", None)
        if session is not None:
            if exception:
                session.rollback()
            session.close()

    @app.errorhandler(HTTPStatus.BAD_REQUEST)
    def handle_bad_request(error: BadRequest) -> Response:
        description = getattr(error, "description", None) or "Invalid request"
        return jsonify({"detail": description}), HTTPStatus.BAD_REQUEST

    @app.errorhandler(HTTPStatus.NOT_FOUND)
    def handle_not_found(error: Exception) -> Response:
        description = getattr(error, "description", None) or "Resource not found"
        return jsonify({"detail": description}), HTTPStatus.NOT_FOUND

    @app.errorhandler(HTTPStatus.GONE)
    def handle_gone(error: Exception) -> Response:
        description = getattr(error, "description", None) or "Resource gone"
        return jsonify({"detail": description}), HTTPStatus.GONE

    @app.route("/datarooms", methods=["GET"])
    @login_required
    def list_datarooms() -> Response:
        session = get_db()
        datarooms = session.execute(
            select(Folder).where(Folder.parent_id.is_(None)).order_by(Folder.name.asc())
        ).scalars()
        return jsonify([serialize_summary(folder_to_summary(room)) for room in datarooms])

    @app.route("/datarooms", methods=["POST"])
    @login_required
    def create_dataroom() -> Response:
        try:
            payload = DataroomCreateRequest.model_validate(request.get_json(force=True))
        except BadRequest:
            abort(HTTPStatus.BAD_REQUEST, description="Invalid JSON payload")
        except ValidationError as exc:
            abort(HTTPStatus.BAD_REQUEST, description=str(exc))

        session = get_db()
        dataroom = Folder(name=payload.name, parent=None)
        session.add(dataroom)
        session.commit()
        session.refresh(dataroom)
        return jsonify(serialize_summary(folder_to_summary(dataroom))), HTTPStatus.CREATED

    @app.route("/folders/root", methods=["GET"])
    @login_required
    def get_root_folder() -> Response:
        session = get_db()
        dataroom_id = request.args.get("dataroom_id")
        root: Optional[Folder]
        if dataroom_id is not None:
            try:
                dataroom_id_int = int(dataroom_id)
            except ValueError:
                abort(HTTPStatus.BAD_REQUEST, description="Invalid dataroom_id")
            root = session.get(Folder, dataroom_id_int)
            if root is None or root.parent_id is not None:
                abort(HTTPStatus.NOT_FOUND, description="Dataroom not found")
        else:
            root = ensure_default_dataroom(session)
        return jsonify(serialize_summary(folder_to_summary(root)))

    @app.route("/folders/<int:folder_id>/contents", methods=["GET"])
    @login_required
    def get_folder_contents(folder_id: int) -> Response:
        session = get_db()
        folder = session.get(Folder, folder_id)
        if folder is None:
            abort(HTTPStatus.NOT_FOUND, description="Folder not found")

        # Pagination parameters (independent for folders/files)
        folder_page = max(1, int(request.args.get("folder_page", request.args.get("page", 1))))
        folder_page_size = min(100, max(10, int(request.args.get("folder_page_size", request.args.get("page_size", 50)))))
        file_page = max(1, int(request.args.get("file_page", request.args.get("page", 1))))
        file_page_size = min(100, max(10, int(request.args.get("file_page_size", request.args.get("page_size", 50)))))

        folder_offset = (folder_page - 1) * folder_page_size
        file_offset = (file_page - 1) * file_page_size

        # Count totals
        from sqlalchemy import func
        total_folders = session.execute(
            select(func.count()).select_from(Folder).where(Folder.parent_id == folder.id)
        ).scalar_one()
        total_files = session.execute(
            select(func.count()).select_from(File).where(File.folder_id == folder.id)
        ).scalar_one()

        # Get paginated results
        folders = session.execute(
            select(Folder)
            .where(Folder.parent_id == folder.id)
            .order_by(Folder.name.asc())
            .limit(folder_page_size)
            .offset(folder_offset)
        ).scalars()
        files = session.execute(
            select(File)
            .where(File.folder_id == folder.id)
            .order_by(File.name.asc())
            .limit(file_page_size)
            .offset(file_offset)
        ).scalars()

        contents = FolderContents(
            id=folder.id,
            name=folder.name,
            breadcrumbs=build_breadcrumbs(folder),
            folders=[folder_to_summary(child) for child in folders],
            files=[FileBase.model_validate(file, from_attributes=True) for file in files],
            total_folders=total_folders,
            total_files=total_files,
            folder_page=folder_page,
            folder_page_size=folder_page_size,
            file_page=file_page,
            file_page_size=file_page_size,
        )
        return jsonify(serialize_contents(contents))

    @app.route("/folders", methods=["POST"])
    @login_required
    def create_folder() -> Response:
        try:
            payload = FolderCreateRequest.model_validate(request.get_json(force=True))
        except BadRequest:
            abort(HTTPStatus.BAD_REQUEST, description="Invalid JSON payload")
        except ValidationError as exc:
            abort(HTTPStatus.BAD_REQUEST, description=str(exc))

        session = get_db()
        if payload.parent_id is None:
            abort(HTTPStatus.BAD_REQUEST, description="parent_id is required for folders")

        parent = session.get(Folder, payload.parent_id)
        if parent is None:
            abort(HTTPStatus.NOT_FOUND, description="Parent folder not found")

        folder = Folder(name=payload.name, parent=parent)
        session.add(folder)
        session.commit()
        session.refresh(folder)
        return jsonify(serialize_summary(folder_to_summary(folder))), HTTPStatus.CREATED

    @app.route("/folders/<int:folder_id>", methods=["PATCH"])
    @login_required
    def rename_folder(folder_id: int) -> Response:
        try:
            payload = FolderUpdateRequest.model_validate(request.get_json(force=True))
        except BadRequest:
            abort(HTTPStatus.BAD_REQUEST, description="Invalid JSON payload")
        except ValidationError as exc:
            abort(HTTPStatus.BAD_REQUEST, description=str(exc))

        session = get_db()
        folder = session.get(Folder, folder_id)
        if folder is None:
            abort(HTTPStatus.NOT_FOUND, description="Folder not found")

        folder.name = payload.name
        session.commit()
        session.refresh(folder)
        return jsonify(serialize_summary(folder_to_summary(folder)))

    def delete_folder_files(folder: Folder) -> None:
        for file in list(folder.files):
            remove_file_storage(file)
        for child in list(folder.children):
            delete_folder_files(child)

    def remove_file_storage(file: File) -> None:
        path = file.storage_path
        if path.exists():
            path.unlink()

    @app.route("/folders/<int:folder_id>", methods=["DELETE"])
    @login_required
    def delete_folder(folder_id: int) -> Response:
        session = get_db()
        folder = session.get(Folder, folder_id)
        if folder is None:
            abort(HTTPStatus.NOT_FOUND, description="Folder not found")
        if folder.parent_id is None:
            abort(HTTPStatus.BAD_REQUEST, description="Cannot delete root folder")

        delete_folder_files(folder)
        session.delete(folder)
        session.commit()
        return Response(status=HTTPStatus.NO_CONTENT)

    @app.route("/files", methods=["POST"])
    @login_required
    def upload_file() -> Response:
        folder_id_str = request.args.get("folder_id")
        if folder_id_str is None:
            abort(HTTPStatus.BAD_REQUEST, description="Missing folder_id query parameter")
        try:
            folder_id = int(folder_id_str)
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST, description="Invalid folder_id")

        file_storage = request.files.get("upload")
        if file_storage is None:
            abort(HTTPStatus.BAD_REQUEST, description="No file uploaded")
        if file_storage.mimetype not in {"application/pdf"}:
            abort(HTTPStatus.BAD_REQUEST, description="Only PDF files are supported")
        
        # Check file size (additional validation beyond Flask's MAX_CONTENT_LENGTH)
        file_storage.seek(0, 2)  # Seek to end
        file_size = file_storage.tell()
        file_storage.seek(0)  # Reset to beginning
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            abort(HTTPStatus.BAD_REQUEST, description="File size exceeds 100MB limit")
        if file_size == 0:
            abort(HTTPStatus.BAD_REQUEST, description="Empty file not allowed")

        session = get_db()
        folder = session.get(Folder, folder_id)
        if folder is None:
            abort(HTTPStatus.NOT_FOUND, description="Folder not found")

        stored_name = f"{uuid4().hex}.pdf"
        file_path = STORAGE_DIR / stored_name
        file_storage.save(file_path)
        size_bytes = file_path.stat().st_size

        file_record = File(
            name=file_storage.filename or "Untitled",
            stored_name=stored_name,
            mime_type=file_storage.mimetype or "application/pdf",
            size_bytes=size_bytes,
            folder=folder,
        )
        session.add(file_record)
        session.commit()
        session.refresh(file_record)
        return jsonify(serialize_file(file_record)), HTTPStatus.CREATED

    @app.route("/files/<int:file_id>", methods=["GET"])
    @login_required
    def get_file(file_id: int) -> Response:
        session = get_db()
        file = session.get(File, file_id)
        if file is None:
            abort(HTTPStatus.NOT_FOUND, description="File not found")
        return jsonify(serialize_file(file))

    @app.route("/files/<int:file_id>/download", methods=["GET"])
    @login_required
    def download_file(file_id: int):
        session = get_db()
        file = session.get(File, file_id)
        if file is None:
            abort(HTTPStatus.NOT_FOUND, description="File not found")
        if not file.storage_path.exists():
            abort(HTTPStatus.GONE, description="File data missing")

        return send_file(
            file.storage_path,
            mimetype=file.mime_type,
            as_attachment=True,
            download_name=file.name,
        )

    @app.route("/files/<int:file_id>", methods=["PATCH"])
    @login_required
    def rename_file(file_id: int) -> Response:
        try:
            payload = FileRenameRequest.model_validate(request.get_json(force=True))
        except BadRequest:
            abort(HTTPStatus.BAD_REQUEST, description="Invalid JSON payload")
        except ValidationError as exc:
            abort(HTTPStatus.BAD_REQUEST, description=str(exc))

        session = get_db()
        file = session.get(File, file_id)
        if file is None:
            abort(HTTPStatus.NOT_FOUND, description="File not found")

        file.name = payload.name
        session.commit()
        session.refresh(file)
        return jsonify(serialize_file(file))

    @app.route("/files/<int:file_id>", methods=["DELETE"])
    @login_required
    def delete_file(file_id: int) -> Response:
        session = get_db()
        file = session.get(File, file_id)
        if file is None:
            abort(HTTPStatus.NOT_FOUND, description="File not found")

        file_path = file.storage_path
        if file_path.exists():
            file_path.unlink()

        session.delete(file)
        session.commit()
        return Response(status=HTTPStatus.NO_CONTENT)

    @app.route("/search", methods=["GET"])
    @login_required
    def search():
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"folders": [], "files": []})

        session = get_db()
        
        # Search folders by name
        folders = session.execute(
            select(Folder)
            .where(Folder.name.ilike(f"%{query}%"))
            .order_by(Folder.name.asc())
            .limit(50)
        ).scalars()

        # Search files by name
        files = session.execute(
            select(File)
            .where(File.name.ilike(f"%{query}%"))
            .order_by(File.name.asc())
            .limit(50)
        ).scalars()

        return jsonify({
            "folders": [serialize_summary(folder_to_summary(f)) for f in folders],
            "files": [serialize_file(file) for file in files]
        })

    return app


app = create_app()
