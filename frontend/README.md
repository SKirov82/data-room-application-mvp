# Acme Dataroom Frontend

This package contains the React + Vite single page application for the Acme Dataroom MVP. It communicates with the Flask backend to display folders, upload PDFs, and perform rename/delete actions.

## Development

```bash
npm install
npm run dev
```

By default the app expects the backend at `http://localhost:8000`. You can override this by defining `VITE_API_BASE_URL` in a `.env` file.

The UI is styled with Tailwind CSS and leverages utility classes directly within the React components. The Tailwind configuration lives in `tailwind.config.cjs`.

## Production Build

```bash
npm run build
```

The compiled assets will be emitted to `dist/`.

## Testing

```bash
npm run test
```

The Vitest suite stubs the backend API responses and verifies the React data room flows without requiring the Flask service to be running.
