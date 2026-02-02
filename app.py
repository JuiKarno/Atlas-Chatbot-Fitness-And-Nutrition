import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import os

# Security imports
from config.security import (
    SecurityConfig,
    validate_user_ownership,
    sanitize_input,
    add_security_headers,
    validate_numeric_input
)

# --- CONFIG & CORE IMPORTS ---
from config.settings import Config
from core.nlu_engine import SmartNLUEngine
from core.recommender import ContentBasedRecommender
from core.user_manager import UserManager
from core.safety_validator import SafetyValidator
from core.simple_memory import SimpleMemory

# Helpers
from core.response_formatter import (
    format_exercise_card, 
    format_nutrition_card,
    format_log_confirmation,
    format_weight_report,
    format_nutrition_report,
    format_workout_history
)
from core.calculator import calculate_bmi, calculate_target_calories

# --- FIREBASE INIT ---
import json

if not firebase_admin._apps:
    key_path = Config.FIREBASE_CREDENTIALS if hasattr(Config, 'FIREBASE_CREDENTIALS') else 'serviceAccountKey.json'
    
    # Option 1: Load from environment variable (Railway deployment)
    firebase_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
    if firebase_json:
        try:
            service_account_info = json.loads(firebase_json)
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized from environment variable.")
        except json.JSONDecodeError as e:
            print(f"Error parsing FIREBASE_SERVICE_ACCOUNT_JSON: {e}")
    # Option 2: Load from file (local/Render deployment)
    elif os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        print("Firebase initialized from serviceAccountKey.json file.")
    else:
        print("Warning: No Firebase credentials found. Set FIREBASE_SERVICE_ACCOUNT_JSON env var or provide serviceAccountKey.json")

db_client = firestore.client() if firebase_admin._apps else None

app = Flask(__name__)
app.secret_key = SecurityConfig.SECRET_KEY

# CORS Configuration - allow frontend from different domain (Render)
# In production, ALLOWED_ORIGINS env var should be set to your Render frontend URL
CORS(app, 
     origins=SecurityConfig.ALLOWED_ORIGINS,
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     expose_headers=['Content-Type'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[SecurityConfig.RATE_LIMIT_DEFAULT],
    storage_uri="memory://"
)

# Add security headers to all responses
@app.after_request
def after_request(response):
    return add_security_headers(response)

# --- ENGINE INIT ---
nlu = SmartNLUEngine()
recommender = ContentBasedRecommender()
# UserManager expects key_path, not db_client - let it initialize its own connection
key_path = Config.FIREBASE_CREDENTIALS if hasattr(Config, 'FIREBASE_CREDENTIALS') else 'serviceAccountKey.json'
user_manager = UserManager(key_path)



# --- ROUTES ---
@app.route('/')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        "status": "healthy",
        "service": "Atlas Backend API",
        "version": "2.0"
    }), 200


@app.route('/health')
def health():
    """Alternative health check endpoint"""
    return jsonify({"status": "ok"}), 200


@app.route('/api/firebase-config')
def firebase_config():
    """Serve Firebase client config from environment variables"""
    return jsonify({
        "apiKey": os.getenv('FIREBASE_API_KEY'),
        "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
        "projectId": os.getenv('FIREBASE_PROJECT_ID_CLIENT'),
        "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
        "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
        "appId": os.getenv('FIREBASE_APP_ID')
    })


