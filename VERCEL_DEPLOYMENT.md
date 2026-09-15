# 🚀 Deploying SURVI / LANDNEXUS to Vercel

This repository is fully configured for seamless deployment to **Vercel**.

---

## 🛠️ Summary of Fixes Applied for Vercel

1. **Vercel Routing Configuration (`vercel.json`)**:
   - Added rewrite rules (`/(.*) -> /index.html`) so refreshing or direct navigation to subpaths (e.g. `/documents`, `/parcels`, `/gis`, `/data-quality`) does not result in a `404 Not Found` error.
2. **Missing Vite Configuration (`vite.config.js`)**:
   - Created `vite.config.js` properly wiring `@vitejs/plugin-react`, port configurations, dev server proxying, and production chunk optimization.
3. **Monorepo & Multi-Folder Deployment Support**:
   - Added root-level and frontend-level `vercel.json` and `package.json` configurations. Whether you import the repository root, the inner project folder, or select `frontend` as the Root Directory, Vercel detects and builds the project automatically.
4. **Resilient API URL Handling & Trailing Slash Sanitization**:
   - Fixed API base URL resolution in `src/App.jsx` to automatically strip trailing slashes, preventing double-slash failures (e.g., `https://api.domain.com//auth/login`).
   - Added friendly error handling when non-JSON responses (like HTML fallback pages) are received, clearly instructing users if `VITE_API_URL` is missing.
5. **Session Safety & Null Checks**:
   - Guarded user role and token state initialization to eliminate React crashes (`Cannot read properties of undefined`).
   - Added safe checks in `Cards` and `allowedNav` components.
6. **Instant UI Preview Mode**:
   - Added a **"⚡ Preview UI Directly (No Backend Required)"** button on the login screen. You can showcase the dashboard, GIS maps, workflow tabs, and data quality inspector on Vercel immediately, even before configuring a live backend.

---

## 📋 How to Deploy to Vercel

### Method 1: Deploy via GitHub (Recommended)

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Configure Vercel deployment and fix build errors"
   git push origin main
   ```

2. **Import into Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new).
   - Select your GitHub repository (`Land-Aquisation`).
   - Framework Preset: **Vite** (auto-detected).
   - If deploying from repository root, keep default settings or set **Root Directory** to `frontend` (both work).

3. **Configure Environment Variable (Optional for Live Backend)**:
   - In the **Environment Variables** section, add:
     - **Key**: `VITE_API_URL`
     - **Value**: `https://your-backend-service.onrender.com` (your hosted backend URL, e.g., on Render, Railway, or Fly.io)
   - *Note: If you leave this empty, the frontend runs smoothly and you can use the instant preview mode or local dev proxy.*

4. **Click Deploy**:
   - Vercel will install dependencies, build the Vite application in seconds, and assign a production URL (e.g., `https://land-acquisition.vercel.app`).

---

### Method 2: Deploy via Vercel CLI

1. Install Vercel CLI (if not installed):
   ```bash
   npm i -g vercel
   ```
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   vercel
   ```
3. Follow the CLI prompts to deploy. For production:
   ```bash
   vercel --prod
   ```

---

## ⚙️ Backend Hosting Recommendation
Because the backend uses FastAPI, PyTesseract (OCR with native system binaries), Poppler (`pdf2image`), and Scikit-Learn/SHAP ML models with SQLite persistence, it should be deployed on a continuous container host such as:
- [Render.com](https://render.com) (Web Service using Docker or Python)
- [Railway.app](https://railway.app)
- [Fly.io](https://fly.io)
- Or locally exposed using `run_tunnel.bat` (Cloudflare / Localtunnel)
