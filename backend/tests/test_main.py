from __future__ import annotations

import io
from pathlib import Path
from typing import Tuple

from flask.testing import FlaskClient


def test_create_and_list_folders(client: Tuple[FlaskClient, Path]) -> None:
    api, _ = client

    root_response = api.get("/folders/root")
    assert root_response.status_code == 200
    root_data = root_response.get_json()
    assert root_data["name"] == "Root"

    create_response = api.post(
        "/folders",
        json={"name": "Financials", "parent_id": root_data["id"]},
    )
    assert create_response.status_code == 201

    contents_response = api.get(f"/folders/{root_data['id']}/contents")
    assert contents_response.status_code == 200
    contents = contents_response.get_json()

    folder_names = [folder["name"] for folder in contents["folders"]]
    assert "Financials" in folder_names


def test_file_lifecycle_operations(client: Tuple[FlaskClient, Path]) -> None:
    api, storage_dir = client

    root_id = api.get("/folders/root").get_json()["id"]
    folder_id = api.post(
        "/folders", json={"name": "Contracts", "parent_id": root_id}
    ).get_json()["id"]

    payload = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    upload_response = api.post(
        "/files",
        data={"upload": (io.BytesIO(payload), "nda.pdf", "application/pdf")},
        content_type="multipart/form-data",
        query_string={"folder_id": folder_id},
    )
    assert upload_response.status_code == 201
    file_data = upload_response.get_json()
    assert file_data["name"] == "nda.pdf"
    assert file_data["size_bytes"] == len(payload)

    stored_files = list(storage_dir.iterdir())
    assert len(stored_files) == 1

    rename_response = api.patch(
        f"/files/{file_data['id']}", json={"name": "updated-nda.pdf"}
    )
    assert rename_response.status_code == 200
    assert rename_response.get_json()["name"] == "updated-nda.pdf"

    delete_response = api.delete(f"/files/{file_data['id']}")
    assert delete_response.status_code == 204
    assert list(storage_dir.iterdir()) == []


def test_delete_folder_cascades_to_children(client: Tuple[FlaskClient, Path]) -> None:
    api, storage_dir = client

    root_id = api.get("/folders/root").get_json()["id"]
    parent_id = api.post(
        "/folders", json={"name": "Q1", "parent_id": root_id}
    ).get_json()["id"]
    child_id = api.post(
        "/folders", json={"name": "Drafts", "parent_id": parent_id}
    ).get_json()["id"]

    payload = b"%PDF-1.4\nTest"
    api.post(
        "/files",
        data={"upload": (io.BytesIO(payload), "draft.pdf", "application/pdf")},
        content_type="multipart/form-data",
        query_string={"folder_id": child_id},
    )

    assert len(list(storage_dir.iterdir())) == 1

    delete_parent = api.delete(f"/folders/{parent_id}")
    assert delete_parent.status_code == 204

    assert list(storage_dir.iterdir()) == []

    missing_child = api.get(f"/folders/{child_id}/contents")
    assert missing_child.status_code == 404


def test_cannot_delete_root_folder(client: Tuple[FlaskClient, Path]) -> None:
    api, _ = client

    root_id = api.get("/folders/root").get_json()["id"]
    response = api.delete(f"/folders/{root_id}")
    assert response.status_code == 400
    assert response.get_json()["detail"] == "Cannot delete root folder"
