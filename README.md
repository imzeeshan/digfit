# DigFit

Django app for DigFit. Auth, payments, dashboard, and deployment — all wired up.

<div align="center">
  <img src="https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django"/>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Tailwind_CSS-CDN-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS"/>
  <img src="https://img.shields.io/badge/Stripe-Payments-6772E5?style=for-the-badge&logo=stripe&logoColor=white" alt="Stripe"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License: MIT"/>
</div>

---

## What's included

- **Custom user model** — email-only login, no username
- **Authentication** — signup, login, email verification, password reset (django-allauth)
- **Stripe subscriptions** — Payment Methods API, webhooks, subscription status tracking
- **User dashboard** — sidebar nav, profile (with avatar upload), settings, notification preferences, API keys
- **Weight log reminders** — in-app alerts when a user has not logged weight within a configurable day window (optional one-time email)
- **Subscription plans** — admin-managed plans with trial support
- **REST API** — Django REST Framework with session + token auth (including **`/api/auth/login/`** for API tokens)
- **Meal plan vs logs** — compare planned `MealEntry` rows to logged `UserMeal` entries via **LLM** (Ollama) or **DB** (deterministic JSON: slots, daily totals, insights)
- **MCP server** — django-drf-mcp auto-exposes API endpoints as MCP tools for AI assistants
- **Ollama integration** — local LLM tool-calling via MCP (chat with your API using llama3.1, qwen2.5, etc.)
- **Audit trails** — automatic change tracking on all models (django-auditlog)
- **Background tasks** — Django 6.0 native `@task()` decorator, no Celery needed
- **Content Security Policy** — Django 6.0 built-in CSP middleware with nonces
- **Template partials** — Django 6.0 `{% partialdef %}` for reusable components
- **Security headers** — HSTS, SSL redirect, secure cookies (auto-enabled in production)
- **PostgreSQL support** — `DATABASE_URL` with SQLite fallback
- **Static files** — WhiteNoise, no nginx needed
- **Deployment** — Gunicorn + Procfile, ready for Railway/Heroku/VPS
- **Linting** — Ruff with Django-specific rules
- **Automated tests** — landing, auth, API token login/logout, dashboard, models
- **Seed data** — one command to populate demo data

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0, Python 3.12 |
| Auth | django-allauth (email-only) |
| Payments | Stripe (Payment Methods API) |
| Frontend | Tailwind CSS (CDN), Alpine.js, HTMX |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Static files | WhiteNoise |
| Server | Gunicorn |
| API | Django REST Framework |
| MCP | django-drf-mcp (Model Context Protocol) |
| LLM | Ollama (local models with tool calling) |
| Tasks | Django 6.0 native `@task()` |
| Audit | django-auditlog |
| Linting | Ruff |

## Quick start

```bash
git clone <your-repository-url>
cd digfit
cp .env.example .env
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Visit **http://localhost:8000** — Django admin: **http://localhost:8000/admin/** (`admin@example.com` / `admin123` after seeding)

## Docker

Run the full stack (Gunicorn + PostgreSQL) with Docker Compose. Migrations and static files run automatically on startup; **seed data is a separate step** (not run by the container entrypoint).

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine + Compose v2

### First-time setup

```bash
git clone <your-repository-url>
cd digfit
cp .env.example .env
docker compose up --build
```

Wait until the `web` service logs show Gunicorn is ready:

```text
Listening at: http://127.0.0.1:8000
```

In a **second terminal**, seed the database (admin user, demo users, subscription plans):

```bash
docker compose exec web python manage.py seed_data
```

Open the app:

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000 | Public site / dashboard (after login) |
| http://127.0.0.1:8000/admin/ | Django admin |

**Seed credentials** (safe for local dev only — change in production):

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@example.com` | `admin123` |
| Coach | `coach@example.com` | `coach123` |
| User | `user@example.com` | `user1234` |

To create a custom superuser instead of (or in addition to) seed data:

```bash
docker compose exec web python manage.py createsuperuser
```

### What Docker runs

| Service | Image / build | Port | Notes |
|---------|---------------|------|-------|
| `web` | Built from `Dockerfile` | **8000** | Runs `migrate`, `collectstatic`, then Gunicorn |
| `db` | `postgres:16-alpine` | internal | User/db/password: `dig_fit` / `dig_fit` / `dig_fit` |

