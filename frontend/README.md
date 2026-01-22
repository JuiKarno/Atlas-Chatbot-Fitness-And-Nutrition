# Frontend Files for Render Static Site

This directory contains the static frontend files that will be deployed to Render.

## Structure

- `index.html` - Login/signup page (originally auth.html)
- `chat.html` - Main chatbot interface (originally chatbot.html)  
- `config.js` - Backend API URL configuration
- `static/` - Static assets (images, etc.)
- `_redirects` - Render routing configuration

## Before Deploying

1. Deploy your backend to Railway first
2. Get your Railway backend URL (e.g., `https://your-app.up.railway.app`)
3. Update `config.js` with your Railway URL:
   ```javascript
   window.API_CONFIG = {
       BASE_URL: 'https://your-railway-url.up.railway.app'
   };
   ```

## Deployment

These files will be deployed to Render as a static site.
See the Railway deployment guide for complete instructions.
