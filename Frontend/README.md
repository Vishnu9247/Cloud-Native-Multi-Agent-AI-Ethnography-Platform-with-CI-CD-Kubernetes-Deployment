# Ethnography Assistant Frontend

React frontend for the Ethnography Assistant.

## Run

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`, so start the FastAPI backend on port `8000` before testing backend sync.

To point the frontend at a different backend URL, create `.env.local`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```
