# Complete API Setup Guide for STRATOS V1 MVP

## Overview

STRATOS uses multiple APIs across 6 layers. This guide covers all APIs needed for production-grade financial intelligence.

---

## 1. TRADING & MARKET DATA APIs

### 1.1 Upstox (Primary Trading Platform)

**Status**: ✅ Already Integrated

**What it provides**:
- Real-time market data
- Portfolio management
- Order execution
- Account information

**Setup** (Already done - see UPSTOX_SETUP_GUIDE.md):
```bash
UPSTOX_ACCESS_TOKEN=your_token
UPSTOX_SANDBOX_MODE=true
```

**Endpoints Used**:
- Instruments (NSE, BSE, MCX)
- Market quotes (real-time)
- Historical data (OHLC)
- Portfolio/Holdings
- Orders
- Margins/Funds

---

### 1.2 Polygon.io (Stock Data & Real-time Quotes)

**Why**: High-quality US stock data, crypto, forex
**Cost**: Free tier available, $199/month for premium
**API Key**: https://polygon.io/

**Setup**:

```bash
# 1. Get API key from https://polygon.io/
# 2. Add to .env
POLYGON_API_KEY=pk_live_...

# 3. Install client
pip install polygon-api-client
```

**Configuration** (data-fabric/src/data_fabric/adapters/providers/):

Create `polygon_provider.py`:

```python
from polygon import RESTClient

class PolygonProvider:
    def __init__(self, api_key: str):
        self.client = RESTClient(api_key)
    
    async def get_stock_quotes(self, ticker: str):
        """Get real-time stock quotes"""
        quotes = self.client.get_last_quote(ticker)
        return {
            "ticker": ticker,
            "bid": quotes.bid,
            "ask": quotes.ask,
            "last_updated": quotes.last_updated
        }
    
    async def get_crypto_quotes(self, crypto: str):
        """Get crypto quotes"""
        quote = self.client.crypto_quotes_latest(crypto)
        return quote
    
    async def get_forex_quotes(self, pair: str):
        """Get forex quotes"""
        quote = self.client.forex_quotes_latest(pair)
        return quote
```

**What it provides**:
- US stock quotes
- Crypto data
- Forex quotes
- Historical aggregates
- Technical indicators

---

### 1.3 Alpha Vantage (Already Integrated)

**What it provides**:
- Stock time series data
- Technical indicators
- Forex data
- Crypto data

**Setup**:

```bash
# Get free API key from https://www.alphavantage.co/
ALPHA_VANTAGE_API_KEY=demo

# For production, upgrade to paid ($9/month)
```

**Already used in**:
- `orchestrator/src/stratos_orchestrator/adapters/tools/alpha_vantage_tool.py`

---

### 1.4 Finnhub (Company Data & News) - Already Integrated

**What it provides**:
- Company fundamentals
- News sentiment
- Earnings data
- Company profiles

**Setup**:

```bash
# Get API key from https://finnhub.io/
FINNHUB_API_KEY=your_key

# Free tier: 60 API calls/minute
# Paid: $99/month
```

**Already used in**:
- `orchestrator/src/stratos_orchestrator/adapters/tools/finnhub_tool.py`

---

### 1.5 CoinGecko (Crypto Data) - Already Integrated

**What it provides**:
- Crypto prices (free!)
- Market cap
- Volume
- Change metrics

**Setup**:

```bash
# NO API KEY REQUIRED for basic tier
# Free public API: https://api.coingecko.com/api/v3/

# Optional: Pro API ($50/month)
COINGECKO_PRO_KEY=your_key
```

**Already used in**:
- `orchestrator/src/stratos_orchestrator/adapters/tools/coingecko_tool.py`

---

## 2. NEWS & SENTIMENT APIs

### 2.1 NewsAPI (News Aggregation) - Already Integrated

**What it provides**:
- News headlines
- Company news
- Market news
- Sentiment indicators

**Setup**:

```bash
# Get API key from https://newsapi.org/
NEWS_API_KEY=your_key

# Free tier: 100 requests/day
# Paid: $45/month for 50k requests/month
```

**Already used in**:
- `orchestrator/src/stratos_orchestrator/adapters/tools/company_news_tool.py`

---

### 2.2 Sentiment140 (Twitter Sentiment Analysis)

**Why**: Real-time sentiment from Twitter/X
**Cost**: Free
**API**: https://www.sentiment140.com/

**Setup**:

Create `sentiment140_provider.py`:

