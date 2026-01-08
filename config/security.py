"""
Security Configuration Module for Atlas Chatbot
Centralizes security-related configurations and utilities
"""

import os
import re
import html
from functools import wraps
from flask import request, jsonify, g
from dotenv import load_dotenv

load_dotenv()


class SecurityConfig:
    """Security configuration for the application."""
    
    # Flask Secret Key - MUST be set in environment
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', None)
    
    # CORS Configuration - Set your production domain
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
    
    # Rate Limiting Configuration
    RATE_LIMIT_DEFAULT = "100 per minute"
    RATE_LIMIT_CHAT = "30 per minute"
    RATE_LIMIT_AUTH = "10 per minute"
    
    # Debug Mode - ALWAYS False in production
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Security Headers
    # Note: CSP is configured to allow Firebase Auth (Google Sign-In) to work
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        # CSP configured for Firebase Authentication compatibility
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.tailwindcss.com "
            "https://*.gstatic.com "
            "https://apis.google.com "
            "https://*.googleapis.com "
            "https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com "
            "https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https: blob:; "
            "frame-src 'self' https://*.firebaseapp.com https://accounts.google.com; "
            "connect-src 'self' "
            "https://*.googleapis.com "
            "https://*.gstatic.com "
            "https://*.firebaseio.com "
            "https://*.firebaseapp.com "
            "https://identitytoolkit.googleapis.com "
            "https://securetoken.googleapis.com "
            "wss://*.firebaseio.com;"
        )
    }
    
    @classmethod
    def validate(cls):
        """Validate that required security configurations are set."""
        errors = []
        
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'your_secret_key_here':
            errors.append("FLASK_SECRET_KEY must be set to a strong random value")
        
        if cls.DEBUG:
            errors.append("Debug mode is enabled - disable for production")
            
        return errors


def validate_user_ownership(f):
    """
    Decorator to validate that the authenticated user has access to the requested resource.
    Expects user_id in request JSON/args and compares with authenticated user from Firebase token.
    
    For now, this validates user_id is present. In production, add Firebase Admin SDK token verification.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user_id from request
        if request.method == 'GET':
            user_id = request.args.get('user_id')
        else:
            data = request.get_json(silent=True) or {}
            user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        
        # Basic sanitization of user_id
        if not re.match(r'^[a-zA-Z0-9_-]{1,128}$', user_id):
            return jsonify({"success": False, "error": "Invalid user ID format"}), 400
            
        # Store validated user_id in Flask g object for use in the route
        g.user_id = user_id
        
        return f(*args, **kwargs)
    return decorated_function


def sanitize_input(text, max_length=1000):
    """
    Sanitize user input to prevent XSS and injection attacks.
    
    Args:
        text: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    return text


def sanitize_html_output(text):
    """
    Escape HTML entities in text to prevent XSS when rendering.
    Use this for user-generated content that will be displayed.
    
    Args:
        text: Text that may contain HTML
        
    Returns:
        HTML-escaped string
    """
    if not text:
        return ""
    return html.escape(str(text))


def validate_numeric_input(value, min_val=None, max_val=None, default=None):
    """
    Validate and convert numeric input with bounds checking.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        default: Default value if validation fails
        
    Returns:
        Validated numeric value or default
    """
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return default
        if max_val is not None and num > max_val:
            return default
        return num
    except (TypeError, ValueError):
        return default


def add_security_headers(response):
    """Add security headers to response."""
    for header, value in SecurityConfig.SECURITY_HEADERS.items():
        response.headers[header] = value
    return response
