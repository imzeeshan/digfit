# DigFit REST API

Base URL: `/api/`

All endpoints return JSON. Paginated list endpoints return 20 items per page (configurable via `?page=N`).

---

## Authentication

Every request must include one of the following:

| Method | Header / Mechanism | Notes |
|---|---|---|
| **Session** | Django session cookie | Automatic after browser login |
| **Token** | `Authorization: Token <key>` | DRF token — obtain via **`POST /api/auth/login/`** (see below). **Use the word `Token`, not `Bearer`.** Postman’s “Bearer Token” type will not work. |
| **MCP Internal** | `X-MCP-Token: <token>` | Used by the MCP chat bridge; authenticates as superuser |

Unauthenticated requests receive `401 Unauthorized` (except **`POST /api/auth/login/`**, which is public).

### Obtain token (login)

`POST /api/auth/login/` — **no auth header.** JSON body:

| Field | Type | Required |
|---|---|---|
| `email` | string | Yes |
| `password` | string | Yes |

**Success (200):** `{ "token": "<40-char hex key>" }` — use as `Authorization: Token <key>` on subsequent requests. A new row in `authtoken_token` is created if the user had none; otherwise the existing key is returned.

**Failure (400):** invalid credentials or validation errors.

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"your-password"}'
```

### Logout (invalidate token)

`POST /api/auth/logout/` — requires `Authorization: Token <key>`. Deletes that user’s token. **204** with empty body on success.

```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Token <your-token>"
```

---

## Permission Model

| Role | Scope |
|---|---|
| **Regular user** | Can only read/write their own data. `user` is set automatically on create. |
| **Admin** (`is_staff`) | Can see and manage all users' data. Can filter by `?user=<id>`. |

Endpoints marked **Admin only** require `is_staff=True`.

---

## Pagination

All list endpoints are paginated.

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/weights/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

---

## Endpoints

### API root (`GET /api/`)

Returns JSON hyperlinks for each **viewset list** URL (e.g. `users`, `meal-plans`, `weights`) and for **`auth-login`** / **`auth-logout`**. Custom `@action` routes (such as `meal-plans/.../compare-meals/`) are **not** duplicated here; they live under their resource’s URL patterns (see tables below and the browsable API). Requires authentication like other API routes unless you use the browsable HTML with an active session.

### Auth (API token)

| Method | URL | Permission | Description |
|---|---|---|---|
| `POST` | `/api/auth/login/` | Public | Email + password → `{ "token": "…" }` |
| `POST` | `/api/auth/logout/` | Token | Deletes the caller’s token (204) |

### Users

Read-only. Admin sees all users; regular users see only themselves.

| Method | URL | Permission | Description |
|---|---|---|---|
| `GET` | `/api/users/` | Authenticated | List users |
| `GET` | `/api/users/{id}/` | Authenticated | Retrieve user |
| `GET` | `/api/users/me/` | Authenticated | Current user profile |
| `PATCH` | `/api/users/me/` | Authenticated | Update current user profile |

#### Response fields

| Field | Type | Notes |
|---|---|---|
| `id` | int | Read-only |
| `email` | string | Read-only |
| `name` | string | |
| `role` | string | Read-only |
| `date_of_birth` | date (YYYY-MM-DD) | Nullable |
| `gender` | string | Nullable |
| `metadata` | object | Arbitrary JSON |
| `profile_pic` | string | Extracted from `metadata.profile_pic` |
| `is_active` | bool | Read-only |
| `date_joined` | datetime | Read-only |

#### PATCH `/api/users/me/`

Updatable fields: `name`, `date_of_birth`, `gender`, `metadata`.

```json
{
  "name": "Jane Doe",
  "date_of_birth": "1990-06-15"
}
```

---

### Subscription Plans

Admin has full CRUD; regular users can list/retrieve active plans only.

| Method | URL | Permission | Description |
|---|---|---|---|
| `GET` | `/api/plans/` | Authenticated | List plans (users see active only) |
| `GET` | `/api/plans/{slug}/` | Authenticated | Retrieve plan by slug |
| `POST` | `/api/plans/` | Admin | Create plan |
| `PUT` | `/api/plans/{slug}/` | Admin | Full update |
| `PATCH` | `/api/plans/{slug}/` | Admin | Partial update |
| `DELETE` | `/api/plans/{slug}/` | Admin | Delete plan |

**Lookup field:** `slug` (not `id`).

#### Fields

| Field | Type | Writable | Notes |
|---|---|---|---|
| `id` | int | No | |
| `name` | string | Yes | |
| `slug` | string | Yes | URL-safe identifier |
| `description` | string | Yes | |
| `price` | decimal | Yes | |
| `interval` | string | Yes | e.g. `month`, `year` |
| `features` | object | Yes | JSON |
| `is_active` | bool | Yes | |
| `created_at` | datetime | No | |
| `updated_at` | datetime | No | |

---

### User Settings

Retrieve and update notification preferences and subscription info. No create/delete (auto-created per user).

| Method | URL | Permission | Description |
|---|---|---|---|
| `GET` | `/api/settings/` | Authenticated | List (admin sees all) |
| `GET` | `/api/settings/{id}/` | Authenticated | Retrieve |
| `PUT` | `/api/settings/{id}/` | Authenticated | Full update |
| `PATCH` | `/api/settings/{id}/` | Authenticated | Partial update |
| `GET` | `/api/settings/me/` | Authenticated | Current user's settings |
| `PATCH` | `/api/settings/me/` | Authenticated | Update current user's settings |

#### Fields

| Field | Type | Writable | Notes |
|---|---|---|---|
| `id` | int | No | |
| `notify_comments` | bool | Yes | |
| `notify_updates` | bool | Yes | |
| `notify_marketing` | bool | Yes | |
| `weight_reminder_days` | int | Yes | Days without a weight log before reminder (0 = disabled, default 5) |
| `subscription_plan` | int | No | FK |
| `subscription_plan_name` | string | No | |
| `subscription_status` | string | No | |
| `subscription_start_date` | datetime | No | |
| `subscription_end_date` | datetime | No | |
| `trial_end_date` | datetime | No | |
| `is_subscription_active` | bool | No | Computed |
| `is_trial_active` | bool | No | Computed |
| `api_key_prefix` | string | No | |
| `api_key_created_at` | datetime | No | |
| `created_at` | datetime | No | |
| `updated_at` | datetime | No | |

---

### Stripe Customers

Read-only, admin only.

| Method | URL | Permission | Description |
|---|---|---|---|
| `GET` | `/api/stripe-customers/` | Admin | List all Stripe customers |
| `GET` | `/api/stripe-customers/{id}/` | Admin | Retrieve |

#### Fields

| Field | Type | Notes |
|---|---|---|
| `id` | int | |
| `user_email` | string | |
| `stripe_customer_id` | string | |
| `stripe_subscription_id` | string | |
| `subscription_status` | string | |
| `created_at` | datetime | |
| `updated_at` | datetime | |

---

### Weights

Full CRUD. `user` is auto-set to the authenticated user on create.

| Method | URL | Permission | Description |
|---|---|---|---|
| `GET` | `/api/weights/` | Authenticated | List weight entries |
| `GET` | `/api/weights/{id}/` | Authenticated | Retrieve |
| `POST` | `/api/weights/` | Authenticated | Create |
| `PUT` | `/api/weights/{id}/` | Authenticated | Full update |
| `PATCH` | `/api/weights/{id}/` | Authenticated | Partial update |
| `DELETE` | `/api/weights/{id}/` | Authenticated | Delete |
| `GET` | `/api/weights/reminder/` | Authenticated | Check if current user's weight log is overdue |

#### Fields

| Field | Type | Writable | Notes |
|---|---|---|---|
| `id` | int | No | |
| `user` | int | No | Auto-set |
| `user_email` | string | No | |
| `datetime` | datetime | Yes | ISO 8601 |
| `value` | decimal | Yes | Weight in lbs |
| `source` | string | Yes | `manual` (default), `api`, `import`, `device` |
| `metadata` | object | Yes | Arbitrary JSON |

#### GET `/api/weights/reminder/`

Returns the current user's weight reminder status. The threshold is configured per-user
via `weight_reminder_days` in User Settings (default: 5, set to 0 to disable).

**Response when overdue:**

```json
{
  "overdue": true,
  "threshold_days": 5,
  "last_logged": "2026-05-06T08:00:00Z",
  "days_since": 7
}
```

**Response when up to date (or reminders disabled):**

```json
{
  "overdue": false
}
```

#### Example: create a weight entry

```bash
curl -X POST /api/weights/ \
  -H "Authorization: Token <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "datetime": "2026-05-12T08:00:00Z",
    "value": "175.50",
    "source": "manual"
  }'
