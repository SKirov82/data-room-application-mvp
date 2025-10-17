export interface FolderSummary {
  id: number;
  name: string;
  created_at: string;
}

export interface FileItem {
  id: number;
  name: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
}

export interface FolderContents {
  id: number;
  name: string;
  breadcrumbs: FolderSummary[];
  folders: FolderSummary[];
  files: FileItem[];
  total_folders: number;
  total_files: number;
  folder_page: number;
  folder_page_size: number;
  file_page: number;
  file_page_size: number;
}
