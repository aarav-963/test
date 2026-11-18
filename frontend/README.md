# EventSphere

React frontend for campus event discovery and registration. The UI reads and writes through the API at `https://test-39sh.onrender.com` and includes no login or authentication flow.

## Deploy to Vercel

1. Push this project to a Git repository and import it in Vercel.
2. Keep the framework preset as **Vite**. The included `vercel.json` sets the build command to `npm run build` and the output directory to `dist`.
3. Deploy. No environment variables are required.

The included Vercel rewrite forwards `/api/*` paths and query strings to the deployed API. Vercel adds CORS response headers for those routes. If the backend URL changes, update the rewrite destination in `vercel.json` and redeploy.

## Run locally

```sh
npm install
npm run dev
```

The Vite development server proxies `/api/*` requests to the same backend. To run the production-style Express server locally, use `npm run build` followed by `npm start`.