`docker-compose.yml` sets `DATABASE_URL` to PostgreSQL inside the compose network. Your `.env` is still loaded for Stripe, email, Ollama, etc.; compose overrides `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `DATABASE_URL` for the container.

### Useful commands

```bash
# Start in the background
docker compose up -d --build

# Follow logs
docker compose logs -f web

# Stop containers (keep database volume)
docker compose down

# Stop and delete the PostgreSQL data volume (fresh DB)
docker compose down -v

# Run tests inside the web container
docker compose exec web python manage.py test

# Django shell
docker compose exec web python manage.py shell
```

### Ollama from Docker

Ollama usually runs on the host. On Docker Desktop, uncomment in `docker-compose.yml`:

```yaml
OLLAMA_HOST: http://host.docker.internal:11434
```

Ensure the model is pulled on the host (`ollama pull medgemma:4b` or your chosen model).

## Project structure

```
digfit/
├── manage.py
├── core/
│   ├── settings.py           # All config via env vars
│   ├── urls.py               # Root URL routing
│   ├── wsgi.py / asgi.py
│   ├── authentication.py     # MCP token auth for DRF
│   ├── permissions.py
│   ├── ollama_client.py      # Ollama HTTP client
│   └── management/commands/  # mcp_chat, ollama_ping
├── apps/
│   ├── accounts/             # CustomUser (email-only), admin
│   │   ├── models.py         # CustomUser + CustomUserManager
│   │   ├── admin.py
│   │   └── tests.py
│   ├── dashboard/            # Dashboard, profile, settings, meal plans
│   │   ├── models.py         # MealPlan, UserMeal, UserSettings, Weight, …
│   │   ├── views.py / urls.py / admin.py
│   │   ├── meal_plan_compare.py  # Shared context, plan resolution, DB compare
│   │   ├── meal_plan_llm.py      # LLM compare (Ollama)
│   │   ├── notifications.py  # Sync weight-overdue in-app notifications
│   │   ├── signals.py        # Re-sync notifications on weight/settings changes
│   │   ├── tasks.py          # Background email tasks
│   │   ├── context_processors.py
│   │   ├── tests.py
│   │   └── management/commands/
│   │       ├── seed_data.py
│   │       ├── sync_notifications.py
│   │       └── check_weight_reminders.py
│   ├── api/                  # REST API + MCP
│   │   ├── serializers.py
│   │   ├── auth_views.py     # POST /api/auth/login/, /logout/
│   │   ├── views.py          # ViewSets (users, meal-plans, weights, …)
│   │   ├── urls.py
│   │   └── tests.py
│   ├── subscriptions/        # Stripe integration
│   │   ├── models.py         # StripeCustomer
│   │   ├── views.py          # checkout, webhooks
│   │   └── urls.py
│   └── landing/              # Public pages
│       ├── views.py          # home, features, pricing, robots.txt
│       ├── urls.py
│       └── tests.py
├── templates/
│   ├── base.html             # Public layout (nav + footer)
│   ├── account/              # allauth templates (styled)
│   ├── dashboard/            # Dashboard layout + pages + audit logs
│   ├── landing/              # Home, features, pricing
│   └── subscriptions/        # Stripe checkout
├── static/css/               # Design system CSS
├── docker/
│   └── entrypoint.sh         # migrate + collectstatic, then exec CMD
├── Dockerfile
├── docker-compose.yml        # web (Gunicorn) + PostgreSQL
├── .dockerignore
├── API.md                    # REST API reference
├── DATABASE.MD               # Schema / models overview
├── DigFit_API.postman_collection.json
├── screenshots/              # App screenshots
├── CLAUDE.md                 # AI editor context
├── CONTRIBUTING.md
├── Makefile                  # Dev commands
├── Procfile                  # Railway / Heroku (Gunicorn)
├── pyproject.toml            # Ruff config
├── requirements.txt
└── .env.example
```

## Environment variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
DEBUG=True
SECRET_KEY=your-secret-key

# Database (default: SQLite)
# DATABASE_URL=postgres://user:password@localhost:5432/dbname

# Stripe (required for payments)
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

# Ollama (local LLM — install from https://ollama.com)
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=medgemma:4b

# Email (default: console backend)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_HOST_USER=your-email@gmail.com
# EMAIL_HOST_PASSWORD=your-app-password
```

## Django 6.0 features used

This project uses three major features introduced in Django 6.0:

**Background Tasks** — Send emails asynchronously without Celery:
```python
from django.tasks import task

@task
def send_welcome_email(user_email):
    send_mail("Welcome!", "...", None, [user_email])

# In your view:
send_welcome_email.enqueue(user_email=user.email)
```

