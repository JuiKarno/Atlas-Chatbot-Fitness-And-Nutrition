#!/usr/bin/env python
"""
Production WSGI entry point for Atlas Chatbot.
Use with Gunicorn or any WSGI server.

Usage:
    gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
"""

from app import app

if __name__ == "__main__":
    app.run()
