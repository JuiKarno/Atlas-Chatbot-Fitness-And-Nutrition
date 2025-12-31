from datetime import datetime, timedelta
from google.cloud.firestore import Query


class PredictiveEngine:
    def __init__(self, db_client):
        self.db = db_client

    def predict_next_workout_time(self, user_id):
        """Predicts when user will likely work out next based on history."""
        try:
            if not self.db:
                return self._default_prediction()

            # Query Firestore for recent logs
            logs_ref = self.db.collection('users').document(user_id) \
                .collection('journey_logs') \
                .order_by('timestamp', direction=Query.DESCENDING) \
                .limit(30)

            logs = [doc.to_dict() for doc in logs_ref.stream()]

            # Match actual fitness intents used in app.py
            fitness_intents = ['fitness_request', 'fitness_variation']
            workout_hours = []

            for log in logs:
                intent = log.get('intent', '')
                if intent in fitness_intents:
                    timestamp = log.get('timestamp')
                    hour = self._extract_hour(timestamp)
                    if hour is not None:
                        workout_hours.append(hour)

            # Default response for new users
            if not workout_hours:
                return self._default_prediction()

            # Find most common hour
            hour_counts = {}
            for hour in workout_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1

            common_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
            confidence = hour_counts[common_hour] / len(workout_hours)
            time_of_day = self._hour_to_time_of_day(common_hour)

            return {
                'predicted_time': time_of_day,
                'common_hour': common_hour,
                'confidence': round(confidence, 2),
                'message': f"You usually work out in the {time_of_day} ({common_hour}:00). Ready to crush it today?"
            }
        except Exception as e:
            print(f"Predictive Error: {e}")
            return self._default_prediction()

    def detect_plateau_risk(self, user_id):
        """Detects if user is requesting too many variations (sign of boredom/plateau)."""
        try:
            if not self.db:
                return {'risk_level': 'low', 'message': '', 'suggestion': ''}

            # Simple query without composite index requirement
            logs_ref = self.db.collection('users').document(user_id) \
                .collection('journey_logs') \
                .order_by('timestamp', direction=Query.DESCENDING) \
                .limit(50)

            variation_intents = ['fitness_variation', 'nutrition_variation']
            seven_days_ago = datetime.now() - timedelta(days=7)
            count = 0

            for doc in logs_ref.stream():
                log = doc.to_dict()
                # Filter by intent in Python (avoids composite index)
                if log.get('intent') in variation_intents:
                    timestamp = log.get('timestamp')
                    # Check if within last 7 days
                    if self._is_recent(timestamp, seven_days_ago):
                        count += 1

            if count >= 5:
                return {
                    'risk_level': 'high',
                    'message': "I've noticed you're switching things up frequently. Want me to create a fresh 30-day plan?",
                    'suggestion': 'Generate my plan'
                }
            elif count >= 2:
                return {
                    'risk_level': 'medium',
                    'message': 'Looking for variety? I can suggest a completely different workout style!',
                    'suggestion': 'Try something new'
                }
            return {'risk_level': 'low', 'message': '', 'suggestion': ''}
        except Exception as e:
            print(f"Plateau detection error: {e}")
            return {'risk_level': 'low', 'message': '', 'suggestion': ''}

    def suggest_proactive_message(self, user_id, profile):
        """Aggregates predictions to return the best suggestion."""
        suggestions = []

        # 1. Workout Prediction
        pred_workout = self.predict_next_workout_time(user_id)
        if pred_workout.get('confidence', 0) > 0.3:
            suggestions.append(pred_workout['message'])

        # 2. Plateau Risk
        pred_plateau = self.detect_plateau_risk(user_id)
        if pred_plateau.get('risk_level') in ['high', 'medium']:
            suggestions.append(pred_plateau['message'])

        # 3. Goal-based fallback for new users or low data
        if not suggestions:
            goal = profile.get('goal', '')
            suggestions.extend(self._get_goal_suggestions(goal))

        return suggestions

    # --- HELPER METHODS ---

    def _default_prediction(self):
        """Returns default prediction for new users or errors."""
        return {
            'predicted_time': 'evening',
            'common_hour': 18,
            'confidence': 0.0,
            'message': ''
        }

    def _extract_hour(self, timestamp):
        """Extract hour from various timestamp formats."""
        if timestamp is None:
            return None
        # Firestore Timestamp object
        if hasattr(timestamp, 'hour'):
            return timestamp.hour
        # If it has a to_datetime method (Firestore Timestamp)
        if hasattr(timestamp, 'to_datetime'):
            return timestamp.to_datetime().hour
        # ISO string format
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).hour
            except:
                return None
        # Python datetime
        if isinstance(timestamp, datetime):
            return timestamp.hour
        return None

    def _hour_to_time_of_day(self, hour):
        """Convert hour to time of day string."""
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 22:
            return 'evening'
        return 'night'

    def _is_recent(self, timestamp, cutoff):
        """Check if timestamp is more recent than cutoff."""
        if timestamp is None:
            return False
        # Firestore Timestamp with to_datetime
        if hasattr(timestamp, 'to_datetime'):
            return timestamp.to_datetime() > cutoff
        # Firestore Timestamp with timestamp() method
        if hasattr(timestamp, 'timestamp'):
            return datetime.fromtimestamp(timestamp.timestamp()) > cutoff
        # ISO string format
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.replace(tzinfo=None) > cutoff
            except:
                return False
        # Python datetime
        if isinstance(timestamp, datetime):
            return timestamp.replace(tzinfo=None) > cutoff
        return False

    def _get_goal_suggestions(self, goal):
        """Get goal-based suggestions for new users."""
        goal_suggestions = {
            'Weight Loss': ["Ready for a calorie-burning session today?"],
            'Muscle Gain': ["Time to hit those gains! Want a workout suggestion?"],
            'Maintenance': ["Let's keep you on track today!"]
        }
        return goal_suggestions.get(goal, [])