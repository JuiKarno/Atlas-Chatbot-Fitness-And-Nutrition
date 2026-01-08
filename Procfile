# Procfile for production deployment (Heroku, Railway, Render, etc.)
# Cloudflare Workers requires different setup - see DEPLOYMENT.md

web: gunicorn -w 4 -b 0.0.0.0:$PORT wsgi:app
