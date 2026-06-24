# SQLite + Stripe Backend Patterns

Reusable Go patterns for micro-SaaS backends: SQLite with `modernc.org/sqlite` (pure Go, no CGo) and Stripe subscription flow.

## SQLite: modernc.org/sqlite

Use `modernc.org/sqlite` instead of `mattn/go-sqlite3` — it's pure Go, no CGo, compiles everywhere including Alpine Docker containers without build tools.

### Connection

```go
import (
    "database/sql"
    _ "modernc.org/sqlite"
)

func New(path string) (*sql.DB, error) {
    dsn := fmt.Sprintf("%s?_journal_mode=WAL&_busy_timeout=5000&_foreign_keys=on", path)
    db, err := sql.Open("sqlite", dsn)
    if err != nil {
        return nil, err
    }
    db.SetMaxOpenConns(1)  // SQLite is single-writer
    db.SetMaxIdleConns(1)
    return db, nil
}
```

Key pragmas in DSN:
- `_journal_mode=WAL` — better concurrency for reads
- `_busy_timeout=5000` — wait 5s on lock contention instead of failing
- `_foreign_keys=on` — enforce FK constraints (off by default in SQLite)

### Migrations

Run on startup, idempotent:

```go
func migrate(db *sql.DB) error {
    queries := []string{
        `CREATE TABLE IF NOT EXISTS shares (...);`,
        `CREATE INDEX IF NOT EXISTS idx_... ON shares(...);`,
        `CREATE TABLE IF NOT EXISTS users (...);`,
    }
    for _, q := range queries {
        if _, err := db.Exec(q); err != nil {
            return fmt.Errorf("migrate: %w\n%s", err, q)
        }
    }
    return nil
}
```

No migration framework needed for simple schemas. `IF NOT EXISTS` makes it idempotent.

### Docker persistence

Mount a volume for the SQLite file:

```yaml
services:
  app:
    volumes:
      - app_data:/data
    environment:
      - DB_PATH=/data/app.db
```

SQLite file is self-contained — backup is `cp /data/app.db /backup/`.

## Stripe Subscriptions

### Go dependency

```
require github.com/stripe/stripe-go/v81 v81.0.0
```

### Checkout Session (create)

```go
import (
    "github.com/stripe/stripe-go/v81"
    "github.com/stripe/stripe-go/v81/checkout/session"
)

func createCheckout(w http.ResponseWriter, r *http.Request) {
    stripe.Key = os.Getenv("STRIPE_SECRET_KEY")
    
    params := &stripe.CheckoutSessionParams{
        Mode: stripe.String(string(stripe.CheckoutSessionModeSubscription)),
        LineItems: []*stripe.CheckoutSessionLineItemParams{
            {
                Price:    stripe.String(os.Getenv("STRIPE_PRO_PRICE_ID")),
                Quantity: stripe.Int64(1),
            },
        },
        SuccessURL: stripe.String(os.Getenv("BASE_URL") + "/pro?success=true"),
        CancelURL:  stripe.String(os.Getenv("BASE_URL") + "/pro?canceled=true"),
    }
    
    s, err := session.New(params)
    // Return s.URL to redirect user
}
```

### Webhook Handler

```go
import (
    "github.com/stripe/stripe-go/v81/webhook"
)

func handleWebhook(w http.ResponseWriter, r *http.Request) {
    body, _ := io.ReadAll(r.Body) // max ~64KB
    event, err := webhook.ConstructEvent(body, r.Header.Get("Stripe-Signature"), webhookSecret)
    if err != nil {
        http.Error(w, "invalid signature", 400)
        return
    }
    
    switch event.Type {
    case "checkout.session.completed":
        // Unmarshal event.Data.Raw into stripe.CheckoutSession
        // Create user + generate API key + set pro_until
    case "customer.subscription.deleted":
        // Revoke pro access
    case "customer.subscription.updated":
        // Extend pro_until to match subscription period end
    }
    
    w.WriteHeader(200)
}
```

### API Key Generation

```go
import "crypto/rand"

func generateKey(prefix string) string {
    b := make([]byte, 16) // 32 hex chars
    rand.Read(b)
    return prefix + hex.EncodeToString(b)
}
// Usage: generateKey("fmt_") → "fmt_a1b2c3d4e5f6..."
```

### User Lifecycle

1. User clicks "Pro — $3/mo" → `POST /api/stripe/checkout` → redirect to Stripe
2. Stripe handles payment → sends `checkout.session.completed` webhook
3. Webhook handler: create user row with `stripe_customer_id`, generate `api_key`, set `pro_until` to now+1 month
4. User sees success page, API key displayed there
5. On subscription cancel: webhook sets `pro_until` to now (or subscription end)
6. On renewal: webhook extends `pro_until`

### Environment Variables

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
BASE_URL=https://fmtthis.dev
```

Create the Stripe product with recurring price first in Stripe Dashboard (Products → Add Product → Recurring → $3/mo), then copy the price ID.

### Dev API Key (Testing Without Stripe)

When Stripe keys are unset, the checkout/webhook endpoints return 503 — everything else works. But the Pro API endpoint requires a valid API key, which is normally created by the Stripe webhook. For local testing, add a dev override:

**In auth package (`auth/auth.go`):**
```go
func IsDevKey(apiKey string) bool {
    devKey := os.Getenv("FMTTHIS_DEV_API_KEY")
    return devKey != "" && apiKey == devKey
}
```

**In the format handler — check both real Pro users AND the dev key:**
```go
if !auth.IsPro(user) && !auth.IsDevKey(apiKey) {
    http.Error(w, `{"error":"valid Pro subscription required"}`, 403)
    return
}
```

**In docker-compose.yml — use bare reference so it pulls from `.env`:**
```yaml
environment:
  - FMTTHIS_DEV_API_KEY
```

Then create a `.env` file (gitignored) with `FMTTHIS_DEV_API_KEY=***` and test:
```bash
curl -H 'Authorization: Bearer *** \
  -d '{"input":"{}","format":"json"}' \
  localhost:8080/api/format
```

In production, leave `FMTTHIS_DEV_API_KEY` unset — `IsDevKey` returns false and only real Stripe-backed Pro users can access the endpoint. This pattern avoids the chicken-and-egg problem of needing a Stripe subscription just to test API auth during development.
