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
```

The current learning unit contains:

- `src/main.ts`: creates and mounts the Vue application.
- `src/App.vue`: the root page component.
- `src/components/ServiceReadiness.vue`: reactive service-status component.
- `src/api/health.ts`: typed FastAPI health request.
- `vite.config.ts`: Vue plugin and local reverse-proxy configuration.

The upload and report workflow will be added in later, independently verifiable
units.
