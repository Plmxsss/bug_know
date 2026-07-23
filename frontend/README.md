# AgriGuard AI Web

This directory contains the Vue 3, TypeScript, and Vite frontend.

## Development

Start FastAPI on port 8000 first. Then run:

```powershell
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. During development, Vite forwards browser
requests beginning with `/api` and `/media` to FastAPI. The browser therefore
uses relative URLs and does not need a separate backend address or CORS
exception.

Build and type-check the production bundle:

```powershell
npm run build
npm test
```

The current learning unit contains:

- `src/main.ts`: creates and mounts the Vue application.
- `src/App.vue`: shared page shell and navigation.
- `src/router/index.ts`: maps `/` and `/detect` to page components.
- `src/components/ServiceReadiness.vue`: reactive service-status component.
- `src/api/`: typed health and multipart detection requests.
- `src/stores/detection.ts`: Pinia state for the active detection.
- `src/views/DetectionView.vue`: image selection, preview, upload, and results.
- `vite.config.ts`: Vue plugin and local reverse-proxy configuration.

Vitest replaces the real detection API in store tests, so routine frontend
tests do not load YOLO or require a GPU. Diagnosis reports and history will be
added in later, independently verifiable units.
