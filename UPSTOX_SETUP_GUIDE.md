# Upstox App Setup Guide for STRATOS

## Step 1: Create Upstox App

Follow these steps on https://upstox.com/apps/my-apps:

### App Details

1. **App Name**: `Stratos`
   - Already filled: "Stratos"

2. **Redirect URL** (Required)
   ```
   https://localhost:3000/auth/upstox/callback
   ```
   OR if deployed:
   ```
   https://your-domain.com/auth/upstox/callback
   ```

3. **Primary IP** (Optional but Recommended)
   - Your development machine or server IP
   - Example: `192.168.1.100` or `203.0.113.45`
   - Required for live trading

4. **Secondary IP** (Optional)
   - Backup IP for redundancy
   - Can be left empty initially

5. **Postback URL** (Optional - for Webhooks)
   ```
   https://your-domain.com/webhooks/upstox/orders
   ```

6. **Notifier Webhook Endpoint** (Optional)
   ```
   https://your-domain.com/webhooks/upstox/notify
   ```

7. **Description** (Optional)
   ```
   STRATOS Financial Intelligence OS - Trading and Portfolio Management
   ```

8. **Accept Terms** ✓

### Click "Continue"

You'll receive:
- **API Key** (save this!)
- **API Secret** (save this!)

---

## Step 2: Generate OAuth Access Token

After app creation, you'll see an option to generate tokens.

### In "My Apps" Dashboard:

1. Click on your "Stratos" app
2. Click **"Generate Token"** button
3. You'll be redirected to Upstox login
4. Login with your trading account credentials
5. Grant permissions
6. You'll receive an **Access Token**

**Token Format**: `eyJ...` (long JWT string)

---

## Step 3: Configure STRATOS

### Create `.env` file in project root:

```bash
# Upstox Configuration
UPSTOX_API_KEY="your_api_key_here"
UPSTOX_API_SECRET="your_api_secret_here"
UPSTOX_ACCESS_TOKEN="your_access_token_here"

# Backend Configuration
UPSTOX_SANDBOX_MODE=true  # Set to false for live trading
UPSTOX_WEBHOOK_SECRET="random_secret_key"

# Frontend Configuration
NEXT_PUBLIC_UPSTOX_REDIRECT_URL="https://localhost:3000/auth/upstox/callback"
NEXT_PUBLIC_UPSTOX_API_KEY="your_api_key_here"
```

### Never commit `.env` to Git!

Add to `.gitignore`:
```
.env
.env.local
.env.*.local
```

---

## Step 4: Initialize STRATOS with Upstox

### Backend Setup (Python/FastAPI)

```python
# orchestrator/src/stratos_orchestrator/config.py

import os

class UpstoxConfig:
    API_KEY = os.getenv("UPSTOX_API_KEY")
    API_SECRET = os.getenv("UPSTOX_API_SECRET")
    ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
    SANDBOX_MODE = os.getenv("UPSTOX_SANDBOX_MODE", "true").lower() == "true"
    WEBHOOK_SECRET = os.getenv("UPSTOX_WEBHOOK_SECRET")
    REDIRECT_URL = os.getenv("UPSTOX_REDIRECT_URL")
```

### Initialize in Orchestrator

```python
# orchestrator/src/stratos_orchestrator/adapters/tools/upstox_init.py

from stratos_orchestrator.adapters.tools.upstox import create_upstox_integration
from stratos_orchestrator.config import UpstoxConfig

async def init_upstox():
    """Initialize Upstox integration"""
    integration = await create_upstox_integration(
        access_token=UpstoxConfig.ACCESS_TOKEN,
        api_key=UpstoxConfig.API_KEY,
        sandbox_mode=UpstoxConfig.SANDBOX_MODE
    )
    
    if await integration.initialize():
        print("✅ Upstox connected!")
        return integration
    else:
        print("❌ Upstox connection failed")
        return None
```

### Register with Finance Council

```python
# orchestrator/src/stratos_orchestrator/application/finance_council.py

async def setup_with_upstox(self, upstox_integration):
    """Add Upstox tools to Finance Council"""
    await upstox_integration.register_with_agents(self.agent_registry)
    
    # Now agents can use:
    # - upstox_portfolio
    # - upstox_market_data
    # - upstox_orders
    # - upstox_risk
```

### Frontend Setup (Next.js)

```typescript
// frontend/src/lib/upstox-client.ts

export class UpstoxClient {
  private apiKey: string;
  private redirectUrl: string;
  
  constructor() {
    this.apiKey = process.env.NEXT_PUBLIC_UPSTOX_API_KEY!;
    this.redirectUrl = process.env.NEXT_PUBLIC_UPSTOX_REDIRECT_URL!;
  }
  
  getAuthUrl(): string {
    return `https://api.upstox.com/index/dialog/authorize?apikey=${this.apiKey}&redirect_uri=${encodeURIComponent(this.redirectUrl)}`;
  }
}
```

---

## Step 5: Test Connection

### Test Script

```python
# test_upstox_connection.py

