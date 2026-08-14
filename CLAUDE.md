# CLAUDE.md

## Project

Blockchain-Based Academic Credential Verification System — a final-year
capstone project. 3-week build timeline, 3-person team learning the stack
as we go, ~PGK 140 total budget. **Open-source tools only — no commercial
blockchain infrastructure (no Alchemy/Infura paid tiers, no managed chain
services).**

## Architecture

- **Frontend**: React (Vite, plain JavaScript — not TypeScript) SPA styled
  with Tailwind CSS.
- **Backend**: Flask REST API.
- **Dev mode**: Vite dev server proxies `/api/*` requests to Flask.
- **Production**: The React build output (`dist/`) is copied into Flask's
  `static/` folder. Flask serves it directly, with a catch-all route to
  `index.html` so client-side routing works on refresh/deep links. This
  means **one deployable process** and **no CORS in production** (CORS is
  only needed in dev, scoped to the Vite origin).

## Backend

- Flask app organized with **Blueprints**: `auth`, `credentials`, `admin`,
  `verify`.
- **Flask-SQLAlchemy** + **Flask-Migrate** for models and schema migrations.
- **Flask-JWT-Extended** for authentication.
- Password hashing via **Werkzeug's built-in `generate_password_hash` /
  `check_password_hash`** — no extra dependency for this.
- **Flask-CORS**, scoped only to the Vite dev origin (not wildcard, not
  needed at all in prod — see Architecture above).

## Database

**SQLite** for dev/demo — zero setup, zero cost, fits the budget and
timeline. Not intended to scale past the capstone.

Core models:
- **User**: `id, name, email, password_hash, role`
- **Credential**: `id, student_id, title, issue_date, cert_hash,
  chain_tx_id, revoked, revoked_at`
- **AuditLog**: `id, actor_id, action, credential_id, timestamp`

## Auth / RBAC

JWT access tokens carry a `role` claim (`admin` / `student` / `verifier`).
A route decorator enforces role checks on protected endpoints. This is the
**only** permission layer — there is no blockchain-level access control.

## Blockchain

- **Solidity** contract `CertificateRegistry.sol`, deployed to a local
  **Hardhat** node for development.
- The contract stores **only a hash per credential — never personal data**.
- `issueCredential` / `revokeCredential` are restricted to a single owner
  address. `verifyCredential` is a free `view` function anyone can call.
- **Important**: end users (students, verifiers, admins) never hold a
  wallet or sign a transaction. The Flask backend holds **one service
  wallet private key** in `.env` (never committed) and calls the contract
  via **web3.py** on the user's behalf, only after the app's own JWT/RBAC
  layer has authorized the action.

## QR Codes

Generated server-side with the Python `qrcode` library, encoding a link to
`/verify/<cert_id>`.

## Conventions

- Stick to **Python + JavaScript only** — no second backend language.
- Prefer the simplest solution that satisfies the *current phase's*
  acceptance criteria over speculative generality. We have 3 weeks, not a
  production roadmap.
- Never commit `.env`, `venv/`, `__pycache__/`, `node_modules/`, or `dist/`
  (see `.gitignore`).
