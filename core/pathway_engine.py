from datetime import datetime, timedelta
import random


class PathwayEngine:
    def __init__(self, db_client):
        self.db = db_client

    def generate_30_day_pathway(self, profile):
        """Generates a personalized 30-day transformation pathway."""
        goal = profile.get('goal', 'Maintenance')
        level = profile.get('fitness_level', 'Beginner')
        conditions = profile.get('medical_conditions', '').lower()

        # 1. Select the base template based on Goal
        if goal == 'Weight Loss':
            pathway = self._weight_loss_pathway(level, conditions)
        elif goal == 'Muscle Gain':
            pathway = self._muscle_gain_pathway(level, conditions)
        else:
            pathway = self._maintenance_pathway(level, conditions)

        # 2. Personalize based on specific user stats (Age, BMI)
        personalized_pathway = self._personalize_pathway(pathway, profile)

        # 3. Generate the specific day-by-day schedule
        daily_plan = self._create_daily_plan(personalized_pathway)

        # 4. Return the complete object to be saved to Firestore
        return {
            'pathway_id': f"path_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'goal': goal,
            'level': level,
            'duration_days': 30,
            'start_date': datetime.now().date().isoformat(),
            'daily_plan': daily_plan,
            'milestones': self._generate_milestones(goal, level),
            'nutrition_guidelines': self._get_nutrition_guidelines(goal)
        }

    # --- TEMPLATES ---

    def _weight_loss_pathway(self, level, conditions):
        base = {
            'goal': 'Weight Loss',
            'focus': 'Calorie deficit + consistent movement',
            'weekly_structure': {
                'strength_days': 3 if 'knee' not in conditions else 2,
                'cardio_days': 4,
                'active_recovery_days': 1
            },
            'progression': 'Increase cardio duration by 5 mins each week',
            'key_exercises': self._get_joint_friendly_exercises(conditions),
        }
        if level == 'Beginner':
            base['weekly_structure']['strength_days'] = 2
            base['weekly_structure']['cardio_days'] = 3
        return base

    def _muscle_gain_pathway(self, level, conditions):
        base = {
            'goal': 'Muscle Gain',
            'focus': 'Hypertrophy and progressive overload',
            'weekly_structure': {
                'strength_days': 4,
                'cardio_days': 2,
                'active_recovery_days': 1
            },
            'progression': 'Increase weight or reps every session',
            'key_exercises': self._get_joint_friendly_exercises(conditions),
        }
        if level == 'Beginner':
            base['weekly_structure']['strength_days'] = 3
        return base

    def _maintenance_pathway(self, level, conditions):
        return {
            'goal': 'Maintenance',
            'focus': 'General health and mobility',
            'weekly_structure': {
                'strength_days': 3,
                'cardio_days': 3,
                'active_recovery_days': 1
            },
            'progression': 'Maintain consistency and form',
            'key_exercises': self._get_joint_friendly_exercises(conditions),
        }

    # --- PERSONALIZATION LOGIC ---

    def _personalize_pathway(self, pathway, profile):
        """Adjusts the pathway intensity based on age and BMI."""
        age = profile.get('age', 25)
        bmi = profile.get('bmi', 22.0)

        # Senior logic
        if age > 50:
            pathway['focus'] += " (Low Impact Focus)"
            pathway['progression'] = "Gradual volume increase"

        # BMI logic
        if bmi > 30 and pathway['goal'] == 'Weight Loss':
            pathway['weekly_structure']['cardio_days'] += 1
            pathway['focus'] += " (Walking based cardio)"

        return pathway

    def _get_joint_friendly_exercises(self, conditions):
        safe_exercises = {
            'general': ['Squats', 'Pushups', 'Lunges', 'Plank'],
            'knee': ['Glute Bridges', 'Clamshells', 'Swimming', 'Upper Body Press'],
            'back': ['Walking', 'Cat-Cow', 'Bird-Dog', 'Wall Sits'],
            'shoulder': ['Leg Press', 'Squats', 'Bicep Curls', 'Tricep Pushdowns']
        }
        for condition, exercises in safe_exercises.items():
            if condition in conditions:
                return exercises
        return safe_exercises['general']

    # --- DAILY GENERATION ---

    def _create_daily_plan(self, pathway):
        daily_plan = []
        start_date = datetime.now().date()

        # Get the workout rotation based on the goal
        rotation = self._get_weekly_rotation(pathway['goal'])

        for day in range(1, 31):
            current_date = start_date + timedelta(days=day - 1)

            # Use modulo to cycle through the 7-day rotation
            day_template = rotation[(day - 1) % 7]

            # Apply Progressive Overload: Add duration in later weeks
            week_num = ((day - 1) // 7) + 1
            duration = day_template['duration']
            if week_num > 1 and day_template['type'] in ['Cardio', 'Strength']:
                duration += 5

            plan_day = {
                'day': day,
                'date': current_date.isoformat(),
                'focus': day_template['focus'],
                'workout_type': day_template['type'],
                'estimated_duration': duration,
                'intensity': day_template['intensity'],
                'nutrition_focus': self._get_daily_nutrition_focus(day, pathway['goal']),
                'recovery_tips': self._get_recovery_tip(),
                'completed': False
            }
            daily_plan.append(plan_day)

        return daily_plan

    def _get_weekly_rotation(self, goal):
        """Returns a 7-day list of workout types based on goal."""
        if goal == 'Weight Loss':
            return [
                {'type': 'Strength', 'focus': 'Full Body', 'duration': 40, 'intensity': 'Medium'},
                {'type': 'Cardio', 'focus': 'Steady State', 'duration': 30, 'intensity': 'Low'},
                {'type': 'Strength', 'focus': 'Upper Body', 'duration': 40, 'intensity': 'Medium'},
                {'type': 'Cardio', 'focus': 'Intervals', 'duration': 20, 'intensity': 'High'},
                {'type': 'Strength', 'focus': 'Lower Body', 'duration': 40, 'intensity': 'High'},
                {'type': 'Active Recovery', 'focus': 'Yoga/Walk', 'duration': 30, 'intensity': 'Low'},
                {'type': 'Rest', 'focus': 'Recovery', 'duration': 0, 'intensity': 'None'}
            ]
        elif goal == 'Muscle Gain':
            return [
                {'type': 'Strength', 'focus': 'Push (Chest/Tri)', 'duration': 50, 'intensity': 'High'},
                {'type': 'Strength', 'focus': 'Pull (Back/Bi)', 'duration': 50, 'intensity': 'High'},
                {'type': 'Strength', 'focus': 'Legs', 'duration': 50, 'intensity': 'High'},
                {'type': 'Active Recovery', 'focus': 'Mobility', 'duration': 20, 'intensity': 'Low'},
                {'type': 'Strength', 'focus': 'Upper Body', 'duration': 50, 'intensity': 'Medium'},
                {'type': 'Strength', 'focus': 'Lower Body', 'duration': 50, 'intensity': 'Medium'},
                {'type': 'Rest', 'focus': 'Sleep', 'duration': 0, 'intensity': 'None'}
            ]
        else:  # Maintenance
            return [
                {'type': 'Strength', 'focus': 'Full Body', 'duration': 30, 'intensity': 'Medium'},
                {'type': 'Cardio', 'focus': 'Walk/Run', 'duration': 30, 'intensity': 'Medium'},
                {'type': 'Active Recovery', 'focus': 'Stretch', 'duration': 15, 'intensity': 'Low'},
                {'type': 'Strength', 'focus': 'Full Body', 'duration': 30, 'intensity': 'Medium'},
                {'type': 'Cardio', 'focus': 'Mix', 'duration': 30, 'intensity': 'Medium'},
                {'type': 'Active Recovery', 'focus': 'Fun Activity', 'duration': 45, 'intensity': 'Low'},
                {'type': 'Rest', 'focus': 'Relax', 'duration': 0, 'intensity': 'None'}
            ]

    # --- EXTRAS ---

    def _generate_milestones(self, goal, level):
        if goal == 'Weight Loss':
            return ["Day 7: Complete all cardio", "Day 14: Track calories perfectly", "Day 30: Re-weigh"]
        elif goal == 'Muscle Gain':
            return ["Day 7: Hit protein goal", "Day 14: Increase lift weight", "Day 30: Progress photo"]
        return ["Day 15: Halfway check-in", "Day 30: Completion"]

    def _get_nutrition_guidelines(self, goal):
        if goal == 'Weight Loss': return "Aim for a 300-500 calorie deficit. High protein."
        if goal == 'Muscle Gain': return "Slight surplus (+250 cal). High protein (2g/kg)."
        return "Maintenance calories. Whole foods focus."

    def _get_daily_nutrition_focus(self, day, goal):
        tips = ["Hydrate before meals", "Eat protein with breakfast", "Eat veggies first", "No late night snacks",
                "Try a new healthy recipe"]
        return random.choice(tips)

    def _get_recovery_tip(self):
        tips = ["Sleep 7-8 hours", "Stretch for 10 mins", "Foam roll legs", "Take a cold shower",
                "Practice deep breathing"]
        return random.choice(tips)