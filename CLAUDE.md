# artifacts

This is an **OpenResty (nginx + LuaJIT) reverse proxy** that serves Scality build artifacts stored in a Google Cloud Storage S3-compatible bucket. It contains:

- Lua scripts for request handling (`lua/`) — S3 signature computation, GitHub org-based auth, build lookup, metadata, copy operations, directory browsing
- nginx config template (`conf/nginx.conf.template`) — wired to the Lua scripts via `*_by_lua_file` directives; uses XSLT for HTML directory listings
- XSLT template (`xslt/`) — renders S3 XML listings as HTML
- Helm chart (`charts/artifacts/`) — Kubernetes deployment config
- Python integration tests (`tests/`) — pytest + boto3 + requests, run against a live stack in CI
- Shell startup scripts (`start.sh`, `stop.sh`) — resolve DNS for S3 endpoints and render the nginx config template at container start

Key env vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BUCKET_PREFIX`, `ENDPOINT_URL`, `GITHUB_API_ENABLED`, `GITHUB_API_COMPANY`, `GITHUB_USER_ALLOWED_UPLOAD`, `BOT_USERNAME`, `BOT_TOKEN`.

No Scality internal git-based dependencies (no arsenal, vaultclient, etc.).
