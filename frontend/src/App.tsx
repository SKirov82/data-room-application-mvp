import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { FolderContents, FolderSummary, FileItem } from "./types";
import { CreateFolderDialog } from "./components/CreateFolderDialog";
import { RenameDialog } from "./components/RenameDialog";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { SearchBar } from "./components/SearchBar";
import { LoginForm } from "./components/LoginForm";
import { RegisterForm } from "./components/RegisterForm";
import { useAuth } from "./contexts/AuthContext";
import { Button } from "./components/ui/button";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface AsyncState {
  loading: boolean;
  error: string | null;
}

interface DialogState {
  createFolder: boolean;
  renameFolder: { open: boolean; folder: FolderSummary | null };
  renameFile: { open: boolean; file: FileItem | null };
  deleteFolder: { open: boolean; folder: FolderSummary | null };
  deleteFile: { open: boolean; file: FileItem | null };
}

function formatBytes(size: number): string {
  if (size === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
  const value = size / Math.pow(1024, index);
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function App() {
  const { user, logout, loading: authLoading } = useAuth();
  const [showRegister, setShowRegister] = useState(false);
  const [datarooms, setDatarooms] = useState<FolderSummary[]>([]);
  const [selectedDataroom, setSelectedDataroom] = useState<FolderSummary | null>(null);
  const [currentFolder, setCurrentFolder] = useState<FolderContents | null>(null);
  const [state, setState] = useState<AsyncState>({ loading: true, error: null });
  const [folderPage, setFolderPage] = useState(1);
  const [filePage, setFilePage] = useState(1);
  const [dialogs, setDialogs] = useState<DialogState>({
    createFolder: false,
    renameFolder: { open: false, folder: null },
    renameFile: { open: false, file: null },
    deleteFolder: { open: false, folder: null },
    deleteFile: { open: false, file: null },
  });
  const [createDataroomOpen, setCreateDataroomOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const secondaryButtonClasses =
    "rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-60";
  const primaryButtonClasses =
    "rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-60";
  const cardActionButtonClasses =
    "text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2";

  const loadFolder = async (
    folderId: number,
    options?: { folderPage?: number; filePage?: number }
  ) => {
    const nextFolderPage = options?.folderPage ?? folderPage;
    const nextFilePage = options?.filePage ?? filePage;

    setState({ loading: true, error: null });
    try {
      const params = new URLSearchParams({
        folder_page: String(nextFolderPage),
        folder_page_size: "50",
        file_page: String(nextFilePage),
        file_page_size: "50",
      });

      const response = await fetch(
        `${API_BASE_URL}/folders/${folderId}/contents?${params.toString()}`,
        { credentials: "include" }
      );
      if (!response.ok) {
        throw new Error(`Unable to load folder (${response.status})`);
      }
      const data: FolderContents = await response.json();
      setCurrentFolder(data);
      setFolderPage(data.folder_page);
      setFilePage(data.file_page);
      setState({ loading: false, error: null });
    } catch (error) {
      console.error(error);
      setState({ loading: false, error: error instanceof Error ? error.message : "Unknown error" });
    }
  };

  const loadRoot = async (dataroomId: number) => {
    setState({ loading: true, error: null });
    try {
      const response = await fetch(
        `${API_BASE_URL}/folders/root?dataroom_id=${dataroomId}`,
        { credentials: "include" }
      );
      if (!response.ok) {
        throw new Error("Failed to resolve root folder");
      }
      const root: FolderSummary = await response.json();
      await loadFolder(root.id, { folderPage: 1, filePage: 1 });
    } catch (error) {
      console.error(error);
      setState({ loading: false, error: error instanceof Error ? error.message : "Unknown error" });
    }
  };

  const loadDatarooms = async (preferredId?: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/datarooms`, { credentials: "include" });
      if (!response.ok) {
        throw new Error("Failed to load datarooms");
      }
      const rooms: FolderSummary[] = await response.json();
      setDatarooms(rooms);

      if (rooms.length === 0) {
        setSelectedDataroom(null);
        setCurrentFolder(null);
        setState({ loading: false, error: null });
        return;
      }

      const nextRoom = preferredId
        ? rooms.find((room) => room.id === preferredId) ?? rooms[0]
        : rooms[0];

      setSelectedDataroom(nextRoom);
      await loadRoot(nextRoom.id);
    } catch (error) {
      console.error(error);
      setState({ loading: false, error: error instanceof Error ? error.message : "Unknown error" });
    }
  };

  useEffect(() => {
    loadRoot();
  }, []);

  const handleCreateFolder = async (name: string) => {
    if (!currentFolder) return;

    try {
      const response = await fetch(`${API_BASE_URL}/folders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, parent_id: currentFolder.id }),
      });
      if (!response.ok) {
        throw new Error("Failed to create folder");
      }
      await loadFolder(currentFolder.id);
    } catch (error) {
      alert(error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleRenameFolder = async (newName: string) => {
    const folder = dialogs.renameFolder.folder;
    if (!folder) return;

    try {
      const response = await fetch(`${API_BASE_URL}/folders/${folder.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName }),
      });
      if (!response.ok) {
        throw new Error("Failed to rename folder");
      }
      if (currentFolder && currentFolder.id === folder.id) {
        await loadFolder(folder.id);
      } else if (currentFolder) {
        await loadFolder(currentFolder.id);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleDeleteFolder = async () => {
    const folder = dialogs.deleteFolder.folder;
    if (!folder) return;

    try {
      const response = await fetch(`${API_BASE_URL}/folders/${folder.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete folder");
      }
      if (currentFolder && currentFolder.id === folder.id) {
        const parent = currentFolder.breadcrumbs[currentFolder.breadcrumbs.length - 2];
        if (parent) {
          await loadFolder(parent.id);
        } else {
          await loadRoot();
        }
      } else if (currentFolder) {
        await loadFolder(currentFolder.id);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleUploadFile = async (event: ChangeEvent<HTMLInputElement>) => {
    if (!currentFolder) return;
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("upload", file);

    try {
      const response = await fetch(`${API_BASE_URL}/files?folder_id=${currentFolder.id}`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail ?? "Failed to upload file");
      }
      await loadFolder(currentFolder.id);
    } catch (error) {
      alert(error instanceof Error ? error.message : "Unknown error");
    } finally {
      event.target.value = "";
    }
  };

  const handleOpenFile = (file: FileItem) => {
    window.open(`${API_BASE_URL}/files/${file.id}/download`, "_blank");
  };

  const handleRenameFile = async (newName: string) => {
    const file = dialogs.renameFile.file;
    if (!file) return;

    try {
      const response = await fetch(`${API_BASE_URL}/files/${file.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName }),
      });
      if (!response.ok) {
        throw new Error("Failed to rename file");
      }
      if (currentFolder) {
        await loadFolder(currentFolder.id);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleDeleteFile = async () => {
    const file = dialogs.deleteFile.file;
    if (!file) return;

    try {
      const response = await fetch(`${API_BASE_URL}/files/${file.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete file");
      }
      if (currentFolder) {
        await loadFolder(currentFolder.id);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : "Unknown error");
    }
  };

  const breadcrumbItems = useMemo(() => {
    if (!currentFolder) return [];
    return currentFolder.breadcrumbs;
  }, [currentFolder]);

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="text-lg text-slate-600">Loading...</div>
      </div>
    );
  }

  // Show login/register if not authenticated
  if (!user) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
        {showRegister ? (
          <RegisterForm onToggleMode={() => setShowRegister(false)} />
        ) : (
          <LoginForm onToggleMode={() => setShowRegister(true)} />
        )}
      </div>
    );
  }

  // Show dataroom interface when authenticated
  return (
    <div className="min-h-screen bg-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-6 pb-10 pt-8 text-slate-900 md:gap-8 md:px-10 lg:px-12">
        <header className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Acme Dataroom</h1>
              <p className="mt-1 text-base text-slate-500">
                {user.email} •{' '}
                <button onClick={logout} className="text-indigo-600 hover:text-indigo-500">
                  Logout
                </button>
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              className={secondaryButtonClasses}
              onClick={() => setDialogs({ ...dialogs, createFolder: true })}
              disabled={!currentFolder}
            >
              New Folder
            </button>
            <button
              type="button"
              className={`${primaryButtonClasses} whitespace-nowrap`}
              onClick={handleUploadClick}
              disabled={!currentFolder}
            >
              Upload PDF
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={handleUploadFile}
            />
            </div>
          </div>
          <SearchBar 
            onFolderClick={(id) => loadFolder(id)} 
            onFileClick={handleOpenFile}
          />
        </header>

        <main className="flex-1">
          {state.loading && (
            <div className="rounded-2xl bg-white p-6 text-base font-medium text-slate-500 shadow-panel sm:p-8">
              Loading...
            </div>
          )}
          {state.error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-base font-medium text-rose-700 shadow-none sm:p-8">
              {state.error}
            </div>
          )}
          {!state.loading && !state.error && currentFolder && (
            <div className="flex flex-col gap-8 rounded-2xl bg-white p-6 shadow-panel sm:p-8">
              <nav className="flex flex-wrap items-center gap-1 text-sm text-slate-500">
                {breadcrumbItems.map((crumb, index) => (
                  <span key={crumb.id} className="flex items-center gap-1">
                    <button
                      type="button"
                      className={`rounded px-2 py-1 text-sm font-medium transition hover:text-indigo-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-default disabled:text-slate-500`}
                      onClick={() => loadFolder(crumb.id)}
                      disabled={index === breadcrumbItems.length - 1}
                    >
                      {crumb.name}
                    </button>
                    {index !== breadcrumbItems.length - 1 && <span className="text-slate-400">/</span>}
                  </span>
                ))}
              </nav>

              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-900">Folders</h2>
                  <span className="text-sm text-slate-400">{currentFolder.total_folders} total</span>
                </div>
                {currentFolder.folders.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                    No subfolders yet.
                  </p>
                ) : (
                  <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {currentFolder.folders.map((folder) => (
                      <li
                        key={folder.id}
                        className="group flex flex-col gap-3 rounded-xl border border-transparent bg-slate-50 p-4 shadow-sm transition hover:-translate-y-1 hover:border-slate-200 hover:bg-white hover:shadow-lg"
                      >
                        <button
                          type="button"
                          className="flex w-full items-start gap-3 text-left"
                          onClick={() => loadFolder(folder.id)}
                        >
                          <span className="text-3xl" aria-hidden>
                            📁
                          </span>
                          <div>
                            <h3 className="text-lg font-semibold text-slate-900">{folder.name}</h3>
                            <p className="mt-1 text-sm text-slate-500">
                              Created {new Date(folder.created_at).toLocaleString()}
                            </p>
                          </div>
                        </button>
                        <div className="flex flex-wrap gap-3 text-indigo-600">
                          <button
                            type="button"
                            className={`${cardActionButtonClasses} text-indigo-600 hover:text-indigo-500 focus-visible:outline-indigo-500`}
                            onClick={() =>
                              setDialogs({ ...dialogs, renameFolder: { open: true, folder } })
                            }
                          >
                            Rename
                          </button>
                          <button
                            type="button"
                            className={`${cardActionButtonClasses} text-rose-600 hover:text-rose-500 focus-visible:outline-rose-500`}
                            onClick={() =>
                              setDialogs({ ...dialogs, deleteFolder: { open: true, folder } })
                            }
                          >
                            Delete
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-900">Files</h2>
                  <span className="text-sm text-slate-400">{currentFolder.total_files} total</span>
                </div>
                {currentFolder.files.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                    No files uploaded yet.
                  </p>
                ) : (
                  <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {currentFolder.files.map((file) => (
                      <li
                        key={file.id}
                        className="group flex flex-col gap-3 rounded-xl border border-transparent bg-slate-50 p-4 shadow-sm transition hover:-translate-y-1 hover:border-slate-200 hover:bg-white hover:shadow-lg"
                      >
                        <button
                          type="button"
                          className="flex w-full items-start gap-3 text-left"
                          onClick={() => handleOpenFile(file)}
                        >
                          <span className="text-3xl" aria-hidden>
                            📄
                          </span>
                          <div>
                            <h3 className="text-lg font-semibold text-slate-900">{file.name}</h3>
                            <p className="mt-1 text-sm text-slate-500">
                              {formatBytes(file.size_bytes)} • Uploaded {new Date(file.created_at).toLocaleString()}
                            </p>
                          </div>
                        </button>
                        <div className="flex flex-wrap gap-3 text-indigo-600">
                          <button
                            type="button"
                            className={`${cardActionButtonClasses} text-indigo-600 hover:text-indigo-500 focus-visible:outline-indigo-500`}
                            onClick={() =>
                              setDialogs({ ...dialogs, renameFile: { open: true, file } })
                            }
                          >
                            Rename
                          </button>
                          <button
                            type="button"
                            className={`${cardActionButtonClasses} text-rose-600 hover:text-rose-500 focus-visible:outline-rose-500`}
                            onClick={() =>
                              setDialogs({ ...dialogs, deleteFile: { open: true, file } })
                            }
                          >
                            Delete
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {currentFolder && (currentFolder.total_folders > currentFolder.page_size || currentFolder.total_files > currentFolder.page_size) && (
                <div className="flex items-center justify-between border-t border-slate-200 pt-6">
                  <div className="text-sm text-slate-600">
                    Page {currentFolder.page} • Showing up to {currentFolder.page_size} items per page
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className={secondaryButtonClasses}
                      onClick={() => currentFolder && loadFolder(currentFolder.id, currentPage - 1)}
                      disabled={currentPage <= 1}
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      className={secondaryButtonClasses}
                      onClick={() => currentFolder && loadFolder(currentFolder.id, currentPage + 1)}
                      disabled={
                        currentFolder.folders.length < currentFolder.page_size &&
                        currentFolder.files.length < currentFolder.page_size
                      }
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Dialogs */}
      <CreateFolderDialog
        open={dialogs.createFolder}
        onOpenChange={(open) => setDialogs({ ...dialogs, createFolder: open })}
        onConfirm={handleCreateFolder}
      />

      <RenameDialog
        open={dialogs.renameFolder.open}
        onOpenChange={(open) =>
          setDialogs({ ...dialogs, renameFolder: { open, folder: null } })
        }
        onConfirm={handleRenameFolder}
        currentName={dialogs.renameFolder.folder?.name ?? ""}
        itemType="folder"
      />

      <RenameDialog
        open={dialogs.renameFile.open}
        onOpenChange={(open) =>
          setDialogs({ ...dialogs, renameFile: { open, file: null } })
        }
        onConfirm={handleRenameFile}
        currentName={dialogs.renameFile.file?.name ?? ""}
        itemType="file"
      />

      <ConfirmDialog
        open={dialogs.deleteFolder.open}
        onOpenChange={(open) =>
          setDialogs({ ...dialogs, deleteFolder: { open, folder: null } })
        }
        onConfirm={handleDeleteFolder}
        title="Delete Folder"
        description={`Are you sure you want to delete "${dialogs.deleteFolder.folder?.name}" and all of its contents? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
      />

      <ConfirmDialog
        open={dialogs.deleteFile.open}
        onOpenChange={(open) =>
          setDialogs({ ...dialogs, deleteFile: { open, file: null } })
        }
        onConfirm={handleDeleteFile}
        title="Delete File"
        description={`Are you sure you want to delete "${dialogs.deleteFile.file?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
      />
    </div>
  );
}

export default App;
