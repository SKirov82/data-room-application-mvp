from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class FileBase(BaseModel):
    id: int
    name: str
    mime_type: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FolderSummary(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FolderContents(BaseModel):
    id: int
    name: str
    breadcrumbs: List[FolderSummary]
    folders: List[FolderSummary]
    files: List[FileBase]
    total_folders: int
    total_files: int
    folder_page: int
    folder_page_size: int
    file_page: int
    file_page_size: int


class FolderCreateRequest(BaseModel):
    name: str
    parent_id: Optional[int] = None


class FolderUpdateRequest(BaseModel):
    name: str


class FileRenameRequest(BaseModel):
    name: str


class DataroomCreateRequest(BaseModel):
    name: str
