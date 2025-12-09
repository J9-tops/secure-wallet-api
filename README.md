# Wallet Service with Paystack, JWT & API Keys

A production-ready backend wallet service built with FastAPI, PostgreSQL, and Paystack integration.

## Features

✅ **Google OAuth Authentication** - JWT-based user authentication  
✅ **Paystack Integration** - Secure payment processing with webhook verification  
✅ **API Key Management** - Service-to-service authentication with permissions  
✅ **Wallet Operations** - Deposits, transfers, balance checks  
✅ **Transaction History** - Complete audit trail  
✅ **Security Features** - Signature verification, permission-based access  
✅ **Idempotent Operations** - Safe webhook processing  

## Project Structure

```
src/
├── db/
│   ├── __init__.py
│   └── session.py          # Database configuration
├── models/
│   ├── __init__.py
│   ├── user.py             # User model
│   ├── wallet.py           # Wallet model
│   ├── transaction.py      # Transaction model
│   └── api_key.py          # API Key model
├── routes/
│   ├── __init__.py
│   ├── auth.py             # Authentication routes
│   ├── api_keys.py         # API key management
│   └── wallet.py           # Wallet operations
├── schemas/
│   ├── __init__.py
│   └── wallet.py           # Pydantic schemas
├── services/
│   ├── __init__.py
│   ├── paystack.py         # Paystack service
│   └── wallet_service.py   # Wallet business logic
├── utils/
│   ├── __init__.py
│   ├── security.py         # Security utilities
│   └── auth.py             # Auth dependencies
├── __init__.py
└── main.py                 # Application entry point
```

## Installation

### 1. Clone and Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
```

### 3. Setup PostgreSQL

```bash
# Create database
createdb wallet_service

# Or using psql
psql -U postgres
CREATE DATABASE wallet_service;
```

### 4. Setup Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:8000/auth/google/callback`
6. Copy Client ID and Secret to `.env`

### 5. Setup Paystack

1. Sign up at [Paystack](https://paystack.com/)
2. Get your test secret key from Settings
3. Add to `.env`
4. Configure webhook URL: `https://yourdomain.com/wallet/paystack/webhook`

### 6. Run Application

```bash
# Initialize database (first time only)
python -c "from src.db.session import init_db; import asyncio; asyncio.run(init_db())"

# Start server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, access interactive docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/google` | Initiate Google sign-in |
| GET | `/auth/google/callback` | OAuth callback (returns JWT) |

### API Key Management

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/keys/create` | Create API key | JWT |
| POST | `/keys/rollover` | Rollover expired key | JWT |

### Wallet Operations

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/wallet/deposit` | Initiate deposit | JWT or API Key (deposit) |
| POST | `/wallet/paystack/webhook` | Paystack webhook | Paystack signature |
| GET | `/wallet/deposit/{ref}/status` | Check deposit status | JWT or API Key (read) |
| GET | `/wallet/balance` | Get balance | JWT or API Key (read) |
| POST | `/wallet/transfer` | Transfer funds | JWT or API Key (transfer) |
| GET | `/wallet/transactions` | Transaction history | JWT or API Key (read) |

## Usage Examples

### 1. Authentication with Google

```bash
# Step 1: Open in browser
http://localhost:8000/auth/google

# Step 2: After OAuth, you'll receive:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 2. Create API Key

```bash
curl -X POST http://localhost:8000/keys/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "payment-service",
    "permissions": ["deposit", "transfer", "read"],
    "expiry": "1M"
  }'

# Response:
{
  "api_key": "sk_live_xxxxx",
  "expires_at": "2025-01-08T12:00:00Z"
}
```

### 3. Deposit Money (JWT)

```bash
curl -X POST http://localhost:8000/wallet/deposit \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5000
  }'

# Response:
{
  "reference": "TXN_20241208120000_a1b2c3d4",
  "authorization_url": "https://checkout.paystack.com/..."
}
```

### 4. Deposit Money (API Key)

```bash
curl -X POST http://localhost:8000/wallet/deposit \
  -H "x-api-key: sk_live_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5000
  }'
```

### 5. Check Balance

```bash
# Using JWT
curl -X GET http://localhost:8000/wallet/balance \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Using API Key
curl -X GET http://localhost:8000/wallet/balance \
  -H "x-api-key: sk_live_xxxxx"

# Response:
{
  "balance": 15000.00
}
```

### 6. Transfer Funds

```bash
curl -X POST http://localhost:8000/wallet/transfer \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_number": "1234567890123",
    "amount": 3000
  }'

# Response:
{
  "status": "success",
  "message": "Transfer completed"
}
```

### 7. Get Transaction History

```bash
curl -X GET http://localhost:8000/wallet/transactions \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
[
  {
    "type": "deposit",
    "amount": 5000.00,
    "status": "success",
    "reference": "TXN_20241208120000_a1b2c3d4",
    "created_at": "2024-12-08T12:00:00Z"
  },
  {
    "type": "transfer",
    "amount": 3000.00,
    "status": "success",
    "recipient_wallet_number": "1234567890123",
    "created_at": "2024-12-08T13:00:00Z"
  }
]
```

## Security Features

### JWT Authentication
- Tokens expire after 24 hours
- HS256 algorithm
- Includes user_id and email claims

### API Key Security
- SHA-256 hashed storage
- Permission-based access control
- Maximum 5 active keys per user
- Automatic expiration
- Revocation support

### Paystack Webhook Verification
- HMAC SHA-512 signature verification
- Idempotent processing (no double-credit)
- Amount validation

### Transfer Security
- Balance verification
- Atomic transactions
- Self-transfer prevention
- Unique transaction references

## Database Schema

### Users Table
- id (UUID, PK)
- email (unique)
- google_id (unique)
- name, picture
- is_active
- timestamps

### Wallets Table
- id (UUID, PK)
- user_id (FK, unique)
- wallet_number (13 digits, unique)
- balance (Decimal)
- timestamps

### Transactions Table
- id (UUID, PK)
- user_id (FK)
- reference (unique)
- type (deposit/transfer)
- amount (Decimal)
- status (pending/success/failed)
- recipient details
- Paystack details
- timestamps

### API Keys Table
- id (UUID, PK)
- user_id (FK)
- name
- key_hash (unique)
- permissions (array)
- is_active, is_revoked
- expires_at
- timestamps

## Testing Paystack Webhooks Locally

Use ngrok to expose your local server:

```bash
# Install ngrok
npm install -g ngrok

# Start ngrok
ngrok http 8000

# Configure webhook in Paystack dashboard
https://your-ngrok-url.ngrok.io/wallet/paystack/webhook
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Invalid/expired auth
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Production Deployment

### Environment Variables
- Set strong `JWT_SECRET`
- Use production Paystack keys
- Configure proper `DATABASE_URL`
- Set `DEBUG=False`

### Database
- Use connection pooling
- Enable SSL for PostgreSQL
- Regular backups

### Security
- Use HTTPS only
- Configure CORS properly
- Rate limiting
- Monitor webhook attempts

### Monitoring
- Log all transactions
- Alert on failed webhooks
- Track API key usage

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql -U postgres -d wallet_service
```

### OAuth Redirect Issues
- Ensure redirect URI matches exactly in Google Console
- Check `GOOGLE_REDIRECT_URI` in `.env`

### Webhook Not Receiving Events
- Verify webhook URL is publicly accessible
- Check Paystack dashboard for delivery logs
- Verify signature validation

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.