```python
import aiohttp
from typing import Dict, Any

class Sentiment140Provider:
    """Twitter sentiment analysis"""
    
    BASE_URL = "http://sentiment140.appspot.com/api"
    
    async def get_sentiment(self, query: str, count: int = 100) -> Dict[str, Any]:
        """Get sentiment for a query/stock"""
        params = {
            'q': query,
            'count': count
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE_URL}/bulkClassifyTweet",
                params=params
            ) as resp:
                data = await resp.json()
                
                positive = sum(1 for t in data['tweets'] if t['polarity'] == 4)
                negative = sum(1 for t in data['tweets'] if t['polarity'] == 0)
                neutral = sum(1 for t in data['tweets'] if t['polarity'] == 2)
                
                return {
                    "query": query,
                    "positive": positive,
                    "negative": negative,
                    "neutral": neutral,
                    "sentiment_score": (positive - negative) / len(data['tweets'])
                }
```

**Integration** (Add to `nlp/src/stratos_nlp/adapters/`):

```python
# sentiment_provider.py
from sentiment140_provider import Sentiment140Provider

class SentimentAnalysisAdapter:
    def __init__(self):
        self.sentiment140 = Sentiment140Provider()
    
    async def analyze_stock_sentiment(self, symbol: str):
        """Analyze sentiment for a stock"""
        return await self.sentiment140.get_sentiment(symbol)
```

---

### 2.3 Alternative: Hugging Face (Free Sentiment Analysis)

**Why**: No API key needed, completely free
**Cost**: Free
**Model**: distilbert-base-multilingual-uncased-sentiment

**Setup**:

```bash
pip install transformers torch
```

Create `huggingface_sentiment.py`:

```python
from transformers import pipeline

class HuggingFaceSentiment:
    def __init__(self):
        self.sentiment_pipeline = pipeline("sentiment-analysis")
    
    async def analyze_text(self, text: str):
        """Analyze sentiment of text"""
        result = self.sentiment_pipeline(text)
        return {
            "text": text,
            "sentiment": result[0]['label'],
            "confidence": result[0]['score']
        }
    
    async def analyze_earnings_call(self, transcript: str):
        """Analyze earnings call sentiment"""
        # Split into chunks
        chunks = [transcript[i:i+512] for i in range(0, len(transcript), 512)]
        
        sentiments = []
        for chunk in chunks:
            result = await self.analyze_text(chunk)
            sentiments.append(result)
        
        # Calculate aggregate sentiment
        positive = sum(1 for s in sentiments if s['sentiment'] == 'POSITIVE')
        negative = sum(1 for s in sentiments if s['sentiment'] == 'NEGATIVE')
        
        return {
            "overall_sentiment": "POSITIVE" if positive > negative else "NEGATIVE",
            "positive_ratio": positive / len(sentiments),
            "analysis": sentiments
        }
```

---

## 3. ECONOMIC & MACRO DATA APIs

### 3.1 FRED (Federal Reserve Economic Data)

**Why**: US economic indicators (GDP, unemployment, inflation, etc.)
**Cost**: FREE
**API**: https://fred.stlouisfed.org/

**Setup**:

```bash
# Get API key from https://fred.stlouisfed.org/docs/api/fred/
FRED_API_KEY=your_key

# Install client
pip install fredapi
```

**Integration** (data-fabric/src/data_fabric/adapters/providers/):

Create `fred_provider.py`:

```python
import fred as fred_client
from datetime import datetime, timedelta

class FREDProvider:
    def __init__(self, api_key: str):
        self.fred = fred_client.FredClient(api_key)
    
    async def get_macro_indicators(self):
        """Get key macro indicators"""
        return {
            "gdp": self.fred.get_series("A191RL1Q225SBEA"),  # Real GDP
            "unemployment": self.fred.get_series("UNRATE"),  # Unemployment rate
            "inflation": self.fred.get_series("CPIAUCSL"),   # CPI
            "yield_curve": {
                "2yr": self.fred.get_series("DGS2"),
                "10yr": self.fred.get_series("DGS10"),
            },
            "federal_funds_rate": self.fred.get_series("FEDFUNDS")
        }
    
    async def get_market_regime_data(self):
        """Get data for regime detection"""
        return {
            "vix": self.fred.get_series("VIXCLS"),
            "credit_spreads": self.fred.get_series("BAA10Y"),
            "yield_spread_2_10": (
                self.fred.get_series("DGS10")[-1] - 
                self.fred.get_series("DGS2")[-1]
            )
        }
```

---

### 3.2 World Bank API

