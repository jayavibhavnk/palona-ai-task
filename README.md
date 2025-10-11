# Commerce Chat — AI Shopping Assistant

A production-ready demo of a **chat-based commerce agent** with:

* **Text recommendations**
* **Image-based product search** (drag & drop)
* **Cart actions** handled via natural language (e.g., “add #2”, “view cart”, “checkout”)
* **Markdown** rendering for assistant replies
* Clean **React + Vite + Tailwind** frontend, FastAPI backend, Weaviate vector DB, and Groq LLM

> Backend deployed at: `https://macro-crane-474800-p9.uw.r.appspot.com`
> Frontend: React (Vite) — https://palonai-chat.vercel.app/

---

## Table of Contents

* [Architecture](#architecture)
* [Screenshots](#screenshots)
* [Repo Structure](#repo-structure)
* [Quick Start](#quick-start)

  * [Frontend (React + Vite)](#frontend-react--vite)
  * [Backend (FastAPI)](#backend-fastapi)
* [Environment Variables](#environment-variables)
* [Deploy](#deploy)

  * [Frontend to Vercel](#frontend-to-vercel)
  * [Backend (Google Cloud / any host)](#backend-google-cloud--any-host)
* [API Reference](#api-reference)
* [Data & Search](#data--search)
* [UI Features](#ui-features)
* [Common Fixes / Troubleshooting](#common-fixes--troubleshooting)
* [Security Notes](#security-notes)
* [Roadmap](#roadmap)
* [License](#license)

---

## Architecture

```
┌────────────────┐       chat/image/cart        ┌────────────────────────┐
│  React/Vite UI │  ─────────────────────────→  │ FastAPI (Groq + Weav.) │
│  Tailwind CSS  │  ←───────── JSON (LLM + products + cart) ─────────────┘
└────────────────┘                                │
       │                                           │ vector queries
       │ drag&drop image → base64                  ▼
       │                                     ┌──────────┐
       └────────────────────────────────────►│ Weaviate │
                                             └──────────┘
```

* **LLM**: Groq `openai/gpt-oss-120b`
* **Vector DB**: Weaviate (collection “Product”)
* **Search**: `near_text`, `near_image`
* **Cart**: session-scoped in-memory store on server
* **Sessions**: simple `session_id` persisted in browser `localStorage`

---

## Quick Start

### Frontend (React + Vite)

1. **Install**

```bash
cd frontend
npm install
# if plugin error:
# npm i -D @vitejs/plugin-react
```

2. **Set API base**
   Create `.env` in `frontend/`:

```env
VITE_API_BASE=https://macro-crane-474800-p9.uw.r.appspot.com
```

3. **Run**

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

> If you get a white screen, open the browser console. We wrap the app in an error boundary so you’ll see a friendly error instead of a blank page.

---

### Backend (FastAPI)

1. **Install**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn groq weaviate-client pydantic requests
```

2. **Env vars**

```bash
export GROQ_API_KEY=YOUR_KEY
export WEAVIATE_URL=https://<cluster>.weaviate.cloud
export WEAVIATE_API_KEY=YOUR_WCS_KEY
# Optional
# export COHERE_API_KEY=YOUR_COHERE_KEY
```

3. **Run**

```bash
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

4. **CORS**
   Already enabled in your code:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Environment Variables

### Frontend

* `VITE_API_BASE` — backend URL; e.g. `https://macro-crane-474800-p9.uw.r.appspot.com`

### Backend

* `GROQ_API_KEY` — required
* `WEAVIATE_URL` — required (`https://...weaviate.cloud`)
* `WEAVIATE_API_KEY` — if your cluster requires it
* `WEAVIATE_LOCAL=true` — to use local weaviate (optional)
* `COHERE_API_KEY` — optional (if using Cohere reranking headers)

---

## Deploy

### Frontend to Vercel

1. Push `frontend/` to a Git repo (GitHub/GitLab).
2. On Vercel, **New Project** → Import your repo.
3. Root Directory: `frontend`
4. Build Command: `npm run build`
   Output Dir: `dist`
5. Add Environment Variable:

   * `VITE_API_BASE=https://macro-crane-474800-p9.uw.r.appspot.com`
6. Deploy.

> **CORS** is already open on the backend. If you later restrict it, add your Vercel domain to `allow_origins`.

### Backend (Google Cloud / any host)

* Deploy your `FastAPI` as a container (Cloud Run, App Engine, or bare VM).
* Make sure you set env vars and keep `/health` reachable.
* Confirm CORS is correct for your frontend domain.

---

## API Reference

Base URL: `${VITE_API_BASE}` (e.g., `https://macro-crane-474800-p9.uw.r.appspot.com`)

### `POST /chat`

**Request**

```json
{ "session_id": "string", "query": "Recommend me budget phones" }
```

**Response**

```json
{
  "answer": "string (LLM markdown)",
  "products": [ { "product_name": "...", "price": "...", "url": "...", "image_url": "...", "description": "...", "review_count": "...", "rating_overall": "...", "reviews_json": "..." } ],
  "cart": [ /* session cart items */ ]
}
```

### `POST /image`

Supports URL or base64 (from drag & drop).

**Request (URL)**

```json
{ "session_id": "string", "image_url": "https://..." }
```

**Request (Base64)**

```json
{ "session_id": "string", "image_b64": "data:image/png;base64,AAAA..." }
```

**Response**
Same shape as `/chat`.

### `POST /cart/add`

**Request**

```json
{ "session_id": "string", "item": "#2" }
```

or

```json
{ "session_id": "string", "item": "Exact Product Name" }
```

**Response**

```json
{ "answer": "Added **X** to your cart.", "products": [...], "cart": [...] }
```

### `POST /cart/view`

**Request**

```json
{ "session_id": "string" }
```

**Response**

```json
{ "answer": "🛒 Your cart:\n1. ...", "products": [...], "cart": [...] }
```

### `POST /cart/remove`

**Request**

```json
{ "session_id": "string", "item": "#1" }
```

### `POST /cart/checkout`

**Request**

```json
{ "session_id": "string" }
```

### `POST /session/reset`

Resets in-memory session storage.

---

## Data & Search

* **Weaviate** class: `Product`
* Required properties for UI:

  * `product_name` (string)
  * `description` (string)
  * `price` (string or number)
  * `url` (string)
  * `image_url` (string)
* Optional: `review_count`, `rating_overall`, `reviews_json`
* `target_vector="mm_vec"` and `near_text` / `near_image` are used for top-k retrieval.

---

## UI Features

* **Drag & Drop image** into the bottom bar to trigger `/image` with base64.
* Assistant replies rendered as **Markdown** (`react-markdown + remark-gfm`).
* Product cards inline in chat, with “Add to cart” button posting `#index` to backend.
* “Cart” button: triggers `/cart/view` and shows LLM’s cart summary in chat.
* **Scrolling**: stabilized to avoid jumping to page top when typing:

  ```js
  // Only react to message count and use non-smooth
  useEffect(() => {
    if (!listRef.current) return;
    const last = listRef.current.querySelector("[data-last]");
    last?.scrollIntoView({ behavior: "auto", block: "end" });
  }, [messages.length]);
  ```

  And in the list container, ensure the sentinel exists:

  ```jsx
  <div data-last="" />
  ```

---

## Common Fixes / Troubleshooting

### Vite plugin error

```
Cannot find package '@vitejs/plugin-react' imported from vite.config.js
```

Fix:

```bash
npm i -D @vitejs/plugin-react
```

…and ensure `vite.config.js` imports it.

### CORS error

If frontend can’t call backend:

* You already added:

  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
  ```
* If you want to restrict: set `allow_origins=["http://localhost:5173","https://<your-vercel>.vercel.app"]`

---

## Security Notes

* Never commit API keys. Use `.env` / platform secrets.
* Current CORS is `*` for convenience; restrict for production.
* Backend uses in-memory session storage. For multi-instance scale, use Redis or DB for session/cart.

---

## License

MIT — feel free to adapt and ship.


**This readme was generated using AI with human supervision**
