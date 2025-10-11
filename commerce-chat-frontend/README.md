# Commerce Chat Frontend (React + Tailwind)

A simple, pretty chat UI that connects to your deployed backend.

## 🧰 What you need
- **Node.js** (LTS). If you don't have it:
  - **Windows/Mac**: https://nodejs.org (download & install LTS)
  - After install, open **Terminal** (Mac) or **Command Prompt** (Windows).

## ⚡ Quick Start (Local)
1. Unzip this folder.
2. In your terminal, go into the project:
   ```bash
   cd commerce-chat-frontend
   ```
3. Install dependencies (one-time):
   ```bash
   npm install
   ```
4. (Optional) Set your backend URL:
   - Copy `.env.example` to `.env` and keep the default, or change it:
     ```bash
     cp .env.example .env
     # edit .env if your backend URL differs
     ```
5. Run the app:
   ```bash
   npm run dev
   ```
6. Open the link shown (usually http://localhost:5173).

## 🚀 Deploy (Vercel – easiest)
1. Create a free account at https://vercel.com and install the Vercel CLI:
   ```bash
   npm i -g vercel
   ```
2. In the project folder, run:
   ```bash
   vercel
   ```
   - When asked for *framework*, choose **Vite** (or it auto-detects).
   - After first deploy, for production:
     ```bash
     vercel deploy --prod
     ```
3. In the Vercel dashboard, set an **Environment Variable**:
   - `VITE_API_BASE` = `https://macro-crane-474800-p9.uw.r.appspot.com` (or your backend URL)
   - Re-deploy.

## 🧪 How to use
- Type: “recommend running shoes under $100” → calls `/chat`
- Paste an **image URL** (ending in .jpg/.png/…) and click **Search by image** → calls `/image`
- Cart commands in chat: `add #2`, `view cart`, `remove #1`, `checkout`

## 🔧 Where to change the backend URL
- In `.env` set `VITE_API_BASE`
- Or edit `src/App.jsx` to hardcode a URL.

Enjoy!