**Why**: Global economic data, country-level indicators
**Cost**: FREE
**API**: https://data.worldbank.org/developers/

**Setup**:

```bash
pip install wbdata
```

Create `world_bank_provider.py`:

```python
import wbdata
from datetime import datetime

class WorldBankProvider:
    async def get_country_indicators(self, country_code: str):
        """Get country-level economic data"""
        indicators = {
            "NY.GDP.MKTP.CD": "GDP (current US$)",
            "NY.GDP.PCAP.CD": "GDP per capita",
            "FP.CPI.TOTL.ZG": "Inflation rate",
            "NY.GDS.TOTL.ZS": "Gross savings (% of GNI)",
            "GC.DOD.TOTL.GD.ZS": "Govt debt (% of GDP)"
        }
        
        results = {}
        for code, name in indicators.items():
            try:
                data = wbdata.get_datapoint(code, country_code)
                results[name] = data
            except:
                results[name] = None
        
        return results
    
    async def get_country_ranking(self, indicator_code: str):
        """Get global ranking for an indicator"""
        try:
            data = wbdata.get_datapoints(indicator_code)
            return sorted(data.items(), 
                         key=lambda x: float(x[1]) if x[1] else 0,
                         reverse=True)
        except:
            return []
```

---

### 3.3 Trading Economics API

**Why**: Real-time economic calendar, forecasts
**Cost**: Paid ($99/month), Limited free tier
**API**: https://tradingeconomics.com/

**Setup** (Optional):

```bash
TRADING_ECONOMICS_KEY=your_key
```

---

## 4. ALTERNATIVE DATA APIs

### 4.1 Alternative Data APIs for Trading Signals

#### A) Stock Market Breadth Data (Free Alternative)

```python
# Create breadth_indicator.py
import aiohttp

class MarketBreadthIndicator:
    async def get_market_breadth(self):
        """Get advance/decline ratio from public sources"""
        # Use yfinance for market breadth
        import yfinance as yf
        
        # Get advance/decline line
        # This is a free metric available from multiple sources
        return {
            "advancing_stocks": None,  # Need real-time data source
            "declining_stocks": None,
            "breadth_ratio": None
        }
```

#### B) VIX & Volatility Data (Free via Yahoo Finance)

```python
import yfinance as yf

class VolatilityData:
    async def get_vix_data(self):
        """Get VIX index"""
        vix = yf.Ticker("^VIX")
        return vix.info
    
    async def get_put_call_ratio(self):
        """Get Put/Call ratio for market sentiment"""
        # Would need paid API - skip for free tier
        pass
```

---

### 4.2 Options Data APIs

#### Open Interest & Volume (Yahoo Finance - Free)

```python
import yfinance as yf

class OptionsAnalytics:
    async def get_option_chain(self, symbol: str):
        """Get option chain from Yahoo Finance"""
        stock = yf.Ticker(symbol)
        options = stock.option_chain()
        
        return {
            "calls": options.calls.to_dict(),
            "puts": options.puts.to_dict(),
            "iv": options.calls['impliedVolatility'].mean()
        }
    
    async def calculate_put_call_ratio(self, symbol: str):
        """Calculate Put/Call ratio"""
        options = await self.get_option_chain(symbol)
        
        call_volume = options['calls']['volume'].sum()
        put_volume = options['puts']['volume'].sum()
        
        return put_volume / call_volume if call_volume > 0 else 0
```

---

## 5. BLOCKCHAIN & CRYPTO APIs

### 5.1 Etherscan (Ethereum Blockchain Data)

**What it provides**: Gas prices, transaction data, smart contract analysis
**Cost**: Free tier available
**API**: https://etherscan.io/apis

**Setup**:

```bash
ETHERSCAN_API_KEY=your_key
pip install etherscan-python
```

**Integration**:

```python
from etherscan import Etherscan

class EthereumAnalytics:
    def __init__(self, api_key: str):
        self.eth = Etherscan(api_key)
    
    async def get_gas_prices(self):
        """Get current gas prices"""
        return self.eth.get_gas_tracker()
    
    async def get_eth_price(self):
        """Get ETH/USD price"""
        stats = self.eth.get_ether_lastprice()
        return float(stats['ethusd'])
    
    async def get_smart_contract_info(self, address: str):
        """Get smart contract source code"""
        source = self.eth.get_contract_source_code(address)
        return source
```

---

### 5.2 Messari (Crypto Intelligence)