import asyncio
from stratos_orchestrator.adapters.tools.upstox import create_upstox_integration

async def test():
    integration = await create_upstox_integration(
        access_token="your_token_here",
        sandbox_mode=True
    )
    
    # Test portfolio
    portfolio = await integration.get_portfolio_summary()
    print("Portfolio:", portfolio)
    
    # Test quotes
    quotes = await integration.get_quotes(["NSE_EQ|INE002A01018"])
    print("Quotes:", quotes)
    
    integration.close()

if __name__ == "__main__":
    asyncio.run(test())
```

Run:
```bash
python test_upstox_connection.py
```

---

## Step 6: IP Address Management

### Why IP addresses matter:

- Upstox validates requests from registered IPs
- **Development**: Your local machine IP
- **Production**: Your server's IP
- Cannot be changed more than once per week

### Find Your IP:

```bash
# macOS/Linux
ifconfig | grep "inet "

# Windows
ipconfig | findstr "IPv4"

# Get public IP
curl ifconfig.me
```

### Update IP (if needed):

1. Go to Upstox Apps dashboard
2. Click your app
3. Update Primary IP
4. Wait 24 hours for changes to take effect

---

## Step 7: Webhook Setup (Optional)

### Receive Order Updates in Real-time

```python
# orchestrator/src/stratos_orchestrator/api/webhooks.py

from fastapi import APIRouter, Request
from stratos_orchestrator.config import UpstoxConfig
import hmac
import hashlib

router = APIRouter(prefix="/webhooks/upstox", tags=["upstox"])

@router.post("/orders")
async def order_webhook(request: Request):
    """Receive order updates from Upstox"""
    body = await request.json()
    
    # Verify webhook signature
    signature = request.headers.get("X-Webhook-Signature")
    expected = hmac.new(
        UpstoxConfig.WEBHOOK_SECRET.encode(),
        str(body).encode(),
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected:
        return {"status": "unauthorized"}
    
    # Process order update
    order_id = body.get("order_id")
    status = body.get("status")
    
    # Update Finance Council
    await finance_council.process_order_update(order_id, status)
    
    return {"status": "received"}
```

---

## Troubleshooting

### Issue: "Invalid API Key"
- ✓ Copy exact API key from dashboard
- ✓ Check for extra spaces
- ✓ Verify not expired

### Issue: "Redirect URL mismatch"
- ✓ Match exact URL with app settings
- ✓ Include protocol (https://)
- ✓ No trailing slashes

### Issue: "IP not registered"
- ✓ Add your IP to app settings
- ✓ Wait 24 hours for activation
- ✓ Use secondary IP as backup

### Issue: "Token expired"
- ✓ Generate new token from dashboard
- ✓ Token valid for 24 hours default
- ✓ Update UPSTOX_ACCESS_TOKEN

### Issue: "Rate limit exceeded"
- ✓ Upstox: 100 requests/minute
- ✓ Implement exponential backoff
- ✓ Cache responses when possible

---

## Security Best Practices

### ✅ DO:
- ✓ Store tokens in `.env` files (not in git)
- ✓ Use different tokens for dev/prod
- ✓ Rotate tokens regularly
- ✓ Enable IP whitelisting
- ✓ Use HTTPS for all redirects
- ✓ Validate webhook signatures
- ✓ Log access attempts

### ❌ DON'T:
- ✗ Commit `.env` to git
- ✗ Share API keys in Slack/Email
- ✗ Use same token for multiple apps
- ✗ Hardcode credentials
- ✗ Log sensitive data
- ✗ Expose keys in client-side code

---

## Features Available After Setup

### Agents Can Now:

```python
# Portfolio Analysis
portfolio = await integration.get_portfolio_summary()
allocation = await integration.get_portfolio_allocation()
concentration = await integration.get_portfolio_concentration()

# Market Data
quotes = await integration.get_quotes(["NSE_EQ|INE002A01018"])
technical = await integration.get_technical_analysis("NSE_EQ|INE002A01018")
options = await integration.get_option_chain("NSE_INDEX|Nifty 50")

# Order Execution
order = await integration.place_order(
    instrument_key="NSE_EQ|INE002A01018",
    quantity=1,
    side="BUY",
    order_type="LIMIT",
    price=2500.0
)

# Risk Analysis
metrics = await integration.get_portfolio_metrics()
exposures = await integration.identify_risk_exposures()
```

---

## Next Steps

1. ✅ Create Upstox app
2. ✅ Generate API credentials
3. ✅ Configure STRATOS (.env file)
4. ✅ Test connection
5. ✅ Register with Finance Council agents
6. ✅ Deploy to production

---

## Support

- **Upstox API Docs**: https://upstox.com/api
- **STRATOS Issues**: https://github.com/theory903/Stratos/issues
- **Upstox Support**: https://upstox.com/support

---

**Ready? Let's trade! 🚀**
