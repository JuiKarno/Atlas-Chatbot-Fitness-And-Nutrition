from datetime import datetime, timedelta
from google.cloud.firestore import Query, FieldFilter


class SimpleMemory:
    def __init__(self, db_client):
        self.db = db_client

    def log_interaction(self, user_id, item_title, category):
        """Logs a recommended item to avoid immediate repetition."""
        if not self.db: return

        try:
            self.db.collection('users').document(user_id).collection('recent_recommendations').add({
                'title': item_title,
                'category': category,  # 'exercises' or 'foods'
                'timestamp': datetime.now()
            })
        except Exception as e:
            print(f"Memory Log Error: {e}")

    def get_recent_items(self, user_id, category, limit=20):
        """Retrieves recently recommended items to filter them out."""
        if not self.db: return []

        try:
            # Get items from last 24 hours to keep things fresh but not repetitive
            cutoff = datetime.now() - timedelta(days=1)

            docs = self.db.collection('users').document(user_id).collection('recent_recommendations') \
                .where(filter=FieldFilter('category', '==', category)) \
                .order_by('timestamp', direction=Query.DESCENDING) \
                .limit(limit) \
                .stream()

            return [doc.to_dict().get('title') for doc in docs]
        except Exception as e:
            print(f"Memory Fetch Error: {e}")
            return []