**What it provides**: Crypto metrics, on-chain data, market analysis
**Cost**: Free tier available, $99+/month paid
**API**: https://messari.io/api

**Setup**:

```bash
# Free tier doesn't need API key
# Create messari_provider.py
```

---

## 6. SENTIMENT & NLP APIs

### 6.1 Twitter/X API (Advanced Tier)

**Why**: Real-time sentiment from market participants
**Cost**: $100-$5000+/month
**API**: https://developer.twitter.com/

**Setup** (Optional - Advanced):

```bash
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_BEARER_TOKEN=your_bearer_token

pip install tweepy
```

---

### 6.2 Google Trends (Free Web Search Trends)

**What it provides**: Search interest trends, relative popularity
**Cost**: FREE
**API**: Unofficial but stable

**Setup**:

```bash
pip install pytrends
```

Create `google_trends_provider.py`:

```python
from pytrends.request import TrendReq

class GoogleTrendsProvider:
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360)
    
    async def get_stock_interest(self, stock_symbols: list):
        """Get Google search trends for stocks"""
        self.pytrends.build_payload(
            kw_list=stock_symbols,
            cat=7,  # Finance category
            timeframe='now 1-d'  # Last 1 day
        )
        
        return {
            "interest_by_region": self.pytrends.interest_by_region(),
            "related_queries": self.pytrends.related_queries(),
            "related_topics": self.pytrends.related_topics()
        }
```

---

## 7. GEOPOLITICAL & POLICY DATA

### 7.1 World News API

**What it provides**: News aggregation by country, topic
**Cost**: Free tier, $59/month paid
**API**: https://worldnewsapi.com/

**Setup**:

```bash
WORLD_NEWS_API_KEY=your_key
```

---

### 7.2 Policy Event Calendar

**Free Options**:
1. ECB Calendar: https://www.ecb.europa.eu/
2. FOMC Calendar: https://www.federalreserve.gov/
3. Trading Economics Calendar: Already mentioned above

**Integration** (Scrape/Manual):

```python
class PolicyEventCalendar:
    async def get_upcoming_events(self):
        """Get policy events from various sources"""
        events = {
            "FOMC": [],      # Federal Reserve meetings
            "ECB": [],       # European Central Bank
            "BOE": [],       # Bank of England
            "BOJ": []        # Bank of Japan
        }
        
        # Would need web scraping or paid API
        return events
```

---

## 8. RECOMMENDED API SETUP (By Priority)

### TIER 1: ESSENTIAL (Must Have)

✅ **Already Integrated**:
- Upstox (Trading)
- CoinGecko (Crypto)
- Alpha Vantage (Stock data)
- Finnhub (Company data)
- NewsAPI (News)

⚠️ **Add These** (Free/Low Cost):
- FRED (Macro data) - FREE
- Etherscan (Blockchain) - FREE
- Google Trends (Search trends) - FREE
- Hugging Face Sentiment (NLP) - FREE

**Setup Time**: 2-3 hours
**Cost**: $0 (if using free tiers)

---

### TIER 2: ENHANCED (Nice to Have)

- Polygon.io ($199/month) - US stocks
- World Bank API - FREE
- Sentiment140 - FREE
- Trading Economics (Paid) - $99/month
- Twitter/X API - $100+/month

**Setup Time**: 4-6 hours
**Cost**: $99-200/month for premium features

---

### TIER 3: ADVANCED (Future)

- Machine learning data providers
- Advanced sentiment APIs
- Proprietary datasets
- Real-time alternative data

---

## 9. COMPLETE .env CONFIGURATION

Create `.env` file with all APIs:

```bash
# TRADING & MARKET DATA
UPSTOX_ACCESS_TOKEN=your_upstox_token
UPSTOX_SANDBOX_MODE=true
POLYGON_API_KEY=pk_live_...
ALPHA_VANTAGE_API_KEY=your_key
FINNHUB_API_KEY=your_key
NEWS_API_KEY=your_key

# MACRO DATA
FRED_API_KEY=your_key

# CRYPTO
COINGECKO_PRO_KEY=optional

# BLOCKCHAIN
ETHERSCAN_API_KEY=your_key
MESSARI_API_KEY=optional

# NLP & SENTIMENT
TWITTER_BEARER_TOKEN=optional
TRADING_ECONOMICS_KEY=optional

# DATABASE
DATABASE_URL=postgresql://user:pass@localhost/stratos
REDIS_URL=redis://localhost:6379

# LLM PROVIDERS
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# WEBHOOKS
WEBHOOK_SECRET=random_string
```

---

