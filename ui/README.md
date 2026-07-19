# GenoWall UI (`ui/`)

Svelte frontend — lives **inside** the main [`genowall`](https://github.com/eylernur/genowall) repo.

Vercel builds this folder via the root `vercel.json`. Do not import a separate UI repository.

## Local

```bash
# from repo root — start API
conda activate genowall && make api

# from ui/
cp .env.example .env.local   # VITE_API_URL=http://127.0.0.1:8000
npm install && npm run dev
```

See the root [README](../README.md) for Vercel + ngrok deploy.
