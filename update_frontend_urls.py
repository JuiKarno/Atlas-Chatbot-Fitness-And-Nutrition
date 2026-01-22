"""
Frontend API URL Update Script
This script updates all API endpoint calls in chat.html to use the Railway backend URL
"""

import re

def update_chat_html():
    # Read the chat.html file
    with open('frontend/chat.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Add config.js script tag after Firebase SDKs
    firebase_tag = '    <script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore-compat.js"></script>'
    config_tag = '    <script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore-compat.js"></script>\n\n    <!-- Backend API Configuration -->\n    <script src="config.js"></script>'
    
    if 'config.js' not in content:
        content = content.replace(firebase_tag, config_tag)
    
    # 2. Update initFirebase function to use backend URL
    old_firebase_init = "const response = await fetch('/api/firebase-config');"
    new_firebase_init = "const backendURL = window.API_CONFIG?.BASE_URL || '';\n                const response = await fetch(`${backendURL}/api/firebase-config`);"
    content = content.replace(old_firebase_init, new_firebase_init)
    
    # 3. Update all fetch calls to use backend URL
    # Pattern: fetch('/endpoint'
    
    # Define all API endpoints that need updating
    endpoints = [
        '/load-profile',
        '/update-user-profile',
        '/get-recommendation',
        '/generate-recipe',
        '/feedback',
        '/favorites',
        '/log-data',
        '/reset-preferences'
    ]
    
    for endpoint in endpoints:
        # Update POST requests
        pattern = f"fetch\\('{endpoint}'"
        replacement = f"fetch(`${{window.API_CONFIG?.BASE_URL || ''}}{endpoint}`"
        content = re.sub(pattern, replacement, content)
    
    # Write the updated content
    with open('frontend/chat.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ chat.html updated successfully!")
    print("All API endpoints now use Railway backend URL from config.js")

if __name__ == "__main__":
    update_chat_html()