```

---

### Meal Plans

Full CRUD with nested meal entries. `user` is auto-set on create.

| Method | URL | Permission | Description |
|---|---|---|---|
| `GET` | `/api/meal-plans/` | Authenticated | List plans |
| `GET` | `/api/meal-plans/?user={id}` | Admin | Filter by user ID |
| `GET` | `/api/meal-plans/{id}/` | Authenticated | Retrieve (includes nested entries) |
| `POST` | `/api/meal-plans/` | Authenticated | Create |
| `PUT` | `/api/meal-plans/{id}/` | Authenticated | Full update |
| `PATCH` | `/api/meal-plans/{id}/` | Authenticated | Partial update |
| `DELETE` | `/api/meal-plans/{id}/` | Authenticated | Delete |
| `GET` | `/api/meal-plans/by-user/{user_id}/` | Admin | All plans for a specific user |
| `POST` | `/api/meal-plans/by-user/{user_id}/compare-meals/` | Authenticated | LLM compare without a plan id: picks a plan (overlapping today, preferring most `MealEntry` rows; if in-window plans are empty shells, falls back to latest plan with entries), then compares to `UserMeal` in **that** plan’s date window. Staff: any `user_id`; others: own only. Empty body. |
| `POST` | `/api/meal-plans/{id}/compare-meals/` | Authenticated | Same LLM comparison for a **specific** meal plan id (Ollama; plan owner’s host/model). Empty body. |

#### Fields

| Field | Type | Writable | Notes |
|---|---|---|---|
| `id` | int | No | |
| `user` | int | No | Auto-set |
| `user_email` | string | No | |
| `title` | string | Yes | |
| `start_date` | date | Yes | YYYY-MM-DD |
| `end_date` | date | Yes | YYYY-MM-DD |
| `daily_calorie_target` | int | Yes | Nullable |
| `daily_protein_target` | decimal | Yes | Grams, nullable |
| `daily_carbs_target` | decimal | Yes | Grams, nullable |
| `daily_fat_target` | decimal | Yes | Grams, nullable |
| `daily_water_target_ml` | int | Yes | Millilitres, nullable |
| `dietary_preference` | string | Yes | See choices below |
| `dietary_preference_display` | string | No | Human-readable label |
| `allergies_restrictions` | array | Yes | List of strings |
| `supplements` | array | Yes | List of strings |
| `goal` | string | Yes | |
| `notes` | string | Yes | |
| `entries` | array | No | Nested `MealEntry` objects |
| `entry_count` | int | No | Computed |
| `total_calories` | int | No | Sum of all entries |
| `adherence_rate` | int | No | % of entries linked to actual meals |
| `created_at` | datetime | No | |
| `updated_at` | datetime | No | |

**`dietary_preference` choices:** `none`, `vegetarian`, `vegan`, `keto`, `high_protein`, `paleo`, `mediterranean`

#### Nested entry fields (read-only in meal plan response)

| Field | Type | Notes |
|---|---|---|
| `id` | int | |
| `meal_plan` | int | FK |
| `meal_type` | string | See choices below |
| `meal_type_display` | string | Human-readable |
| `day_number` | int | Day of the plan (1, 2, 3...) |
| `scheduled_time` | time | HH:MM:SS, nullable |
| `title` | string | |
| `foods_json` | array | List of food items |
| `calories` | int | |
| `protein` | decimal | Grams |
| `carbs` | decimal | Grams |
| `fat` | decimal | Grams |
| `portion_notes` | string | |
| `substitutions` | array | |
| `sort_order` | int | |
| `actual_meal` | int | FK to UserMeal, nullable |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**`meal_type` choices:** `breakfast`, `mid_morning_snack`, `lunch`, `evening_snack`, `dinner`, `post_workout`, `bedtime_snack`

#### Example: get all meal plans for user 1 (admin)

```bash
curl /api/meal-plans/by-user/1/ \
  -H "Authorization: Token <admin-key>"
