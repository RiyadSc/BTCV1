# Quant Trading Bot - Professional Trading Signals

A **fully serverless** quantitative trading application that generates institutional-grade trading signals based on market sentiment analysis.

## 🚀 Architecture

This application uses a **modern serverless architecture**:

- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Backend**: Supabase Edge Functions (Deno)
- **Database**: Supabase PostgreSQL
- **Authentication**: Supabase Auth with Google OAuth
- **Real-time Data**: Binance WebSocket API
- **Cron Jobs**: Supabase pg_cron extension

## ✨ Features

- **Daily Trading Signals**: Automatically generated at 9 PM EST
- **Real-time Market Data**: Live BTC price with WebSocket connection
- **Professional Dashboard**: Clean, modern UI for signal analysis
- **Signal History**: Track performance over time
- **Risk Management**: Position sizing and allocation guidance
- **Mobile Responsive**: Works on all devices

## 🏗️ Project Structure

```
├── frontend/                 # Next.js frontend application
│   ├── app/                 # App router pages
│   ├── components/          # React components
│   ├── lib/                 # Utilities and contexts
│   └── package.json         # Frontend dependencies
├── supabase/                # Supabase configuration
│   └── functions/           # Edge Functions
│       ├── generate-daily-signal/    # Daily signal generation
│       ├── get-daily-signal/         # Current signal retrieval
│       ├── get-signal-history/       # Historical signals
│       └── get-market-overview/      # Market sentiment data
├── fgi_strategy/            # Backtesting and strategy logic
├── storage/                 # Historical data storage
└── DEPLOYMENT.md            # Deployment instructions
```

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd Bot-QuantTradingV1.1
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Environment Variables
Create `frontend/.env`:
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Dashboard**: http://localhost:3000/dashboard (after authentication)

## 🔧 Edge Functions

All backend logic is handled by Supabase Edge Functions:

- **`generate-daily-signal`**: Runs daily at 9 PM EST via cron job
- **`get-daily-signal`**: Retrieves current trading signal
- **`get-signal-history`**: Fetches historical signal data
- **`get-market-overview`**: Provides market sentiment and price data

## 📊 Trading Strategy

The bot implements a **Fear & Greed Index (FGI)** based strategy:

- **Ultra Fear (FGI ≤ 15)**: 15% allocation
- **Fear (FGI 16-25)**: 10% allocation  
- **Neutral (FGI 26-74)**: Hold position
- **Greed (FGI 75-84)**: 15% sell
- **Ultra Greed (FGI ≥ 85)**: 20% sell

## 🚀 Deployment

### Vercel Deployment
```bash
cd frontend
npm run build
vercel --prod
```

### Environment Variables in Vercel
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## 🎯 Benefits

✅ **Fully Serverless**: No servers to manage or restart
✅ **Auto-scaling**: Handles traffic spikes automatically
✅ **Cost-effective**: Pay only for what you use
✅ **Zero downtime**: No manual intervention required
✅ **Global CDN**: Vercel provides edge caching
✅ **Real-time**: WebSocket connections for live data

## 📱 Usage

1. **Sign Up/In**: Use Google OAuth or email
2. **View Dashboard**: See current trading signal
3. **Check History**: Review past signals and performance
4. **Monitor Live**: Real-time BTC price and market data

## 🔍 Monitoring

- **Frontend**: Vercel dashboard
- **Edge Functions**: Supabase dashboard
- **Database**: Supabase dashboard
- **Cron Jobs**: Supabase pg_cron logs

## 🛠️ Development

### Running Locally
```bash
# Frontend
cd frontend
npm run dev

# Backend (Edge Functions)
# Deploy directly to Supabase from supabase/functions/
```

### Testing Edge Functions
```bash
# Test individual functions
supabase functions serve generate-daily-signal
supabase functions serve get-daily-signal
```

## 📚 Documentation

- **Deployment Guide**: See `DEPLOYMENT.md`
- **Supabase Docs**: https://supabase.com/docs
- **Vercel Docs**: https://vercel.com/docs

## 🤝 Support

- **Issues**: Create GitHub issue
- **Supabase**: https://supabase.com/support
- **Vercel**: https://vercel.com/support

## 📄 License

This project is proprietary software. All rights reserved.
