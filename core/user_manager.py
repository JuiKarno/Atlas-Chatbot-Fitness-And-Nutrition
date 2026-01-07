import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserManager:
    def __init__(self, key_path=None):
        """
        Initialize the UserManager with Firebase Firestore connection.
        If key_path is not provided, it looks for 'serviceAccountKey.json' in the project root.
        """
        if not firebase_admin._apps:
            # Determine path to service account key if not provided
            if key_path is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                key_path = os.path.join(base_dir, 'serviceAccountKey.json')

            if os.path.exists(key_path):
                try:
                    cred = credentials.Certificate(key_path)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize Firebase: {e}")
            else:
                logger.warning(f"Service account key not found at {key_path}. Firestore features will be disabled.")

        self.db = firestore.client() if firebase_admin._apps else None

    def get_user(self, user_id):
        """Retrieves user profile data from Firestore."""
        if not self.db:
            return None

        try:
            doc_ref = self.db.collection('users').document(user_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    def create_or_update_user(self, user_id, user_data):
        """
        Creates or updates a user document.
        user_data should be a dictionary (e.g., {'age': 25, 'goal': 'weight_loss', 'name': 'Alex'})
        """
        if not self.db:
            return False

        try:
            doc_ref = self.db.collection('users').document(user_id)
            # Merge=True ensures we don't overwrite existing fields unless specified
            doc_ref.set(user_data, merge=True)
            logger.info(f"User {user_id} updated successfully.")
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    def log_interaction(self, user_id, message, response, intent=None):
        """Logs a chat interaction to the user's history subcollection."""
        if not self.db:
            return

        try:
            interaction = {
                'timestamp': datetime.datetime.now(),
                'user_message': message,
                'bot_response': response,
                'intent': intent
            }
            # Add to a subcollection 'history' under the user
            self.db.collection('users').document(user_id).collection('history').add(interaction)
        except Exception as e:
            logger.error(f"Error logging interaction for {user_id}: {e}")

    def get_user_history(self, user_id, limit=5):
        """Retrieves the last N interactions for context."""
        if not self.db:
            return []

        try:
            history_ref = self.db.collection('users').document(user_id).collection('history')
            query = history_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()

            history = []
            for doc in docs:
                history.append(doc.to_dict())

            # Return in chronological order (oldest to newest)
            return history[::-1]
        except Exception as e:
            logger.error(f"Error fetching history for {user_id}: {e}")
            return []

    # ============================================
    # PROGRESS TRACKING METHODS
    # ============================================

    def add_weight_log(self, user_id, weight, height=None):
        """
        Logs a weight entry and updates the user's profile with the latest weight/BMI.
        Returns the calculated BMI if height is available.
        """
        if not self.db:
            return None

        try:
            # Get user profile to retrieve height if not provided
            profile = self.get_user(user_id) or {}
            if height is None:
                height = profile.get('height')

            # Calculate BMI if height is available
            bmi = None
            if height and height > 0:
                height_m = height / 100
                bmi = round(weight / (height_m * height_m), 1)

            # Create log entry
            log_entry = {
                'timestamp': datetime.datetime.now(),
                'weight': weight,
                'bmi': bmi
            }

            # Add to weight_logs subcollection
            self.db.collection('users').document(user_id).collection('weight_logs').add(log_entry)

            # Update user profile with latest weight and BMI
            profile_update = {'weight': weight}
            if bmi:
                profile_update['bmi'] = bmi
            self.create_or_update_user(user_id, profile_update)

            logger.info(f"Weight log added for user {user_id}: {weight}kg, BMI: {bmi}")
            return {'weight': weight, 'bmi': bmi}

        except Exception as e:
            logger.error(f"Error adding weight log for {user_id}: {e}")
            return None

    def get_weight_logs(self, user_id, days=7):
        """Retrieves weight logs for the last N days."""
        if not self.db:
            return []

        try:
            logs_ref = self.db.collection('users').document(user_id).collection('weight_logs')
            # Get all recent logs without complex timestamp filtering
            query = logs_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(30)

            logs = []
            for doc in query.stream():
                data = doc.to_dict()
                timestamp = data.get('timestamp')
                
                # Handle various timestamp formats
                if timestamp:
                    if hasattr(timestamp, 'strftime'):
                        date_str = timestamp.strftime('%Y-%m-%d')
                    elif hasattr(timestamp, 'to_datetime'):
                        date_str = timestamp.to_datetime().strftime('%Y-%m-%d')
                    else:
                        date_str = str(timestamp)[:10]
                else:
                    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
                
                logs.append({
                    'date': date_str,
                    'weight': data.get('weight'),
                    'bmi': data.get('bmi'),
                    'timestamp': timestamp
                })

            # Return only last N days worth, in chronological order
            return logs[:days][::-1]
        except Exception as e:
            logger.error(f"Error fetching weight logs for {user_id}: {e}")
            return []

    def add_nutrition_log(self, user_id, calories=None, protein=None, carbs=None, fat=None):
        """
        Logs nutrition data for today. Updates today's document with cumulative values.
        Uses YYYY-MM-DD as document ID for daily aggregation.
        """
        if not self.db:
            return None

        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            doc_ref = self.db.collection('users').document(user_id).collection('nutrition_logs').document(today)

            # Get existing data for today
            doc = doc_ref.get()
            if doc.exists:
                existing = doc.to_dict()
            else:
                existing = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'entries': []}

            # Add new values (cumulative)
            new_entry = {'timestamp': datetime.datetime.now().isoformat()}
            if calories is not None:
                existing['calories'] = existing.get('calories', 0) + calories
                new_entry['calories'] = calories
            if protein is not None:
                existing['protein'] = existing.get('protein', 0) + protein
                new_entry['protein'] = protein
            if carbs is not None:
                existing['carbs'] = existing.get('carbs', 0) + carbs
                new_entry['carbs'] = carbs
            if fat is not None:
                existing['fat'] = existing.get('fat', 0) + fat
                new_entry['fat'] = fat

            # Track individual entries
            entries = existing.get('entries', [])
            entries.append(new_entry)
            existing['entries'] = entries
            existing['date'] = today
            existing['last_updated'] = datetime.datetime.now()

            # Save to Firestore
            doc_ref.set(existing)

            logger.info(f"Nutrition log updated for user {user_id} on {today}")
            return existing

        except Exception as e:
            logger.error(f"Error adding nutrition log for {user_id}: {e}")
            return None

    def get_today_nutrition(self, user_id):
        """Gets today's nutrition totals."""
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        default_data = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'date': today}
        
        if not self.db:
            return default_data

        try:
            doc_ref = self.db.collection('users').document(user_id).collection('nutrition_logs').document(today)
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            return default_data

        except Exception as e:
            logger.error(f"Error fetching today's nutrition for {user_id}: {e}")
            return default_data


    def get_nutrition_logs(self, user_id, days=7):
        """Retrieves nutrition logs for the last N days."""
        if not self.db:
            return []

        try:
            logs = []
            for i in range(days):
                date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                doc_ref = self.db.collection('users').document(user_id).collection('nutrition_logs').document(date)
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    data['date'] = date
                    logs.append(data)

            # Return in chronological order
            return logs[::-1]

        except Exception as e:
            logger.error(f"Error fetching nutrition logs for {user_id}: {e}")
            return []

    def add_workout_log(self, user_id, workout_name, exercises=None, duration=None):
        """
        Logs a completed workout session.
        exercises should be a list of dicts: [{'name': 'Bench Press', 'sets': 3, 'reps': 10}, ...]
        """
        if not self.db:
            return None

        try:
            log_entry = {
                'timestamp': datetime.datetime.now(),
                'date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'workout_name': workout_name,
                'exercises': exercises or [],
                'duration': duration
            }

            # Add to workout_logs subcollection
            self.db.collection('users').document(user_id).collection('workout_logs').add(log_entry)

            logger.info(f"Workout log added for user {user_id}: {workout_name}")
            return log_entry

        except Exception as e:
            logger.error(f"Error adding workout log for {user_id}: {e}")
            return None

    def get_workout_logs(self, user_id, days=7):
        """Retrieves workout logs for the last N days."""
        if not self.db:
            return []

        try:
            logs_ref = self.db.collection('users').document(user_id).collection('workout_logs')
            # Get all recent logs without complex timestamp filtering
            query = logs_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20)

            logs = []
            for doc in query.stream():
                data = doc.to_dict()
                timestamp = data.get('timestamp')
                
                # Handle various timestamp formats
                if timestamp:
                    if hasattr(timestamp, 'strftime'):
                        date_str = timestamp.strftime('%Y-%m-%d')
                    elif hasattr(timestamp, 'to_datetime'):
                        date_str = timestamp.to_datetime().strftime('%Y-%m-%d')
                    else:
                        date_str = str(timestamp)[:10]
                else:
                    date_str = data.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))
                
                logs.append({
                    'date': date_str,
                    'workout_name': data.get('workout_name'),
                    'exercises': data.get('exercises', []),
                    'duration': data.get('duration'),
                    'timestamp': timestamp
                })

            # Return only last N days worth, in chronological order
            return logs[:days][::-1]

        except Exception as e:
            logger.error(f"Error fetching workout logs for {user_id}: {e}")
            return []

    # ============================================
    # FAVORITES & FEEDBACK METHODS
    # ============================================

    def add_favorite(self, user_id, item_data, item_type='exercise'):
        """Saves a favorited item to the user's favorites collection."""
        if not self.db:
            return False
        try:
            # Create a unique ID for the favorite based on the item name/title
            item_name = item_data.get('Title') or item_data.get('Name')
            if not item_name:
                return False
                
            fav_id = item_name.lower().replace(" ", "_")
            doc_ref = self.db.collection('users').document(user_id).collection('favorites').document(fav_id)
            
            # Add timestamp
            item_data['saved_at'] = datetime.datetime.now()
            item_data['item_type'] = item_type
            
            doc_ref.set(item_data, merge=True)
            logger.info(f"Item '{item_name}' added to favorites for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding favorite for {user_id}: {e}")
            return False

    def get_favorites(self, user_id):
        """Retrieves all favorite items for a user."""
        if not self.db:
            return {'exercises': [], 'nutrition': []}
        try:
            favs_ref = self.db.collection('users').document(user_id).collection('favorites')
            docs = favs_ref.order_by('saved_at', direction=firestore.Query.DESCENDING).stream()
            
            exercises = []
            nutrition = []
            
            for doc in docs:
                data = doc.to_dict()
                # Remove timestamp for JSON serializability
                if 'saved_at' in data and hasattr(data['saved_at'], 'isoformat'):
                    data['saved_at'] = data['saved_at'].isoformat()
                
                if data.get('item_type') == 'exercise' or 'Title' in data:
                    exercises.append(data)
                else:
                    nutrition.append(data)
                    
            return {'exercises': exercises, 'nutrition': nutrition}
        except Exception as e:
            logger.error(f"Error fetching favorites for {user_id}: {e}")
            return {'exercises': [], 'nutrition': []}

    def add_to_ignore_list(self, user_id, item_name):
        """Adds an item to the user's permanent ignore list (dislikes)."""
        if not self.db:
            return False
        try:
            doc_ref = self.db.collection('users').document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                profile = doc.to_dict()
                ignore_list = profile.get('ignore_list', [])
                if item_name.lower() not in [x.lower() for x in ignore_list]:
                    ignore_list.append(item_name.lower())
                    doc_ref.update({'ignore_list': ignore_list})
            else:
                doc_ref.set({'ignore_list': [item_name.lower()]}, merge=True)
                
            logger.info(f"Item '{item_name}' added to ignore list for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding to ignore list for {user_id}: {e}")
            return False

    # ============================================
    # PROGRESS TRACKING METHODS
    # ============================================

    def log_weight(self, user_id, weight):
        """Logs a weight entry for the user."""
        if not self.db: return False
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('weight_logs').document()
            doc_ref.set({
                'weight': float(weight),
                'date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'timestamp': datetime.datetime.now()
            })
            # Also update current profile weight
            self.db.collection('users').document(user_id).update({'weight': float(weight)})
            return True
        except Exception as e:
            logger.error(f"Error logging weight: {e}")
            return False

    def log_nutrition(self, user_id, data):
        """Logs a nutrition entry (calories, macros)."""
        if not self.db: return False
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('nutrition_logs').document()
            data['date'] = datetime.datetime.now().strftime('%Y-%m-%d')
            data['timestamp'] = datetime.datetime.now()
            doc_ref.set(data)
            return True
        except Exception as e:
            logger.error(f"Error logging nutrition: {e}")
            return False

    def get_progress_logs(self, user_id, log_type='weight', days=7):
        """Retrieves progress logs (weight or nutrition) for the last N days."""
        if not self.db: return []
        try:
            coll_name = 'weight_logs' if log_type == 'weight' else 'nutrition_logs'
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            
            ref = self.db.collection('users').document(user_id).collection(coll_name)
            query = ref.where(filter=FieldFilter('timestamp', '>=', cutoff)).order_by('timestamp', direction=firestore.Query.ASCENDING)
            
            logs = [d.to_dict() for d in query.stream()]
            return logs
        except Exception as e:
            logger.error(f"Error fetching progress logs: {e}")
            return []
