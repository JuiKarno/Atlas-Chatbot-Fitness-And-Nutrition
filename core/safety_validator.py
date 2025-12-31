class SafetyValidator:
    @staticmethod
    def validate_request(user_profile):
        """
        Analyzes user profile for safety risks and provides contextual advice.
        Returns: (is_safe: bool, message: str)
        """
        # Default values to safe ranges if missing
        age = int(user_profile.get('age', 25))
        bmi = float(user_profile.get('bmi', 22))
        goal = user_profile.get('goal', 'General Fitness')

        # 1. Age Restriction (COPPA/Safety) - Strict 18+
        if age < 18:
            return False, "⚠️ <b>Age Restriction:</b> Atlas is strictly designed for adults (18+). Please consult a real-life coach or guardian for advice suitable for your age group."

        # 2. BMI Context-Aware Advice

        # Scenario A: Underweight trying to Lose Weight
        if bmi < 18.5 and ('Loss' in goal or 'Cut' in goal):
            return False, (
                f"⚠️ <b>Health Alert:</b> Your BMI is <b>{bmi}</b>, which indicates you may be underweight.<br><br>"
                "It is generally <b>not recommended</b> to pursue weight loss in this range. "
                "I strongly advise focusing on <b>Muscle Gain</b> or <b>Healthy Maintenance</b> to build strength safely.<br><br>"
                "Would you like me to switch your goal to 'Muscle Gain' for today?"
            )

        # Scenario B: Class II Obesity trying to "Bulk" (Pure Muscle Gain without Fat Loss consideration)
        if bmi > 35 and ('Muscle' in goal or 'Gain' in goal) and 'Loss' not in goal:
            return False, (
                f"⚠️ <b>Health Advice:</b> Your BMI is <b>{bmi}</b>. While building muscle is great, "
                "adding more mass (bulking) might put extra stress on your joints and heart right now.<br><br>"
                "I recommend a <b>'Body Recomposition'</b> approach (losing fat while keeping muscle) or consulting a medical professional "
                "to ensure your heart health is managed first.<br><br>"
                "Shall we look at some low-impact exercises instead?"
            )

        # Scenario C: Severe Underweight (Critical Safety)
        if bmi < 16:
            return False, (
                f"🛑 <b>Medical Consultation Required:</b> Your BMI is <b>{bmi}</b>. "
                "For your safety, I cannot generate a fitness plan. Please consult a doctor or a registered dietitian "
                "to ensure you are getting the right nutrition for recovery."
            )

        return True, ""

    @staticmethod
    def get_disclaimer(exercise_type):
        """Returns HTML warnings for specific exercise types."""
        if exercise_type == 'Plyometrics':
            return "<span class='text-xs text-orange-600 block mt-2'><i class='fas fa-exclamation-triangle'></i> High Impact: Ensure proper footwear.</span>"
        if exercise_type == 'Olympic Weightlifting':
            return "<span class='text-xs text-blue-600 block mt-2'><i class='fas fa-info-circle'></i> Technical Lift: Start with light weights.</span>"
        return ""

    # Add to your existing SafetyValidator class in safety_validator.py
    def filter_exercises_for_injuries(self, exercises_list, medical_conditions_str):
        """
        Filters out unsafe exercises based on medical conditions.
        Returns: (filtered_list, warnings)
        """
        if not medical_conditions_str:
            return exercises_list, []

        conditions = medical_conditions_str.lower()
        warnings = []
        safe_exercises = []

        # Define injury-to-exercise risk mappings
        risk_keywords = {
            'knee': ['squat', 'lunge', 'leg press', 'jump', 'run', 'plyo'],
            'back': ['deadlift', 'good morning', 'bent over', 'back extension'],
            'shoulder': ['overhead press', 'snatch', 'handstand', 'bench press'],
            'wrist': ['push-up', 'handstand', 'clean', 'front rack']
        }

        for exercise in exercises_list:
            ex_title = exercise.get('Title', '').lower()
            ex_desc = exercise.get('Desc', '').lower()
            ex_type = exercise.get('Type', '').lower()

            is_unsafe = False

            # Check each condition the user has
            for condition, risky_terms in risk_keywords.items():
                if condition in conditions:
                    for risky_word in risky_terms:
                        if risky_word in ex_title or risky_word in ex_desc:
                            is_unsafe = True
                            warnings.append(f"Removed '{ex_title}' due to {condition} condition")
                            break
                if is_unsafe:
                    break

            # Additional rule: High impact for knee issues
            if 'knee' in conditions and ex_type == 'plyometrics':
                is_unsafe = True
                warnings.append(f"Removed plyometric '{ex_title}' for knee safety")

            if not is_unsafe:
                safe_exercises.append(exercise)

        # If we filtered EVERYTHING, return at least the first one with a warning
        if not safe_exercises and exercises_list:
            safe_exercises = [exercises_list[0]]
            warnings.append("OVERFILTER WARNING: All exercises flagged. Showing one with caution.")

        return safe_exercises, warnings

    # Add to your existing SafetyValidator class in safety_validator.py
    def filter_exercises_for_injuries(self, exercises_list, medical_conditions_str):
        """
        Filters out unsafe exercises based on medical conditions.
        Returns: (filtered_list, warnings)
        """
        if not medical_conditions_str:
            return exercises_list, []

        conditions = medical_conditions_str.lower()
        warnings = []
        safe_exercises = []

        # Define injury-to-exercise risk mappings
        risk_keywords = {
            'knee': ['squat', 'lunge', 'leg press', 'jump', 'run', 'plyo'],
            'back': ['deadlift', 'good morning', 'bent over', 'back extension'],
            'shoulder': ['overhead press', 'snatch', 'handstand', 'bench press'],
            'wrist': ['push-up', 'handstand', 'clean', 'front rack']
        }

        for exercise in exercises_list:
            ex_title = exercise.get('Title', '').lower()
            ex_desc = exercise.get('Desc', '').lower()
            ex_type = exercise.get('Type', '').lower()

            is_unsafe = False

            # Check each condition the user has
            for condition, risky_terms in risk_keywords.items():
                if condition in conditions:
                    for risky_word in risky_terms:
                        if risky_word in ex_title or risky_word in ex_desc:
                            is_unsafe = True
                            warnings.append(f"Removed '{ex_title}' due to {condition} condition")
                            break
                if is_unsafe:
                    break

            # Additional rule: High impact for knee issues
            if 'knee' in conditions and ex_type == 'plyometrics':
                is_unsafe = True
                warnings.append(f"Removed plyometric '{ex_title}' for knee safety")

            if not is_unsafe:
                safe_exercises.append(exercise)

        # If we filtered EVERYTHING, return at least the first one with a warning
        if not safe_exercises and exercises_list:
            safe_exercises = [exercises_list[0]]
            warnings.append("OVERFILTER WARNING: All exercises flagged. Showing one with caution.")

        return safe_exercises, warnings