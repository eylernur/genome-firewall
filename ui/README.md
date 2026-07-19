# GenoWall UI

Svelte + Vite front-end for [GenoWall](https://github.com/eylernur/genowall).

Lives in the main repo under `ui/`. **Vercel Root Directory must be `ui`.**

## Local

```bash
# terminal A — from repo root
conda activate genowall
make api

# terminal B — from ui/
cp .env.example .env.local
npm install
npm run dev
```

Open http://127.0.0.1:5173

| Env | Purpose |
|-----|---------|
| `VITE_API_URL` | FastAPI base (e.g. `http://127.0.0.1:8000`). If unset → preview/mock report. |

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` | Production build → `dist/` |
| `npm run check` | Typecheck |

Full docs: [../README.md](../README.md)
