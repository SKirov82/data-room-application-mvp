from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, Mapping
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .main import ensure_default_dataroom
from .models import File, Folder
from .paths import STORAGE_DIR

PDF_TEMPLATE = textwrap.dedent(
    """\
    %PDF-1.4
    1 0 obj
    << /Type /Catalog /Pages 2 0 R >>
    endobj
    2 0 obj
    << /Type /Pages /Kids [3 0 R] /Count 1 >>
    endobj
    3 0 obj
    << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
    endobj
    4 0 obj
    << /Length {length} >>
    stream
    {text}
    endstream
    endobj
    5 0 obj
    << /Type /Info /Title ({title}) >>
    endobj
    xref
    0 6
    0000000000 65535 f 
    0000000010 00000 n 
    0000000061 00000 n 
    0000000112 00000 n 
    0000000203 00000 n 
    0000000291 00000 n 
    trailer
    << /Size 6 /Root 1 0 R /Info 5 0 R >>
    startxref
    369
    %%EOF
    """
).strip().encode("utf-8")

MOCK_STRUCTURE: Mapping[str, Mapping[str, object]] = {
    "Financials": {
        "Quarterly Reports": {
            "files": {
                "Q1 2023 Summary.pdf": "Highlights from the first quarter of 2023",
                "Q2 2023 Summary.pdf": "Key performance indicators for Q2 2023",
            }
        },
        "Board Decks": {
            "files": {
                "April Board Meeting.pdf": "Slides prepared for the April board review",
            }
        },
        "files": {
            "Balance Sheet.pdf": "Consolidated balance sheet snapshot",
        },
    },
    "Legal": {
        "files": {
            "NDA Template.pdf": "Mutual NDA template used with prospective partners",
            "Master Service Agreement.pdf": "Standard MSA covering service delivery terms",
        },
    },
    "Product": {
        "Roadmaps": {
            "files": {
                "2024 Product Roadmap.pdf": "Upcoming product milestones and releases",
            }
        },
    },
}


def _ensure_child_folder(session: Session, parent: Folder, name: str) -> Folder:
    existing = session.execute(
        select(Folder).where(Folder.parent_id == parent.id, Folder.name == name).limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    folder = Folder(name=name, parent=parent)
    session.add(folder)
    session.commit()
    session.refresh(folder)
    return folder


def _pdf_bytes(title: str, description: str) -> bytes:
    body = textwrap.dedent(
        f"""
        BT
        /F1 24 Tf
        72 720 Td
        ({title}) Tj
        0 -36 Td
        /F1 14 Tf
        ({description}) Tj
        ET
        """
    ).strip()
    payload = PDF_TEMPLATE.replace(b"{title}", title.encode("utf-8"))
    payload = payload.replace(b"{text}", body.encode("utf-8"))
    payload = payload.replace(b"{length}", str(len(body.encode("utf-8"))).encode("utf-8"))
    return payload


def _ensure_file(
    session: Session, folder: Folder, name: str, description: str, storage_dir: Path
) -> None:
    existing = session.execute(
        select(File).where(File.folder_id == folder.id, File.name == name).limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        if not existing.storage_path.exists():
            existing.storage_path.write_bytes(_pdf_bytes(name, description))
            existing.size_bytes = existing.storage_path.stat().st_size
            session.commit()
        return

    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}.pdf"
    file_path = storage_dir / stored_name
    pdf_data = _pdf_bytes(name, description)
    file_path.write_bytes(pdf_data)

    file_record = File(
        name=name,
        stored_name=stored_name,
        mime_type="application/pdf",
        size_bytes=file_path.stat().st_size,
        folder=folder,
    )
    session.add(file_record)
    session.commit()


def _seed_folder(
    session: Session,
    parent: Folder,
    name: str,
    subtree: Mapping[str, object],
    storage_dir: Path,
) -> None:
    folder = _ensure_child_folder(session, parent, name)

    files: Dict[str, str] = subtree.get("files", {})  # type: ignore[assignment]
    for filename, description in files.items():
        _ensure_file(session, folder, filename, description, storage_dir)

    for child_name, child_subtree in subtree.items():
        if child_name == "files":
            continue
        if not isinstance(child_subtree, Mapping):
            continue
        _seed_folder(session, folder, child_name, child_subtree, storage_dir)


def seed_mock_data(session: Session, storage_dir: Path = STORAGE_DIR) -> None:
    root = ensure_default_dataroom(session)
    for name, subtree in MOCK_STRUCTURE.items():
        _seed_folder(session, root, name, subtree, storage_dir)


def main() -> None:
    storage_dir = STORAGE_DIR
    storage_dir.mkdir(parents=True, exist_ok=True)
    with get_session() as session:
        seed_mock_data(session, storage_dir)


if __name__ == "__main__":
    main()