```

#### Example: create a meal plan

```bash
curl -X POST /api/meal-plans/ \
  -H "Authorization: Token <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "May Week 1 — Cutting",
    "start_date": "2026-05-01",
    "end_date": "2026-05-07",
    "daily_calorie_target": 1800,
    "daily_protein_target": "150.00",
    "dietary_preference": "high_protein",
    "goal": "Lose 2 lbs"
  }'
```

#### Example: compare by user id (recommended)

```bash
curl -X POST /api/meal-plans/by-user/3/compare-meals/ \
  -H "Authorization: Token <key>"
```

Response matches the plan-scoped endpoint, plus `user_id`, `meal_plan_title`, and `meal_plan_selection` (`active_window`, `fallback_latest_with_entries`, or `latest_by_start_date`).

#### Example: compare a specific meal plan by id

```bash
curl -X POST /api/meal-plans/42/compare-meals/ \
  -H "Authorization: Token <key>"
```

Response includes `analysis` (plain text from the model) plus `planned_entry_count`, `actual_meal_count`, `actual_total_calories_logged`, `planned_sum_calories_from_entries`, and `date_range`.

---

### User Meals

Actual meals consumed by users. Full CRUD. `user` is auto-set on create.

| Method | URL | Permission | Description |
|---|---|---|---|
| `GET` | `/api/user-meals/` | Authenticated | List meals |
| `GET` | `/api/user-meals/{id}/` | Authenticated | Retrieve |
| `POST` | `/api/user-meals/` | Authenticated | Create |
| `PUT` | `/api/user-meals/{id}/` | Authenticated | Full update |
| `PATCH` | `/api/user-meals/{id}/` | Authenticated | Partial update |
| `DELETE` | `/api/user-meals/{id}/` | Authenticated | Delete |

#### Fields

| Field | Type | Writable | Notes |
|---|---|---|---|
| `id` | int | No | |
| `user` | int | No | Auto-set |
| `user_email` | string | No | |
| `meal_type` | string | Yes | Same choices as MealEntry |
| `meal_type_display` | string | No | Human-readable |
| `title` | string | Yes | |
| `time_taken` | datetime | Yes | ISO 8601 |
| `description` | string | Yes | |
| `calories` | int | Yes | |
| `metadata` | object | Yes | Arbitrary JSON |
| `created_at` | datetime | No | |
| `updated_at` | datetime | No | |

#### Example: log a meal

```bash
curl -X POST /api/user-meals/ \
  -H "Authorization: Token <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_type": "lunch",
    "title": "Grilled chicken salad",
    "time_taken": "2026-05-12T12:30:00Z",
    "calories": 450,
    "description": "Mixed greens, grilled chicken breast, olive oil dressing"
  }'
