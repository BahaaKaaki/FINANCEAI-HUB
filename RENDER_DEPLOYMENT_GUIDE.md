# Render.com Deployment Guide

## Quick Deploy to Render.com

1. Go to [Render.com](https://render.com) and sign up/login
2. Connect your GitHub account and select `BahaaKaaki/FinanceAI-Hub`
3. **Create New Web Service**
   - Name: `financeai-hub`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. **Environment Variables** (Add in Render Dashboard or import from .env)
   ```
   DEBUG=false
   LOG_LEVEL=INFO
   DATABASE_URL=sqlite:///./financial_data.db
   DATABASE_ECHO=false
   DEFAULT_LLM_PROVIDER=openai
   OPENAI_MODEL=gpt-4o-mini
   MAX_TOKENS=4000
   TEMPERATURE=0.1
   MAX_CONCURRENT_REQUESTS=100
   REQUEST_TIMEOUT=30
   
   # Add your API keys (REQUIRED)
   OPENAI_API_KEY=openai_key
   GROQ_API_KEY=groq_key
   ANTHROPIC_API_KEY=anthropic_key
   ```

## Free Tier Limitations

Render.com free tier includes:
- ✅ 750 hours/month (enough for continuous running)
- ✅ Custom domains
- ✅ Automatic HTTPS
- ✅ Git-based deployments
- ⚠️ Spins down after 15 minutes of inactivity
- ⚠️ 512MB RAM limit
- ⚠️ Shared CPU

## Production Considerations

### Database Upgrade (Recommended)
For production, upgrade from SQLite to PostgreSQL:

1. **Add PostgreSQL Service** in Render:
   - Go to Dashboard → "New +" → "PostgreSQL"
   - Choose free tier (1GB storage)
   - Note the connection string

2. **Update Environment Variables**:
   ```
   DATABASE_URL=postgresql://username:password@host:port/database
   ```

3. **Update requirements.txt**:
   ```
   psycopg2-binary==2.9.9
   ```

### Performance Optimization

1. **Enable Persistent Storage** (Paid feature):
   - Add disk storage for database files
   - Prevents data loss on service restarts

2. **Upgrade to Paid Plan** for:
   - No sleep mode
   - More RAM (1GB+)
   - Dedicated CPU
   - Custom build minutes

## Deployment Steps

### 1. Prepare Repository
```bash
# Ensure all files are committed
git add .
git commit -m "Prepare for Render deployment"
git push origin master
```

### 2. Deploy on Render
1. Visit [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect GitHub → Select `FinanceAI-Hub`
4. Configure:
   - **Name**: `financeai-hub`
   - **Branch**: `master`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3. Add Environment Variables
In Render dashboard, add these environment variables:

**Required API Keys:**
- `OPENAI_API_KEY` - OpenAI API key
- `GROQ_API_KEY` - Groq API key  
- `ANTHROPIC_API_KEY` - Anthropic API key

**Optional Configuration:**
- `DEBUG=false`
- `LOG_LEVEL=INFO`
- `MAX_CONCURRENT_REQUESTS=50` (lower for free tier)

### 4. Deploy
Click "Create Web Service" - Render will:
1. Clone your repository
2. Install dependencies
3. Start your application
4. Provide a public URL

## Post-Deployment

### 1. Test Your Deployment
Your app will be available at: `https://financeai-hub.onrender.com`

Test endpoints:
```bash
# Health check
curl https://financeai-hub.onrender.com/health

# API documentation
https://financeai-hub.onrender.com/docs

# Upload test data
curl -X POST https://financeai-hub.onrender.com/api/v1/data/ingest \
  -F "file=@data_set_1.json" \
  -F "source_type=quickbooks"
```

### 2. Monitor Performance
- Check Render dashboard for logs
- Monitor response times
- Watch for memory usage warnings

### 3. Custom Domain (Optional)
1. Go to Settings → Custom Domains
2. Add your domain
3. Update DNS records as instructed

## Troubleshooting

### Common Issues

**1. Build Failures**
- Check `requirements.txt` for version conflicts
- Ensure Python 3.12 compatibility
- Review build logs in Render dashboard

**2. Memory Issues**
- Reduce `MAX_CONCURRENT_REQUESTS` to 10-20
- Optimize database queries
- Consider upgrading to paid plan

**3. Cold Starts**
- Free tier sleeps after 15 minutes
- First request after sleep takes 30-60 seconds
- Consider using a service like UptimeRobot for keep-alive

**4. Database Issues**
- SQLite works but has limitations
- Consider PostgreSQL for production
- Ensure proper database initialization

### Logs and Debugging
```bash
# View logs in Render dashboard or via CLI
render logs --service financeai-hub --tail
```

## Cost Optimization

### Free Tier Tips
1. **Optimize Memory Usage**:
   - Use SQLite instead of PostgreSQL initially
   - Limit concurrent requests
   - Implement request caching

2. **Reduce Build Time**:
   - Use `.dockerignore` to exclude unnecessary files
   - Cache pip dependencies

3. **Monitor Usage**:
   - Track monthly hours (750 limit)
   - Monitor bandwidth usage
   - Watch for memory warnings

### Upgrade Path
When ready for production:
1. **Starter Plan** ($7/month):
   - No sleep mode
   - 1GB RAM
   - Faster builds

2. **PostgreSQL** ($7/month):
   - 1GB storage
   - Better performance
   - Data persistence

## Security Checklist

- ✅ API keys stored as environment variables
- ✅ `.env` file in `.gitignore`
- ✅ HTTPS enabled by default
- ✅ CORS configured properly
- ⚠️ Add authentication for production
- ⚠️ Implement rate limiting
- ⚠️ Add input validation

## Next Steps

1. **Deploy and Test** - Get our app running (done on render)
2. **Add Authentication** - Secure the endpoints
3. **Database Upgrade** - Move to PostgreSQL
4. **Monitoring** - Add error tracking (Sentry)
5. **CI/CD** - Automate deployments
6. **Custom Domain** - Professional appearance