**Content Security Policy** — Built-in CSP middleware with nonce support:
```python
SECURE_CSP = {
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
}
```
```html
<script nonce="{{ csp_nonce }}" src="..."></script>
```

**Template Partials** — Reusable template components without separate files:
```html
{% partialdef stat_card inline %}
<div class="card">{{ card_title }}: {{ card_value }}</div>
{% endpartialdef %}

{% with card_title="Users" card_value="42" %}
    {% partial stat_card %}
{% endwith %}
```

## Audit Trails

Every create, update, and delete across all models is automatically logged using [django-auditlog](https://github.com/jazzband/django-auditlog). The audit log captures:

- **Who** made the change (authenticated user via middleware)
- **What** changed (old and new field values)
- **When** the change occurred
- **Which** model and object were affected

**Tracked models:** CustomUser, SubscriptionPlan, UserSettings, Weight, MealPlan, UserMeal, Intervention, StripeCustomer

**Excluded fields** (sensitive data): `password`, `last_login`, `api_key_hash`

**Dashboard view:** Staff users can browse and filter the full audit log at `/dashboard/audit-logs/` (sidebar: Admin > Audit Logs). The Django admin also shows per-object history via the "Audit log" link on each record.

## Weight log reminders

Users can be reminded to log their weight when they have not recorded an entry within a configurable window. Reminders appear as **in-app notifications** on the dashboard; an optional **one-time email** is sent when a new overdue alert is first created.

### When a user is “overdue”

| Setting | Location | Default |
|---------|----------|---------|
| `weight_reminder_days` | Dashboard **Settings** or `PATCH /api/settings/me/` | **5** days |
| Disabled | Set `weight_reminder_days` to **0** | — |

Logic lives in `UserSettings.get_weight_reminder()` (`apps/dashboard/models.py`): if the latest `Weight` entry for the user is older than `weight_reminder_days` (or there is no entry), the user is overdue.

### How often checks run

There is **no built-in cron or periodic worker** for weight reminders. Overdue state is **recomputed on demand** whenever sync runs:

| Trigger | Code |
|---------|------|
| Authenticated dashboard or landing page load | `apps/dashboard/context_processors.py` → `sync_user_notifications()` |
| Weight create, update, or delete | `apps/dashboard/signals.py` |
| User settings save | `apps/dashboard/signals.py` |
| `GET /api/notifications/` | `NotificationViewSet.get_queryset()` in `apps/api/views.py` |
| `GET /api/weights/reminder/` (legacy) | `WeightViewSet.reminder` in `apps/api/views.py` |

Core sync: `sync_weight_reminder_notification()` and `sync_user_notifications()` in `apps/dashboard/notifications.py`. This creates, updates, or deletes a persisted `Notification` with type `weight_log_overdue`.

For **all users** without waiting for traffic (e.g. to refresh alerts or send emails for inactive users), run manually or on a schedule you configure:

```bash
python manage.py sync_notifications
python manage.py check_weight_reminders   # same sync + prints overdue summary
```

Docker:

```bash
docker compose exec web python manage.py sync_notifications
```

Nothing in `docker-compose.yml` runs these commands automatically; use **cron**, **systemd timers**, or your host’s scheduler if you want daily batch sync (the `check_weight_reminders` docstring suggests daily as an example).

### Email

Email is sent **once per overdue alert**, only when the in-app notification is **first created**, and only if **Product updates** (`notify_updates` on user settings) is enabled.

| Piece | Location |
|-------|----------|
| Enqueue guard | `maybe_send_weight_reminder_email()` in `apps/dashboard/notifications.py` |
| Background send | `send_weight_reminder_email` in `apps/dashboard/tasks.py` (`@task` + `.enqueue()`) |

Repeated page loads or syncs update the in-app message but do **not** resend email (`email_sent_at` on the notification prevents duplicates).

### API

| Endpoint | Description |
|----------|-------------|
| `GET /api/notifications/` | Lists active notifications (syncs on each request) |
| `POST /api/notifications/{id}/dismiss/` | Dismiss an alert |
| `GET /api/weights/reminder/` | Legacy overdue check (prefer notifications) |

See **[API.md](API.md)** for request/response shapes.

## REST API

All endpoints except **`POST /api/auth/login/`** require authentication (session or token). The API root is at `/api/`.

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/auth/login/` | POST | Email + password → API token (no auth) |
| `/api/auth/logout/` | POST | Revoke current API token |
| `/api/users/` | GET | List users (admin: all, user: self) |
| `/api/users/me/` | GET, PATCH | Current user profile |
| `/api/plans/` | GET | Active subscription plans |
| `/api/plans/{slug}/` | GET, PUT, DELETE | Plan detail (write: admin only) |
| `/api/settings/` | GET | User settings |
| `/api/settings/me/` | GET, PATCH | Update notification preferences |
| `/api/stripe-customers/` | GET | Stripe records (admin only) |
| `/api/weights/` | GET, POST | Weight entries (admin: all, user: own) |
| `/api/weights/reminder/` | GET | Legacy: weight log overdue status (prefer `/api/notifications/`) |
| `/api/weights/{id}/` | GET, PUT, PATCH, DELETE | Weight detail |
| `/api/notifications/` | GET | Active in-app notifications (synced on list) |
| `/api/notifications/{id}/` | GET | Notification detail |
| `/api/notifications/{id}/dismiss/` | POST | Dismiss notification |
| `/api/notifications/{id}/read/` | POST | Mark notification read |
| `/api/meal-plans/` | GET, POST | Meal plans (admin: all, user: own) |
| `/api/meal-plans/{id}/` | GET, PUT, PATCH, DELETE | Meal plan detail |
| `/api/meal-plans/{id}/compare-meals/` | POST | **LLM:** compare that plan vs logged meals in range |
| `/api/meal-plans/by-user/{user_id}/compare-meals/` | POST | **LLM:** resolve plan for user, then compare vs logged meals |
| `/api/meal-plans/{id}/compare-meals-db/` | POST | **DB:** deterministic compare for a specific plan (no Ollama) |
| `/api/meal-plans/by-user/{user_id}/compare-meals-db/` | POST | **DB:** resolve plan for user, then deterministic compare |
| `/api/user-meals/` | GET, POST | User meals (admin: all, user: own) |
| `/api/user-meals/{id}/` | GET, PUT, PATCH, DELETE | User meal detail |
| `/api/interventions/` | GET, POST | Interventions (admin: all, user: own) |
| `/api/interventions/{id}/` | GET, PUT, PATCH, DELETE | Intervention detail |

**Obtain a token (login):**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"your-password"}'
```

**Token auth example** (`Authorization` must use the prefix **`Token`**, not `Bearer`):
```bash
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/users/me/
```

Full field lists and curl examples: **[API.md](API.md)**. Postman: **[DigFit_API.postman_collection.json](DigFit_API.postman_collection.json)**.

### Meal plan vs logged meals (compare)

Compare what was **planned** (`MealPlan` + `MealEntry` rows, targets, foods) with what the user **logged** (`UserMeal` rows whose dates fall inside the plan’s `start_date`–`end_date`). All four endpoints use an **empty POST body** and require `Authorization: Token <key>` (staff may compare any user on the **by-user** routes; regular users only their own `user_id`).

| Endpoint | Mode | Description |
|----------|------|-------------|
| `POST /api/meal-plans/{id}/compare-meals/` | LLM | Compare one meal plan by id |
| `POST /api/meal-plans/by-user/{user_id}/compare-meals/` | LLM | Auto-select a plan for the user, then compare |
| `POST /api/meal-plans/{id}/compare-meals-db/` | DB | Deterministic compare for one plan (no Ollama) |
| `POST /api/meal-plans/by-user/{user_id}/compare-meals-db/` | DB | Auto-select a plan, then deterministic compare |

Postman: **Meal plans** folder in [DigFit_API.postman_collection.json](DigFit_API.postman_collection.json) (all four requests).

#### LLM compare (`compare-meals`)

Uses a **local Ollama** model for narrative analysis (`compare_mode`: `llm`, field `analysis`).

| Piece | Location / behavior |
|-------|------------------------|
| Context + prompt | `apps/dashboard/meal_plan_compare.py` — `build_meal_comparison_context()`; `apps/dashboard/meal_plan_llm.py` — `compare_meal_plan_to_logged_meals()` |
| Ollama call | `core/ollama_client.py` — `chat_for_user()` uses the **plan owner’s** **UserSettings** (host/model), with `OLLAMA_HOST` / `OLLAMA_MODEL` as fallback |
| Plan resolution (by user) | `resolve_meal_plan_for_user_comparison()` in `meal_plan_compare.py` — among plans overlapping **today**, prefers the most **MealEntry** rows then latest `start_date`; if in-window plans have no entries, falls back to the latest plan with entries (`meal_plan_selection`: `fallback_latest_with_entries`); otherwise best plan by entry count |
| HTTP | `MealPlanViewSet` — `compare_meals`, `compare_meals_by_user` |

**By-user response extras:** `user_id`, `meal_plan_title`, `meal_plan_selection` (`active_window`, `fallback_latest_with_entries`, or `latest_by_start_date`), `date_range`, entry/meal counts. **404** if the user has no meal plan.

**Failures:** **503** if Ollama is unreachable (`error`: `llm_compare_failed`). Ensure Ollama is running and the model is pulled (see `OLLAMA_*` in **Environment variables**).

#### DB compare (`compare-meals-db`)

Pure ORM logic — no LLM required (`compare_mode`: `db`). Useful for dashboards, tests, and clients that want structured data.

| Piece | Location / behavior |
|-------|------------------------|
| Compare logic | `apps/dashboard/meal_plan_compare.py` — `compare_meal_plan_db()` |
| HTTP | `MealPlanViewSet` — `compare_meals_db`, `compare_meals_by_user_db` |

**Response highlights:** `summary` (counts, adherence, planned vs actual calorie totals), `daily` (per-day breakdown), `by_meal_type`, `slots` (each planned entry with status `linked`, `matched_unlinked`, or `missing_log`), `extra_meals` (logs in the window that do not match a slot), `insights` (short deterministic bullets). Matching uses explicit `MealEntry.actual_meal` links first, then same calendar day + `meal_type`.

**Example:**
```bash
curl -X POST http://localhost:8000/api/meal-plans/by-user/3/compare-meals-db/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**MCP:** Compare routes are exposed like other `/api/*` operations in `tools/list`. **`POST /api/auth/login/`** is excluded from MCP tools in settings.

## MCP (Model Context Protocol)

[django-drf-mcp](https://github.com/Joel-hanson/django-drf-mcp) auto-discovers all DRF endpoints and exposes them as MCP tools for AI assistants.

- **Health check:** `GET /mcp/`
- **JSON-RPC:** `POST /mcp/` (initialize, tools/list, tools/call)

**Connect Claude Desktop / Claude Code:**
```json
{
  "mcpServers": {
    "digfit": {
      "command": "python",
      "args": ["manage.py", "runmcp", "--transport", "stdio"]
    }
  }
}
```

**Standalone server:**
```bash
python manage.py runmcp --transport streamable-http --port 8001
```

### MCP + Local Ollama

You can connect a local Ollama model to the DigFit API via MCP, letting the LLM call your API endpoints as tools (list weights, create meal plans, etc.).

**Prerequisites:**

1. [Install Ollama](https://ollama.com) and pull a model that supports tool calling:
   ```bash
   ollama pull gemma4:e4b
   # Other options: llama3.1, qwen2.5, mistral
   ```

2. Make sure the Django dev server is running (`make run`)

**Interactive chat:**

```bash
# Default (gemma4:e4b)
python manage.py mcp_chat

# Use a different model
python manage.py mcp_chat --model llama3.1

# Point to a remote Django server
python manage.py mcp_chat --base-url http://192.168.1.100:8000
```

**How it works:**

```
User prompt → Ollama LLM → tool call → MCP endpoint (/mcp/) → DRF API → result → LLM → answer
```

1. The command fetches available MCP tools from `POST /mcp/` (`tools/list`)
2. Converts them to Ollama's tool-calling format
3. Sends the user prompt + tool definitions to the local Ollama model
4. When Ollama returns a tool call, it executes via `POST /mcp/` (`tools/call`)
5. The result is fed back to Ollama until it produces a final text answer

**Example session:**

```
$ python manage.py mcp_chat
Ollama model : gemma4:e4b
Django server: http://localhost:8000
Fetching MCP tools...
Loaded 12 tools: api_weights_list, api_weights_create, ...
Type your message (Ctrl+C to quit):

> Show me all weight entries
  Tool call: api_weights_list({})
  Result: [{"id": 1, "value": "185.50", "datetime": "2026-05-10T08:00:00Z", ...}]
```

## Deployment

### Railway

Push to GitHub and connect to Railway. The `Procfile` and `DATABASE_URL` handling are already configured.

### Heroku

```bash
heroku create your-app-name
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DEBUG=False
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py seed_data
```

### VPS

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic
gunicorn core.wsgi --bind 0.0.0.0:8000
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License. See [LICENSE](LICENSE) for details.