```

---

### Interventions

Health interventions / recommendations. Full CRUD. `user` is auto-set on create.

| Method | URL | Permission | Description |
|---|---|---|---|
| `GET` | `/api/interventions/` | Authenticated | List interventions |
| `GET` | `/api/interventions/{id}/` | Authenticated | Retrieve |
| `POST` | `/api/interventions/` | Authenticated | Create |
| `PUT` | `/api/interventions/{id}/` | Authenticated | Full update |
| `PATCH` | `/api/interventions/{id}/` | Authenticated | Partial update |
| `DELETE` | `/api/interventions/{id}/` | Authenticated | Delete |

#### Fields

| Field | Type | Writable | Notes |
|---|---|---|---|
| `id` | int | No | |
| `user` | int | No | Auto-set |
| `user_email` | string | No | |
| `type` | string | Yes | See choices below |
| `type_display` | string | No | Human-readable |
| `status` | string | Yes | See choices below |
| `status_display` | string | No | Human-readable |
| `priority` | string | Yes | See choices below |
| `priority_display` | string | No | Human-readable |
| `title` | string | Yes | |
| `description` | string | Yes | |
| `trigger_source` | string | Yes | What triggered the intervention |
| `target_metric` | string | Yes | e.g. `weight`, `calories` |
| `target_value` | decimal | Yes | Nullable |
| `current_value` | decimal | Yes | Nullable |
| `action_json` | object | Yes | Structured action data |
| `scheduled_at` | datetime | Yes | Nullable |
| `completed_at` | datetime | Yes | Nullable |
| `created_by` | string | Yes | e.g. `system`, `ai`, `admin` |
| `created_at` | datetime | No | |
| `updated_at` | datetime | No | |

**`type` choices:** `dietary`, `exercise`, `behavioral`, `medical`, `supplement`, `other`

**`status` choices:** `pending`, `active`, `completed`, `cancelled`, `skipped`

**`priority` choices:** `low`, `normal`, `high`, `urgent`

---

## Error Responses

All errors follow a consistent format:

| Status | Meaning |
|---|---|
| `400` | Validation error — response body contains field-level errors |
| `401` | Not authenticated |
| `403` | Authenticated but insufficient permissions |
| `404` | Resource not found (or not owned by current user) |
| `405` | HTTP method not allowed |

#### Validation error example

```json
{
  "title": ["This field is required."],
  "start_date": ["Date has wrong format. Use YYYY-MM-DD."]
}
```

---

## API Root

`GET /api/` returns a browsable directory of all registered endpoints:

```json
{
  "users": "http://localhost:8000/api/users/",
  "plans": "http://localhost:8000/api/plans/",
  "settings": "http://localhost:8000/api/settings/",
  "stripe-customers": "http://localhost:8000/api/stripe-customers/",
  "weights": "http://localhost:8000/api/weights/",
  "meal-plans": "http://localhost:8000/api/meal-plans/",
  "user-meals": "http://localhost:8000/api/user-meals/",
  "interventions": "http://localhost:8000/api/interventions/"
}
```
