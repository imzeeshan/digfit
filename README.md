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
- **Subscription plans** — admin-managed plans with trial support
- **REST API** — Django REST Framework with session + token auth
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
- **16 tests** — landing pages, auth, dashboard, models
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
cd dig_fit
make install
cp .env.example .env
make migrate
python manage.py seed_data
make run
```

Visit **http://localhost:8000** — admin login: `admin@example.com` / `admin123`

## Commands

| Command | Description |
|---------|-------------|
| `make install` | Create virtualenv and install dependencies |
| `make run` | Start development server |
| `make migrate` | Run makemigrations + migrate |
| `make test` | Run 16 tests |
| `make seed` | Populate demo data (admin + plans) |
| `make lint` | Lint with ruff |
| `make format` | Format with ruff |
| `make superuser` | Create admin user |
| `make clean` | Remove __pycache__ files |
| `python manage.py mcp_chat` | Chat with Ollama using DigFit API as MCP tools |
| `python manage.py ollama_ping` | Verify Ollama is reachable |
| `python manage.py runmcp` | Start standalone MCP server (stdio/sse/http) |

## Project structure

```
dig_fit/
├── core/
│   ├── settings.py           # All config via env vars
│   ├── urls.py               # Root URL routing
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/             # CustomUser (email-only), admin
│   │   ├── models.py         # CustomUser + CustomUserManager
│   │   ├── admin.py
│   │   └── tests.py          # 6 tests
│   ├── dashboard/            # Dashboard, profile, settings
│   │   ├── models.py         # SubscriptionPlan, UserSettings
│   │   ├── views.py          # dashboard, profile, settings, plans
│   │   ├── tasks.py          # Background email tasks
│   │   ├── tests.py          # 6 tests
│   │   └── management/commands/seed_data.py
│   ├── api/                  # REST API + MCP
│   │   ├── serializers.py    # DRF serializers
│   │   ├── views.py          # ViewSets (users, plans, settings)
│   │   └── urls.py           # Router-based URL config
│   ├── subscriptions/        # Stripe integration
│   │   ├── models.py         # StripeCustomer
│   │   └── views.py          # checkout, webhooks
│   └── landing/              # Public pages
│       ├── views.py          # home, features, pricing, robots.txt
│       └── tests.py          # 4 tests
├── templates/
│   ├── base.html             # Public layout (nav + footer)
│   ├── account/              # 20 allauth templates (styled)
│   ├── dashboard/            # Dashboard layout + pages + audit logs
│   ├── landing/              # Home, features, pricing
│   └── subscriptions/        # Stripe checkout
├── static/css/               # Design system CSS
├── CLAUDE.md                 # AI editor context
├── Makefile                  # Dev commands
├── Procfile                  # Deployment
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

## REST API

All endpoints require authentication (session or token). The API root is at `/api/`.

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/users/` | GET | List users (admin: all, user: self) |
| `/api/users/me/` | GET, PATCH | Current user profile |
| `/api/plans/` | GET | Active subscription plans |
| `/api/plans/{slug}/` | GET, PUT, DELETE | Plan detail (write: admin only) |
| `/api/settings/` | GET | User settings |
| `/api/settings/me/` | GET, PATCH | Update notification preferences |
| `/api/stripe-customers/` | GET | Stripe records (admin only) |
| `/api/weights/` | GET, POST | Weight entries (admin: all, user: own) |
| `/api/weights/{id}/` | GET, PUT, PATCH, DELETE | Weight detail |
| `/api/meal-plans/` | GET, POST | Meal plans (admin: all, user: own) |
| `/api/meal-plans/{id}/` | GET, PUT, PATCH, DELETE | Meal plan detail |
| `/api/user-meals/` | GET, POST | User meals (admin: all, user: own) |
| `/api/user-meals/{id}/` | GET, PUT, PATCH, DELETE | User meal detail |
| `/api/interventions/` | GET, POST | Interventions (admin: all, user: own) |
| `/api/interventions/{id}/` | GET, PUT, PATCH, DELETE | Intervention detail |

**Token auth example:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/users/me/
```

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