# --- API ENDPOINTS ---
@app.route('/load-profile', methods=['POST'])
def load_profile():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "No user ID provided"}), 400

        profile = user_manager.get_user(user_id)
        if profile:
            return jsonify({"success": True, "profile": profile})
        else:
            return jsonify({"success": False, "error": "Profile not found"}), 404

    except Exception as e:
        print(f"Error loading profile: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500


@app.route('/update-user-profile', methods=['POST'])
def update_profile():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        updates = data.get('updates', {})

        current_profile = user_manager.get_user(user_id) or {}
        full_data = current_profile.copy()
        full_data.update(updates)

        clean_updates = {}
        allowed_fields = [
            'name', 'age', 'gender', 'weight', 'height',
            'goal', 'fitness_level', 'medical_conditions'
        ]

        for k in allowed_fields:
            if k in updates:
                clean_updates[k] = updates[k]

        if 'age' in updates and updates['age']: clean_updates['age'] = int(updates['age'])
        if 'weight' in updates and updates['weight']: clean_updates['weight'] = float(updates['weight'])
        if 'height' in updates and updates['height']: clean_updates['height'] = float(updates['height'])

        w = float(full_data.get('weight', 0))
        h = float(full_data.get('height', 0))
        a = int(full_data.get('age', 0))
        g = full_data.get('gender', 'Male')
        goal = full_data.get('goal', 'General')

        if w > 0 and h > 0:
            bmi = calculate_bmi(w, h)
            if bmi: clean_updates['bmi'] = bmi

        if w > 0 and h > 0 and a > 0:
            cals = calculate_target_calories(w, h, a, g, goal)
            if cals: clean_updates['target_calories'] = cals

        user_manager.create_or_update_user(user_id, clean_updates)
        return jsonify({"success": True, "profile": clean_updates})

    except Exception as e:
        print(f"Update Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/generate-recipe', methods=['POST'])
def generate_recipe_endpoint():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        food_name = data.get('food_name')

        profile = user_manager.get_user(user_id) or {}
        recipe_html = nlu.generate_recipe(food_name, profile)

        return jsonify({"success": True, "recipe": recipe_html})
    except Exception as e:
        print(f"Recipe Gen Error: {e}")
        return jsonify({"success": False, "error": "Chef is busy!"}), 500


@app.route('/reset-preferences', methods=['POST'])
def reset_preferences():
    """Clears user's likes and dislikes from session."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "No user ID"}), 400
        
        # The preferences are stored in session, so we just return success
        # The frontend will clear its local session data
        # If you want to persist preferences in Firestore, you would clear them here
        
        return jsonify({"success": True, "message": "Preferences cleared"})
    except Exception as e:
        print(f"Reset Preferences Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/feedback', methods=['POST'])
def handle_feedback():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        item_data = data.get('item_data')
        rating = data.get('rating') # 'good' or 'bad'
        item_type = data.get('item_type', 'exercise')

        if not user_id or not item_data or not rating:
            return jsonify({"success": False, "error": "Missing data"}), 400

        item_name = item_data.get('Title') or item_data.get('Name')

        if rating == 'good':
            # Save to favorites
            success = user_manager.add_favorite(user_id, item_data, item_type)
            msg = f"Saved {item_name} to your favorites!"
        else:
            # Add to permanent ignore list
            success = user_manager.add_to_ignore_list(user_id, item_name)
            msg = f"Understood. I'll stop recommending {item_name}."

        return jsonify({"success": success, "message": msg})
    except Exception as e:
        print(f"Feedback Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/favorites', methods=['GET'])
def get_favorites():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "No user ID"}), 400

        favorites = user_manager.get_favorites(user_id)
        return jsonify({"success": True, "favorites": favorites})
    except Exception as e:
        print(f"Get Favorites Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/log-data', methods=['POST'])
def log_data():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        log_type = data.get('type') # 'weight', 'nutrition'
        payload = data.get('data')

        if not user_id or not log_type or not payload:
            return jsonify({"success": False, "error": "Missing data"}), 400

        if log_type == 'weight':
            success = user_manager.log_weight(user_id, payload.get('weight'))
        elif log_type == 'nutrition':
            success = user_manager.log_nutrition(user_id, payload)
        else:
            return jsonify({"success": False, "error": "Invalid log type"}), 400

        return jsonify({"success": success})
    except Exception as e:
        print(f"Log Data Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/get-recommendation', methods=['POST'])
@limiter.limit(SecurityConfig.RATE_LIMIT_CHAT)
def chat_endpoint():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        message = data.get('message')
        session_data = data.get('session', {})

        history = session_data.get('history', [])
        seen_titles = session_data.get('seen_titles', [])
        last_target = session_data.get('last_target', None)

        # --- PREFERENCE MANAGEMENT (Session) ---
        likes = session_data.get('likes', [])
        dislikes = session_data.get('dislikes', [])

        # 1. FETCH PROFILE
        profile = user_manager.get_user(user_id) or {}

        # 2. ANALYZE INTENT
        analysis = nlu.analyze_message(message, history)
        intent = analysis.get('intent', 'general_chat')
        entities = analysis.get('entities', {})
        new_target = entities.get('target', None)

        # --- HANDLE PREFERENCE UPDATES ---
        # Extract preference/dislike entity
        pref_item = entities.get('preference')

        # Handle list-based preferences from compound sentences
        pref_list = entities.get('preferences', [])
        dislike_list = entities.get('dislikes', [])

        # Merge singular and list preferences
        if pref_item: pref_list.append(pref_item)

        # ALWAYS process preferences from entities (for compound messages like "I like X, give me workout")
        for item in pref_list:
            clean_item = item.lower().strip()
            if clean_item and clean_item not in likes:
                likes.append(clean_item)
            if clean_item in dislikes:
                dislikes.remove(clean_item)

        # ALWAYS process dislikes from entities (for compound messages like "I hate X, suggest workout")
        for item in dislike_list:
            clean_item = item.lower().strip()
            if clean_item and clean_item not in dislikes:
                dislikes.append(clean_item)
            if clean_item in likes:
                likes.remove(clean_item)

        # Clear Preferences (only when explicitly requested)
        if intent == 'clear_preferences':
            likes = []
            dislikes = []

        # --- HANDLE NO EQUIPMENT FLAG ---
        no_equipment = session_data.get('no_equipment', False)
        if entities.get('no_equipment'):
            no_equipment = True
            session_data['no_equipment'] = True

        # Debug log to verify preferences are being captured
        print(f"[App] After processing - Likes: {likes}, Dislikes: {dislikes}, No Equipment: {no_equipment}")

        # Define health-related intents that require profile access
        health_intents = [
            'fitness_request', 'fitness_variation',
            'nutrition_request', 'nutrition_variation',
            'explain_exercise', 'nutrition_recipe'
        ]
        
        # Progress tracking intents (don't require full profile)
        progress_intents = ['log_weight', 'log_nutrition', 'log_workout', 'view_progress']

        # 3. CHECK PROFILE COMPLETENESS FOR HEALTH INTENTS
        if intent in health_intents:
            # Check if profile has required fields for personalized recommendations
            has_weight = profile.get('weight') is not None and profile.get('weight') != ''
            has_height = profile.get('height') is not None and profile.get('height') != ''
            has_goal = profile.get('goal') is not None and profile.get('goal') != ''
            
            if not (has_weight and has_height and has_goal):
                incomplete_msg = """
                    <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl p-4">
                        <div class="flex items-start gap-3">
                            <div class="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-800 text-amber-600 dark:text-amber-300 flex items-center justify-center shrink-0">
                                <i class="fas fa-user-edit"></i>
                            </div>
                            <div>
                                <h4 class="font-bold text-amber-800 dark:text-amber-200 mb-1">Complete Your Profile First</h4>
                                <p class="text-sm text-amber-700 dark:text-amber-300 mb-3">
                                    To give you personalized workout and nutrition recommendations, I need to know a bit more about you.
                                </p>
                                <p class="text-sm text-amber-600 dark:text-amber-400">
                                    Click the <b>"Start Setup"</b> button on the welcome screen, or go to <b>Settings → Edit Profile</b> to complete your profile.
                                </p>
                            </div>
                        </div>
                    </div>
                """
                return jsonify({"reply": incomplete_msg, "session": session_data, "intent": "profile_incomplete"})

        # 4. CONDITIONAL SAFETY CHECK
        if intent in health_intents:
            is_safe, safety_msg = SafetyValidator.validate_request(profile)
            if not is_safe:
                if db_client:
                    db_client.collection('users').document(user_id).collection('journey_logs').add({
                        'timestamp': datetime.now(), 'intent': 'safety_block', 'user_message': message
                    })
                return jsonify({"reply": safety_msg, "session": session_data, "intent": "safety_block"})

        # ============================================
        # PROGRESS TRACKING HANDLERS
        # ============================================

        # 5a. LOG WEIGHT HANDLER
        if intent == 'log_weight':
            weight = entities.get('weight')
            ask_bmi = entities.get('ask_bmi', False)
            
            if weight:
                try:
                    weight = float(weight)
                    result = user_manager.add_weight_log(user_id, weight)
                    
                    if result:
                        # If user also asked for BMI, calculate and include it
                        if ask_bmi and profile.get('height'):
                            height_m = float(profile.get('height')) / 100
                            new_bmi = weight / (height_m * height_m)
                            bmi_category = ""
                            if new_bmi < 18.5:
                                bmi_category = "Underweight"
                                cat_color = "text-blue-600 bg-blue-100"
                            elif new_bmi < 25:
                                bmi_category = "Normal"
                                cat_color = "text-green-600 bg-green-100"
                            elif new_bmi < 30:
                                bmi_category = "Overweight"
                                cat_color = "text-orange-600 bg-orange-100"
                            else:
                                bmi_category = "Obese"
                                cat_color = "text-red-600 bg-red-100"
                            
                            response = f"""
                            <div class="bg-emerald-50 dark:bg-emerald-900/20 p-5 rounded-xl border border-emerald-200 dark:border-emerald-800">
                                <div class="flex items-center gap-3 mb-4">
                                    <div class="w-12 h-12 rounded-full bg-emerald-500 text-white flex items-center justify-center">
                                        <i class="fas fa-check text-xl"></i>
                                    </div>
                                    <div>
                                        <h4 class="font-bold text-emerald-700 dark:text-emerald-300">Weight Updated!</h4>
                                        <p class="text-sm text-emerald-600 dark:text-emerald-400">Your weight has been logged as <b>{weight} kg</b></p>
                                    </div>
                                </div>
                                <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-emerald-100 dark:border-slate-700">
                                    <div class="text-xs font-bold text-slate-400 uppercase mb-1">Your Current BMI</div>
                                    <div class="flex items-center gap-3">
                                        <span class="text-3xl font-black text-slate-800 dark:text-white">{new_bmi:.1f}</span>
                                        <span class="px-3 py-1 rounded-lg text-sm font-bold {cat_color}">{bmi_category}</span>
                                    </div>
                                </div>
                            </div>
                            """
                        else:
                            response = format_log_confirmation('weight', result)
                        
                        return jsonify({"reply": response, "session": session_data, "intent": "log_weight"})
                except (ValueError, TypeError):
                    pass
            
            # If weight not extracted, ask for it
            response = """
            <div class="bg-emerald-50 dark:bg-emerald-900/20 p-4 rounded-xl border border-emerald-200 dark:border-emerald-800">
                <h4 class="font-bold text-emerald-700 dark:text-emerald-300 mb-2"><i class="fas fa-weight"></i> Log Your Weight</h4>
                <p class="text-sm text-emerald-600 dark:text-emerald-400">Please tell me your current weight, like <b>"I weigh 75kg"</b> or <b>"My weight is 68.5 kg"</b></p>
            </div>
            """
            return jsonify({"reply": response, "session": session_data, "intent": "log_weight"})


        # 5b. LOG NUTRITION HANDLER
        if intent == 'log_nutrition':
            calories = entities.get('calories')
            protein = entities.get('protein')
            carbs = entities.get('carbs')
            fat = entities.get('fat')
            
            # Convert to numbers if provided
            try:
                calories = float(calories) if calories else None
                protein = float(protein) if protein else None
                carbs = float(carbs) if carbs else None
                fat = float(fat) if fat else None
            except (ValueError, TypeError):
                calories = protein = carbs = fat = None
            
            if any([calories, protein, carbs, fat]):
                result = user_manager.add_nutrition_log(user_id, calories, protein, carbs, fat)
                if result:
                    # Build logged data for confirmation
                    logged_data = {}
                    if calories: logged_data['calories'] = int(calories)
                    if protein: logged_data['protein'] = int(protein)
                    if carbs: logged_data['carbs'] = int(carbs)
                    if fat: logged_data['fat'] = int(fat)
                    
                    response = format_log_confirmation('nutrition', logged_data)
                    return jsonify({"reply": response, "session": session_data, "intent": "log_nutrition"})
            
            # If nothing extracted, ask for details
            response = """
            <div class="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-xl border border-amber-200 dark:border-amber-800">
                <h4 class="font-bold text-amber-700 dark:text-amber-300 mb-2"><i class="fas fa-utensils"></i> Log Your Nutrition</h4>
                <p class="text-sm text-amber-600 dark:text-amber-400 mb-2">Tell me what you ate! Examples:</p>
                <ul class="text-sm text-amber-600 dark:text-amber-400 space-y-1">
                    <li>• "I ate 500 calories"</li>
                    <li>• "Log 40g protein and 300 calories"</li>
                    <li>• "Had 50g carbs and 20g fat"</li>
                </ul>
            </div>
            """
            return jsonify({"reply": response, "session": session_data, "intent": "log_nutrition"})

        # 5c. LOG WORKOUT HANDLER
        if intent == 'log_workout':
            workout_name = entities.get('workout_name', 'General')
            exercises = entities.get('exercises', [])
            duration = entities.get('duration')
            
            result = user_manager.add_workout_log(user_id, workout_name, exercises, duration)
            if result:
                response = format_log_confirmation('workout', {'workout_name': workout_name})
                return jsonify({"reply": response, "session": session_data, "intent": "log_workout"})
            
            # Fallback
            response = """
            <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl border border-blue-200 dark:border-blue-800">
                <h4 class="font-bold text-blue-700 dark:text-blue-300 mb-2"><i class="fas fa-dumbbell"></i> Workout Logged!</h4>
                <p class="text-sm text-blue-600 dark:text-blue-400">Great job completing your workout! 💪</p>
            </div>
            """
            return jsonify({"reply": response, "session": session_data, "intent": "log_workout"})

        # 5d. VIEW PROGRESS HANDLER
        if intent == 'view_progress':
            progress_type = entities.get('progress_type', 'all')
            
            if progress_type == 'weight' or progress_type == 'all':
                logs = user_manager.get_weight_logs(user_id, days=7)
                current_weight = profile.get('weight', 0)
                current_bmi = profile.get('bmi')
                response = format_weight_report(logs, current_weight, current_bmi)
                return jsonify({"reply": response, "session": session_data, "intent": "view_progress"})
            
            elif progress_type == 'nutrition':
                today_data = user_manager.get_today_nutrition(user_id)
                # Calculate target calories if profile has data
                target_calories = 2000
                if profile.get('weight') and profile.get('height') and profile.get('age'):
                    target_calories = calculate_target_calories(
                        profile.get('weight'),
                        profile.get('height'),
                        profile.get('age'),
                        profile.get('gender', 'Male'),
                        profile.get('activity_level', 'Moderate'),
                        profile.get('goal', 'Maintain')
                    )
                response = format_nutrition_report(today_data, target_calories)
                return jsonify({"reply": response, "session": session_data, "intent": "view_progress"})
            
            elif progress_type == 'workout':
                logs = user_manager.get_workout_logs(user_id, days=7)
                response = format_workout_history(logs)
                return jsonify({"reply": response, "session": session_data, "intent": "view_progress"})
            
            # Default: show weight progress
            logs = user_manager.get_weight_logs(user_id, days=7)
            current_weight = profile.get('weight', 0)
            current_bmi = profile.get('bmi')
            response = format_weight_report(logs, current_weight, current_bmi)
            return jsonify({"reply": response, "session": session_data, "intent": "view_progress"})





        # 5. WORKOUT TABLE HANDLER - Weekly workout schedule with real data
        if intent == 'workout_table' or 'timetable' in message.lower() or 'schedule' in message.lower():
            # Extract workout/rest days from entities or default to 5/2
            workout_days = entities.get('workout_days', 5)
            rest_days = entities.get('rest_days', 2)
            
            # Define muscle group splits based on goal
            goal = profile.get('goal', 'General Fitness')
            level = profile.get('fitness_level', 'Beginner')
            
            # Create weekly split
            if 'Muscle' in goal or 'Strength' in goal:
                weekly_split = [
                    {'day': 'Monday', 'focus': 'Push (Chest/Tri)', 'targets': ['Chest', 'Triceps']},
                    {'day': 'Tuesday', 'focus': 'Pull (Back/Bi)', 'targets': ['Back', 'Biceps']},
                    {'day': 'Wednesday', 'focus': 'Legs & Core', 'targets': ['Legs', 'Core']},
                    {'day': 'Thursday', 'focus': 'Push (Shoulders)', 'targets': ['Shoulder', 'Chest']},
                    {'day': 'Friday', 'focus': 'Pull & Arms', 'targets': ['Back', 'Biceps', 'Triceps']},
                    {'day': 'Saturday', 'focus': 'Rest', 'targets': []},
                    {'day': 'Sunday', 'focus': 'Rest', 'targets': []}
                ]
            elif 'Loss' in goal:
                weekly_split = [
                    {'day': 'Monday', 'focus': 'Full Body HIIT', 'targets': ['Full Body', 'Cardio']},
                    {'day': 'Tuesday', 'focus': 'Upper Body', 'targets': ['Chest', 'Back', 'Shoulder']},
                    {'day': 'Wednesday', 'focus': 'Active Recovery', 'targets': []},
                    {'day': 'Thursday', 'focus': 'Lower Body', 'targets': ['Legs', 'Core']},
                    {'day': 'Friday', 'focus': 'Full Body Circuit', 'targets': ['Full Body']},
                    {'day': 'Saturday', 'focus': 'Cardio/HIIT', 'targets': ['Cardio']},
                    {'day': 'Sunday', 'focus': 'Rest', 'targets': []}
                ]
            else:
                weekly_split = [
                    {'day': 'Monday', 'focus': 'Upper Body', 'targets': ['Chest', 'Back']},
                    {'day': 'Tuesday', 'focus': 'Lower Body', 'targets': ['Legs']},
                    {'day': 'Wednesday', 'focus': 'Rest', 'targets': []},
                    {'day': 'Thursday', 'focus': 'Push Day', 'targets': ['Chest', 'Shoulder', 'Triceps']},
                    {'day': 'Friday', 'focus': 'Pull Day', 'targets': ['Back', 'Biceps']},
                    {'day': 'Saturday', 'focus': 'Full Body', 'targets': ['Full Body']},
                    {'day': 'Sunday', 'focus': 'Rest', 'targets': []}
                ]
            
            # Fetch real exercises from Firestore for each day
            table_rows = []
            for day_plan in weekly_split:
                if day_plan['targets']:
                    exercises = []
                    for target in day_plan['targets'][:2]:  # Max 2 targets per day
                        try:
                            docs = db_client.collection('Fitness').where('Primary_Muscle', '==', target).where('Level', '==', level).limit(2).stream()
                            for doc in docs:
                                data = doc.to_dict()
                                exercises.append(data.get('Exercise_Name', 'Exercise'))
                        except:
                            exercises.append(f"{target} Exercise")
                    
                    if not exercises:
                        exercises = [f"{t} workout" for t in day_plan['targets'][:3]]
                    
                    exercises_str = ', '.join(exercises[:4])
                else:
                    exercises_str = '<span class="text-slate-400">Active Recovery / Stretching</span>'
                
                row_class = 'bg-green-50 dark:bg-green-900/10' if day_plan['focus'] == 'Rest' else ''
                table_rows.append(f"""
                    <tr class="{row_class}">
                        <td class="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">{day_plan['day']}</td>
                        <td class="px-4 py-3"><span class="px-2 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-lg text-sm font-semibold">{day_plan['focus']}</span></td>
                        <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{exercises_str}</td>
                    </tr>
                """)
            
            table_html = f"""
                <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-lg">
                    <div class="bg-gradient-to-r from-brand-500 to-brand-600 px-5 py-4">
                        <h3 class="text-xl font-black text-white"><i class="fas fa-calendar-week mr-2"></i>Your Weekly Workout Schedule</h3>
                        <p class="text-sm text-white/80 mt-1">Customized for <b>{goal}</b> • {level} Level</p>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full">
                            <thead class="bg-slate-50 dark:bg-slate-700/50">
                                <tr>
                                    <th class="px-4 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Day</th>
                                    <th class="px-4 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Focus</th>
                                    <th class="px-4 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Exercises</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
                                {''.join(table_rows)}
                            </tbody>
                        </table>
                    </div>
                    <div class="px-5 py-3 bg-slate-50 dark:bg-slate-700/30 text-xs text-slate-500 dark:text-slate-400">
                        <i class="fas fa-lightbulb text-amber-500 mr-1"></i> Tip: Click on any exercise in the chat to see how to do it!
                    </div>
                </div>
            """
            return jsonify({"reply": table_html, "session": session_data, "intent": "workout_table"})

        # Helper for Logging
        final_target = new_target or "General"
        bot_response = ""

        def log_journey_entry(response_type, rec_count=0):
            try:
                log_data = {
                    'timestamp': datetime.now(),
                    'intent': intent,
                    'user_message': message[:100],
                    'response_type': response_type,
                    'target': final_target,
                    'rec_count': rec_count,
                    'bot_response_preview': str(bot_response)[:50] + "..."
                }
                if db_client:
                    db_client.collection('users').document(user_id).collection('journey_logs').add(log_data)
            except Exception as e:
                print(f"Journey log error: {e}")

        # 5. CONTEXT & MEMORY SETUP
        if intent in ['fitness_variation', 'nutrition_variation']:
            final_target = last_target if last_target else "General"
        elif intent in ['fitness_request', 'nutrition_request']:
            final_target = new_target or "General"
            seen_titles = []
            last_target = final_target

        memory = SimpleMemory(db_client)
        recent_items = []
        if 'fitness' in intent:
            recent_items = memory.get_recent_items(user_id, 'exercises')
        elif 'nutrition' in intent:
            recent_items = memory.get_recent_items(user_id, 'foods')
        ignore_list = list(set(seen_titles + recent_items))

        # 6. GENERATE RESPONSE BASED ON INTENT

        # A. TEXT GENERATION
        text_intents = ['explain_exercise', 'general_chat', 'nutrition_options', 'out_of_scope', 'add_preference',
                        'add_dislike', 'clear_preferences', 'health_inquiry']

        if intent in text_intents:
            bot_response = nlu.generate_response(profile, message, intent)
            log_journey_entry('text_response', 0)

        # B. FITNESS LOGIC
        elif intent in ['fitness_request', 'fitness_variation']:
            raw_recs = recommender.get_recommendations(
                profile,
                intent,
                final_target,
                ignore_list=ignore_list,
                top_k=3,
                likes=likes,
                dislikes=dislikes,
                no_equipment=no_equipment
            )
            recs, warnings = SafetyValidator().filter_exercises_for_injuries(raw_recs,
                                                                             profile.get('medical_conditions', ''))

            if recs:
                for r in recs:
                    seen_titles.append(r.get('Title'))
                    memory.log_interaction(user_id, r.get('Title'), 'exercises')

                bot_response = format_exercise_card(recs, intent, final_target)
                log_journey_entry('fitness_recommendation', len(recs))
            else:
                bot_response = nlu.generate_response(profile, message, 'general_chat')
                log_journey_entry('fitness_fallback', 0)

        # C. NUTRITION LOGIC
        elif intent in ['nutrition_request', 'nutrition_variation']:
            extra_entities = {
                'preference': entities.get('preference'),
                'category': entities.get('category')
            }

            recs = recommender.get_recommendations(
                profile,
                'nutrition_request',
                final_target,
                ignore_list=ignore_list,
                extra_entities=extra_entities,
                top_k=3,
                likes=likes,
                dislikes=dislikes
            )

            filtered_recs = []
            junk_keywords = ['ketchup', 'mayonnaise', 'syrup', 'soda', 'candy', 'chips']
            for item in recs:
                name = item.get('Name', '').lower()
                if any(junk in name for junk in junk_keywords) and 'junk' not in final_target.lower():
                    continue
                filtered_recs.append(item)

            if filtered_recs:
                for r in filtered_recs:
                    seen_titles.append(r.get('Name'))
                    memory.log_interaction(user_id, r.get('Name'), 'foods')

                bot_response = format_nutrition_card(filtered_recs, intent, final_target)
                log_journey_entry('nutrition_recommendation', len(filtered_recs))
            else:
                bot_response = nlu.generate_response(profile, message, 'general_chat')
                log_journey_entry('nutrition_fallback', 0)

        # D. CATCH-ALL BLOCK
        else:
            print(f"Warning: Unhandled intent '{intent}'. Falling back to NLU.")
            bot_response = nlu.generate_response(profile, message, 'general_chat')
            log_journey_entry('fallback_response', 0)

        # 7. SESSION UPDATE
        history.append({"role": "user", "content": message})
        session_data['history'] = history[-6:]
        session_data['seen_titles'] = seen_titles
        session_data['last_target'] = last_target
        session_data['likes'] = likes
        session_data['dislikes'] = dislikes

        return jsonify({"reply": bot_response, "session": session_data, "intent": intent})

    except Exception as e:
        print(f"Endpoint Error: {e}")
        return jsonify({"reply": "I'm having a brief brain freeze. Try again?", "session": {}}), 200



# ============================================
# CONVERSATION HISTORY ENDPOINTS
# ============================================

@app.route('/conversations', methods=['GET'])
def list_conversations():
    """List all conversations for a user."""
    try:
        user_id = request.args.get('user_id')
        if not user_id or not db_client:
            return jsonify({"success": False, "conversations": []})

        convos_ref = db_client.collection('users').document(user_id) \
            .collection('conversations') \
            .order_by('updated_at', direction=firestore.Query.DESCENDING) \
            .limit(20)

        def convert_timestamp(ts):
            """Convert Firestore Timestamp or datetime to ISO string."""
            if ts is None:
                return None
            # Firestore Timestamp object
            if hasattr(ts, 'seconds'):
                return datetime.fromtimestamp(ts.seconds + ts.nanoseconds / 1e9).isoformat()
            # Python datetime object
            if hasattr(ts, 'isoformat'):
                return ts.isoformat()
            # Already a string
            if isinstance(ts, str):
                return ts
            return None

        conversations = []
        for doc in convos_ref.stream():
            data = doc.to_dict()
            conversations.append({
                'id': doc.id,
                'title': data.get('title', 'New Chat'),
                'updated_at': convert_timestamp(data.get('updated_at')),
                'message_count': len(data.get('messages', []))
            })

        return jsonify({"success": True, "conversations": conversations})
    except Exception as e:
        print(f"List conversations error: {e}")
        return jsonify({"success": False, "conversations": []})


@app.route('/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id or not db_client:
            return jsonify({"success": False})

        # Create new conversation document
        now = datetime.now()
        conv_ref = db_client.collection('users').document(user_id) \
            .collection('conversations').document()

        conv_data = {
            'id': conv_ref.id,
            'title': 'New Chat',
            'created_at': now,
            'updated_at': now,
            'messages': [],
            'session': {}
        }
        conv_ref.set(conv_data)

        return jsonify({
            "success": True,
            "conversation": {
                'id': conv_ref.id,
                'title': 'New Chat',
                'updated_at': now.isoformat(),
                'message_count': 0
            }
        })
    except Exception as e:
        print(f"Create conversation error: {e}")
        return jsonify({"success": False})


@app.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Load a specific conversation."""
    try:
        user_id = request.args.get('user_id')
        if not user_id or not db_client:
            return jsonify({"success": False})

        conv_ref = db_client.collection('users').document(user_id) \
            .collection('conversations').document(conversation_id)
        doc = conv_ref.get()

        if not doc.exists:
            return jsonify({"success": False, "error": "Conversation not found"})

        data = doc.to_dict()
        return jsonify({
            "success": True,
            "conversation": {
                'id': doc.id,
                'title': data.get('title', 'New Chat'),
                'messages': data.get('messages', []),
                'session': data.get('session', {})
            }
        })
    except Exception as e:
        print(f"Get conversation error: {e}")
        return jsonify({"success": False})


@app.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id or not db_client:
            return jsonify({"success": False})

        db_client.collection('users').document(user_id) \
            .collection('conversations').document(conversation_id).delete()

        return jsonify({"success": True})
    except Exception as e:
        print(f"Delete conversation error: {e}")
        return jsonify({"success": False})


@app.route('/conversations/<conversation_id>/message', methods=['POST'])
def save_message(conversation_id):
    """Save a message to a conversation."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        role = data.get('role')  # 'user' or 'ai'
        content = data.get('content')

        if not user_id or not db_client or not role or not content:
            return jsonify({"success": False})

        conv_ref = db_client.collection('users').document(user_id) \
            .collection('conversations').document(conversation_id)

        doc = conv_ref.get()
        if not doc.exists:
            return jsonify({"success": False, "error": "Conversation not found"})

        conv_data = doc.to_dict()
        messages = conv_data.get('messages', [])

        # Add new message
        new_message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        messages.append(new_message)

        # Auto-generate title from first user message
        title = conv_data.get('title', 'New Chat')
        if title == 'New Chat' and role == 'user':
            # Use first 40 chars of first message as title
            title = content[:40] + ('...' if len(content) > 40 else '')

        # Update conversation
        conv_ref.update({
            'messages': messages,
            'updated_at': datetime.now(),
            'title': title
        })

        # Also save session if provided
        session = data.get('session')
        if session:
            conv_ref.update({'session': session})

        return jsonify({"success": True, "title": title})
    except Exception as e:
        print(f"Save message error: {e}")
        return jsonify({"success": False})


if __name__ == '__main__':
    # Validate security configuration before starting
    errors = SecurityConfig.validate()
    if errors:
        print("\n⚠️  SECURITY WARNINGS:")
        for error in errors:
            print(f"   - {error}")
        print()
    
    # NEVER use debug=True in production!
    app.run(debug=SecurityConfig.DEBUG, port=5000)