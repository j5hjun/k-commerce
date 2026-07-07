# K-Commerce Web

K-Commerce Web is the Next.js frontend for the K-Commerce agent backend.

Korean documentation is available in [README.ko.md](README.ko.md).

## Getting Started

Install dependencies and run the development server:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

The frontend expects the agent backend to be available at `http://127.0.0.1:8000` by default.

## Backend

From the repository root, start the agent backend with:

```bash
uv run k-commerce-agent
```

The backend exposes health, MCP tool metadata, and streaming chat endpoints.
