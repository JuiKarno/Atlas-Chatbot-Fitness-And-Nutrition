import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import os

# --- CONFIG & CORE IMPORTS ---
from config.settings import Config
from core.nlu_engine import SmartNLUEngine
from core.recommender import ContentBasedRecommender
from core.user_manager import UserManager
from core.safety_validator import SafetyValidator
from core.simple_memory import SimpleMemory

# Helpers
from core.response_formatter import format_exercise_card, format_nutrition_card
from core.calculator import calculate_bmi, calculate_target_calories

# --- FIREBASE INIT ---
if not firebase_admin._apps:
    key_path = Config.FIREBASE_CREDENTIALS if hasattr(Config, 'FIREBASE_CREDENTIALS') else 'serviceAccountKey.json'
    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    else:
        print("Warning: serviceAccountKey.json not found.")

db_client = firestore.client() if firebase_admin._apps else None

app = Flask(__name__)
CORS(app)

# --- ENGINE INIT ---
nlu = SmartNLUEngine()
recommender = ContentBasedRecommender()
user_manager = UserManager(db_client)


# --- ROUTES ---
@app.route('/')
def login_page():
    return render_template('auth.html')


@app.route('/chat')
def chat_page():
    return render_template('chatbot.html')


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


@app.route('/get-recommendation', methods=['POST'])
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

        # Process Likes
        if intent == 'add_preference':
            for item in pref_list:
                clean_item = item.lower().strip()
                if clean_item not in likes: likes.append(clean_item)
                if clean_item in dislikes: dislikes.remove(clean_item)

        # Process Dislikes
        elif intent == 'add_dislike':
            # Also check the singular pref_item here if intent matches
            if pref_item: dislike_list.append(pref_item)

            for item in dislike_list:
                clean_item = item.lower().strip()
                if clean_item not in dislikes: dislikes.append(clean_item)
                if clean_item in likes: likes.remove(clean_item)

        # Clear Preferences
        elif intent == 'clear_preferences':
            likes = []
            dislikes = []

        # Define health-related intents that require profile access
        health_intents = [
            'fitness_request', 'fitness_variation',
            'nutrition_request', 'nutrition_variation',
            'explain_exercise', 'nutrition_recipe'
        ]

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
                dislikes=dislikes
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
    app.run(debug=True, port=5000)