## 10. INTEGRATION CHECKLIST

### Data Fabric Layer

- [ ] Upstox integration
- [ ] FRED macro data
- [ ] World Bank data
- [ ] NewsAPI integration
- [ ] Etherscan blockchain data
- [ ] Google Trends data
- [ ] Data validation and normalization

### NLP Layer

- [ ] Finnhub news analysis
- [ ] Hugging Face sentiment
- [ ] Custom NLP models
- [ ] Named entity recognition
- [ ] Policy document analysis

### ML Layer

- [ ] Technical indicators
- [ ] Volatility models
- [ ] Sentiment aggregation
- [ ] Feature engineering

### Orchestrator Layer

- [ ] Tool registration with agents
- [ ] Multi-API fallback strategies
- [ ] Rate limiting coordination
- [ ] Error handling across APIs

### Frontend Layer

- [ ] API key management UI
- [ ] Connection status monitoring
- [ ] Data refresh intervals
- [ ] Error notifications

---

## 11. SAMPLE SETUP SCRIPT

```bash
#!/bin/bash

# setup_apis.sh

echo "🚀 STRATOS API Setup"

# 1. FRED
echo "1. Setting up FRED..."
curl -X GET "https://api.stlouisfed.org/fred/series/UNRATE?api_key=$FRED_API_KEY" \
  -H "Accept: application/json"

# 2. Etherscan
echo "2. Testing Etherscan..."
curl -X GET "https://api.etherscan.io/api?module=proxy&action=eth_gasPrice&apikey=$ETHERSCAN_API_KEY"

# 3. Google Trends (Python)
python3 << 'PYTHON'
from pytrends.request import TrendReq
pytrends = TrendReq(hl='en-US')
print("✓ Google Trends connected")
PYTHON

# 4. Upstox
python3 << 'PYTHON'
import os
token = os.getenv("UPSTOX_ACCESS_TOKEN")
if token:
    print("✓ Upstox token configured")
else:
    print("✗ Upstox token missing")
PYTHON

echo "✅ API setup complete!"
```

---

## 12. MONITORING & HEALTH CHECKS

Create `api_health_check.py`:

```python
import asyncio
from datetime import datetime

class APIHealthMonitor:
    async def check_all_apis(self):
        """Check all API connections"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "apis": {}
        }
        
        # Check each API
        apis = {
            "upstox": self.check_upstox,
            "polygon": self.check_polygon,
            "fred": self.check_fred,
            "etherscan": self.check_etherscan,
            # ... add more
        }
        
        for api_name, check_func in apis.items():
            try:
                result = await check_func()
                status["apis"][api_name] = {"status": "ok", "data": result}
            except Exception as e:
                status["apis"][api_name] = {"status": "error", "error": str(e)}
        
        return status
```

---

## 13. COST BREAKDOWN

| Service | Free Tier | Paid Tier | Used in STRATOS |
|---------|-----------|-----------|-----------------|
| Upstox | - | - | ✅ Trading |
| Alpha Vantage | 5 calls/min | $9/mo | ✅ Stocks |
| Finnhub | 60/min | $99/mo | ✅ News |
| NewsAPI | 100/day | $45/mo | ✅ News |
| FRED | Unlimited | - | ✅ Macro |
| CoinGecko | Unlimited | $50/mo | ✅ Crypto |
| Etherscan | Unlimited | - | ✅ Blockchain |
| Polygon | Limited | $199/mo | ⚠️ US Stocks |
| World Bank | Unlimited | - | ✅ Global Data |
| Google Trends | Unlimited | - | ✅ Trends |
| **Total** | **$0** | **$500+/mo** | - |

**Recommended**: Start with FREE tier ($0), upgrade as needed.

---

## 14. NEXT STEPS

1. ✅ Start with TIER 1 APIs (all free or already integrated)
2. ⚠️ Add FRED API (30 mins setup)
3. ⚠️ Add Etherscan (30 mins setup)
4. ⚠️ Add Google Trends (15 mins setup)
5. 🚀 Deploy and test
6. 📈 Scale with TIER 2 APIs as needed

---

## Support & References

- **FRED Docs**: https://fred.stlouisfed.org/docs/api/
- **Etherscan Docs**: https://etherscan.io/apis
- **Polygon Docs**: https://polygon.io/docs/
- **Finnhub Docs**: https://finnhub.io/docs/api/
- **CoinGecko Docs**: https://www.coingecko.com/api/documentations/v3

---

**Start with the essentials, scale thoughtfully! 🚀**

