# Deployment Guide for Atlas Chatbot

## ⚠️ Important: Cloudflare Limitations

**Cloudflare Pages/Workers do NOT natively support Python Flask applications.**

Cloudflare offers:
- **Cloudflare Pages**: Static sites only (HTML/CSS/JS)
- **Cloudflare Workers**: JavaScript/TypeScript runtime (not Python)

For a Flask backend like Atlas, you need a **server-based hosting provider**.

---

## Recommended Free Alternatives

### 🚀 Option 1: Render.com (Recommended - Easiest!)

1. Create account at [render.com](https://render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
5. Add environment variables (from `.env`):
   - `FLASK_SECRET_KEY`
   - `OPENROUTER_API_KEY`
   - `FIREBASE_API_KEY`
   - `FIREBASE_AUTH_DOMAIN`
   - `FIREBASE_PROJECT_ID_CLIENT`
   - `FIREBASE_STORAGE_BUCKET`
   - `FIREBASE_MESSAGING_SENDER_ID`
   - `FIREBASE_APP_ID`
6. Upload `serviceAccountKey.json` content as `FIREBASE_SERVICE_ACCOUNT` env var
7. Deploy!

**Free tier includes**: 750 hours/month, auto-deploy from Git

---

### 🚀 Option 2: Railway.app (Also Free & Easy!)

1. Create account at [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub"
3. Add environment variables in Railway dashboard
4. Railway auto-detects Python and deploys!

**Free tier includes**: $5 credit/month

---

### 🚀 Option 3: Heroku (Classic Option)

1. Install Heroku CLI
2. Run:
```bash
heroku login
heroku create atlas-chatbot
heroku config:set FLASK_SECRET_KEY=your_key
# Set all other env vars
git push heroku main
```

---

## Environment Variables Checklist

Make sure these are set in your hosting dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_SECRET_KEY` | ✅ | 64-char random hex string |
| `FLASK_DEBUG` | ✅ | Set to `False` |
| `ALLOWED_ORIGINS` | ✅ | Your domain (e.g., `https://atlas.render.com`) |
| `OPENROUTER_API_KEY` | ✅ | For AI responses |
| `FIREBASE_API_KEY` | ✅ | Firebase client config |
| `FIREBASE_AUTH_DOMAIN` | ✅ | Firebase client config |
| `FIREBASE_PROJECT_ID_CLIENT` | ✅ | Firebase client config |
| `FIREBASE_STORAGE_BUCKET` | ✅ | Firebase client config |
| `FIREBASE_MESSAGING_SENDER_ID` | ✅ | Firebase client config |
| `FIREBASE_APP_ID` | ✅ | Firebase client config |

---

## Firebase Service Account (Admin SDK)

For the backend to access Firestore, you have two options:

### Option A: Upload serviceAccountKey.json
Upload the file to your server (not recommended for most hosts)

### Option B: Environment Variable (Recommended)
1. Convert `serviceAccountKey.json` content to a single-line string
2. Set as `FIREBASE_SERVICE_ACCOUNT` environment variable
3. Update `app.py` to read from env var if file doesn't exist

---

## After Deployment

1. **Update ALLOWED_ORIGINS**: Set to your actual domain
   ```
   ALLOWED_ORIGINS=https://your-app.render.com
   ```

2. **Test the application**: 
   - Login/signup works
   - Chat responses work
   - Rate limiting is active (try rapid requests)

3. **Monitor logs** for any errors

---

## Security Reminders

✅ Debug mode is disabled  
✅ Rate limiting is enabled (100/min default, 30/min on chat)  
✅ CORS is restricted  
✅ Security headers are added  
✅ Firebase config loaded from backend  
✅ Flask secret key is strong  
