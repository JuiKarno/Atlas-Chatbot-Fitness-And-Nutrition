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