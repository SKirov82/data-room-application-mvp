import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  cleanup();
});

describe("App", () => {
  const baseRootFolder = {
    id: 1,
    name: "Acme Dataroom",
    created_at: "2024-01-01T00:00:00Z",
  };

  it("loads the root folder and renders folders and files", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => baseRootFolder,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 1,
          name: baseRootFolder.name,
          breadcrumbs: [baseRootFolder],
          folders: [
            { id: 2, name: "Project Docs", created_at: "2024-01-02T00:00:00Z" },
            { id: 3, name: "Financials", created_at: "2024-01-03T00:00:00Z" },
          ],
          files: [
            {
              id: 11,
              name: "Overview.pdf",
              mime_type: "application/pdf",
              size_bytes: 2048,
              created_at: "2024-01-04T00:00:00Z",
            },
          ],
        }),
      });

    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("open", vi.fn());

    render(<App />);

    expect(await screen.findByText("Project Docs")).toBeInTheDocument();
    expect(screen.getByText("Financials")).toBeInTheDocument();
    expect(screen.getByText("Overview.pdf")).toBeInTheDocument();

    expect(fetchMock.mock.calls[0][0]).toContain("/folders/root");
    expect(fetchMock.mock.calls[1][0]).toContain("/folders/1/contents");
  });

  it("navigates into a nested folder when selected", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => baseRootFolder,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 1,
          name: baseRootFolder.name,
          breadcrumbs: [baseRootFolder],
          folders: [{ id: 2, name: "Project Docs", created_at: "2024-01-02T00:00:00Z" }],
          files: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 2,
          name: "Project Docs",
          breadcrumbs: [
            baseRootFolder,
            { id: 2, name: "Project Docs", created_at: "2024-01-02T00:00:00Z" },
          ],
          folders: [],
          files: [
            {
              id: 22,
              name: "Project Plan.pdf",
              mime_type: "application/pdf",
              size_bytes: 4096,
              created_at: "2024-01-05T00:00:00Z",
            },
          ],
        }),
      });

    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("open", vi.fn());

    render(<App />);

    const folderButton = await screen.findByText("Project Docs");
    await userEvent.click(folderButton);

    await waitFor(() => {
      expect(fetchMock.mock.calls[2]?.[0]).toContain("/folders/2/contents");
    });

    expect(await screen.findByText("Project Plan.pdf")).toBeInTheDocument();
    const breadcrumbButtons = screen.getAllByRole("button", { name: "Project Docs" });
    expect(breadcrumbButtons[0]).toBeDisabled();
  });
});
