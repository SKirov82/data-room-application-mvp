import { useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { FolderSummary, FileItem } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface SearchBarProps {
  onFolderClick: (folderId: number) => void;
  onFileClick: (file: FileItem) => void;
}

interface SearchResults {
  folders: FolderSummary[];
  files: FileItem[];
}

export function SearchBar({ onFolderClick, onFileClick }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (searchQuery: string) => {
    setQuery(searchQuery);
    
    if (!searchQuery.trim()) {
      setResults(null);
      return;
    }

    setIsSearching(true);
    try {
      const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(searchQuery)}`, {
        credentials: "include",
      });
      if (response.ok) {
        const data: SearchResults = await response.json();
        setResults(data);
      }
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setIsSearching(false);
    }
  };

  const clearSearch = () => {
    setQuery("");
    setResults(null);
  };

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          type="text"
          placeholder="Search folders and files..."
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          className="pl-9 pr-4"
        />
      </div>

      {results && (
        <div className="absolute top-full mt-2 w-full rounded-lg border border-slate-200 bg-white shadow-lg z-50 max-h-96 overflow-y-auto">
          {isSearching ? (
            <div className="p-4 text-center text-sm text-slate-500">Searching...</div>
          ) : results.folders.length === 0 && results.files.length === 0 ? (
            <div className="p-4 text-center text-sm text-slate-500">No results found</div>
          ) : (
            <>
              {results.folders.length > 0 && (
                <div className="border-b border-slate-200">
                  <div className="px-4 py-2 text-xs font-semibold text-slate-500 uppercase">
                    Folders ({results.folders.length})
                  </div>
                  {results.folders.map((folder) => (
                    <button
                      key={folder.id}
                      className="w-full px-4 py-2 text-left hover:bg-slate-50 flex items-center gap-2"
                      onClick={() => {
                        onFolderClick(folder.id);
                        clearSearch();
                      }}
                    >
                      <span className="text-lg">📁</span>
                      <span className="text-sm font-medium text-slate-900">{folder.name}</span>
                    </button>
                  ))}
                </div>
              )}
              {results.files.length > 0 && (
                <div>
                  <div className="px-4 py-2 text-xs font-semibold text-slate-500 uppercase">
                    Files ({results.files.length})
                  </div>
                  {results.files.map((file) => (
                    <button
                      key={file.id}
                      className="w-full px-4 py-2 text-left hover:bg-slate-50 flex items-center gap-2"
                      onClick={() => {
                        onFileClick(file);
                        clearSearch();
                      }}
                    >
                      <span className="text-lg">📄</span>
                      <span className="text-sm font-medium text-slate-900">{file.name}</span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
