import pandas as pd
import numpy as np
import re
import json
from typing import Dict, List, Any
import hashlib


class FitnessDataProcessor:
    """Transforms raw fitness data into intelligent exercise database."""

    def __init__(self):
        # Movement pattern classification
        self.movement_patterns = {
            'push': ['press', 'push', 'bench', 'chest', 'shoulder', 'tricep', 'dip'],
            'pull': ['row', 'pull', 'lat', 'back', 'bicep', 'chin', 'shrug'],
            'hinge': ['deadlift', 'good morning', 'hip thrust', 'kettlebell swing'],
            'squat': ['squat', 'lunge', 'leg press', 'hack squat', 'bulgarian'],
            'core': ['crunch', 'plank', 'situp', 'leg raise', 'russian twist', 'wood chop'],
            'cardio': ['run', 'jog', 'sprint', 'cycle', 'row', 'jump', 'burpee']
        }

        # Joint impact assessment
        self.high_impact_keywords = ['jump', 'plyo', 'hop', 'bound', 'skip', 'sprint', 'burpee']
        self.knee_risky = ['squat', 'lunge', 'step', 'jump', 'run', 'plyo']
        self.back_risky = ['deadlift', 'good morning', 'bent over', 'back extension', 'snatch']
        self.shoulder_risky = ['overhead', 'handstand', 'snatch', 'clean', 'behind neck']

        # Equipment classification
        self.equipment_levels = {
            'bodyweight': ['Body Only', 'None', 'Bodyweight'],
            'minimal': ['Dumbbell', 'Kettlebell', 'Resistance Band', 'Medicine Ball'],
            'gym': ['Barbell', 'Machine', 'Cable', 'Smith Machine', 'EZ Curl Bar']
        }

    def process_raw_data(self, raw_df: pd.DataFrame) -> List[Dict]:
        """Main processing pipeline for fitness data."""
        print(f"📊 Processing {len(raw_df)} raw exercises...")

        # 1. Clean and standardize
        df = self._clean_data(raw_df)

        # 2. Enrich with intelligent fields
        df = self._enrich_exercises(df)

        # 3. Categorize for personalization
        df = self._categorize_exercises(df)

        # 4. Generate unique IDs
        df['exercise_id'] = df.apply(self._generate_exercise_id, axis=1)

        # 5. Convert to Firestore-ready format
        processed_exercises = []
        for _, row in df.iterrows():
            exercise = self._create_exercise_object(row)
            processed_exercises.append(exercise)

        print(
            f"✅ Processed {len(processed_exercises)} exercises with {len(df['movement_pattern'].unique())} movement patterns")
        return processed_exercises

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize raw data."""
        # Standardize column names
        column_map = {
            'exercise': 'Title', 'name': 'Title', 'Exercise Name': 'Title',
            'body_part': 'Bodypart', 'target': 'Bodypart', 'muscle': 'Bodypart', 'BodyPart': 'Bodypart',
            'description': 'Desc', 'instructions': 'Desc',
            'difficulty': 'Level', 'experience': 'Level',
            'equipment_needed': 'Equipment', 'tools': 'Equipment'
        }

        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

        # Ensure required columns exist
        required = ['Title', 'Bodypart', 'Level', 'Desc']
        for col in required:
            if col not in df.columns:
                df[col] = ''

        # Clean text fields
        if 'Title' in df.columns:
            df['Title'] = df['Title'].astype(str).str.title().str.strip()

        if 'Bodypart' in df.columns:
            df['Bodypart'] = df['Bodypart'].astype(str).str.title().str.strip()
            # Standardize body part names
            bodypart_map = {
                'Abdominals': 'Abs', 'Abdominal': 'Abs',
                'Quadriceps': 'Quads', 'Hamstrings': 'Hamstrings',
                'Glutes': 'Glutes', 'Calves': 'Calves',
                'Pectorals': 'Chest', 'Chest': 'Chest',
                'Lats': 'Back', 'Back': 'Back', 'Traps': 'Back', 'Middle Back': 'Back', 'Lower Back': 'Back',
                'Deltoids': 'Shoulders', 'Shoulders': 'Shoulders',
                'Biceps': 'Biceps', 'Triceps': 'Triceps',
                'Forearms': 'Forearms'
            }
            # Use map but keep original if not found
            df['Bodypart'] = df['Bodypart'].map(bodypart_map).fillna(df['Bodypart'])

        if 'Level' in df.columns:
            df['Level'] = df['Level'].astype(str).str.capitalize()
            level_map = {
                'Novice': 'Beginner',
                'Amateur': 'Intermediate',
                'Expert': 'Advanced',
                'Pro': 'Advanced'
            }

            # FIX: Use replace to map specific terms while preserving others (like 'Beginner')
            df['Level'] = df['Level'].replace(level_map)

            # Ensure only valid levels exist, default to Intermediate for unknowns
            valid_levels = ['Beginner', 'Intermediate', 'Advanced']
            df.loc[~df['Level'].isin(valid_levels), 'Level'] = 'Intermediate'

        # Fill missing descriptions
        if 'Desc' in df.columns:
            df['Desc'] = df['Desc'].fillna('').astype(str)
            mask = (df['Desc'].str.len() < 10) | (df['Desc'].isna())
            df.loc[mask, 'Desc'] = df.apply(
                lambda x: f"{x['Title']} is a {x.get('Type', 'strength')} exercise targeting the {x['Bodypart']}.",
                axis=1
            )

        # Add Type if missing
        if 'Type' not in df.columns:
            df['Type'] = 'Strength'  # Default

        return df

    def _enrich_exercises(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add intelligent fields for personalization and safety."""

        # Determine movement pattern
        def get_movement_pattern(title, desc):
            combined = f"{title} {desc}".lower()
            for pattern, keywords in self.movement_patterns.items():
                if any(keyword in combined for keyword in keywords):
                    return pattern.capitalize()
            return 'General'

        df['movement_pattern'] = df.apply(
            lambda x: get_movement_pattern(x['Title'], x['Desc']), axis=1
        )

        # Assess joint impact
        def assess_joint_impact(title, desc):
            combined = f"{title} {desc}".lower()

            # High impact detection
            if any(keyword in combined for keyword in self.high_impact_keywords):
                return 'High'

            # Medium impact for compound lifts
            compound_keywords = ['squat', 'deadlift', 'bench', 'press', 'clean', 'snatch']
            if any(keyword in combined for keyword in compound_keywords):
                return 'Medium'

            return 'Low'

        df['joint_impact'] = df.apply(
            lambda x: assess_joint_impact(x['Title'], x['Desc']), axis=1
        )

        # Safety flags for common injuries
        def get_safety_flags(title, desc):
            combined = f"{title} {desc}".lower()
            flags = {}

            # Knee safety
            flags['knee_friendly'] = not any(keyword in combined for keyword in self.knee_risky)

            # Back safety
            flags['back_friendly'] = not any(keyword in combined for keyword in self.back_risky)

            # Shoulder safety
            flags['shoulder_friendly'] = not any(keyword in combined for keyword in self.shoulder_risky)

            # Beginner friendly
            beginner_unfriendly = ['plyometric', 'explosive', 'max', 'heavy', '1RM']
            flags['beginner_friendly'] = not any(keyword in combined for keyword in beginner_unfriendly)

            return flags

        # Apply safety flags
        safety_results = df.apply(lambda x: get_safety_flags(x['Title'], x['Desc']), axis=1)
        safety_df = pd.json_normalize(safety_results)
        df = pd.concat([df, safety_df], axis=1)

        # Equipment accessibility
        def get_equipment_accessibility(equipment):
            if not isinstance(equipment, str):
                return 'gym'

            equipment_lower = equipment.lower()
            for level, keywords in self.equipment_levels.items():
                if any(kw.lower() in equipment_lower for kw in keywords):
                    return level
            return 'gym'

        if 'Equipment' in df.columns:
            df['equipment_accessibility'] = df['Equipment'].apply(get_equipment_accessibility)

        # Estimated calories burned (MET-based estimation)
        def estimate_calories(title, desc, level):
            combined = f"{title} {desc}".lower()

            # MET values approximation
            if any(word in combined for word in ['cardio', 'run', 'sprint', 'jump', 'burpee']):
                met = 8.0 if 'High' in level else 6.0
            elif any(word in combined for word in ['circuit', 'complex', 'compound']):
                met = 6.0
            else:
                met = 3.0  # Strength training

            # Calories for 10 minutes for 70kg person
            return int(met * 70 * 10 / 200)

        df['calories_10min'] = df.apply(
            lambda x: estimate_calories(x['Title'], x['Desc'], x['Level']), axis=1
        )

        return df

    def _categorize_exercises(self, df: pd.DataFrame) -> pd.DataFrame:
        """Categorize exercises for advanced filtering."""

        # Training goals suitability
        def get_goal_suitability(title, desc, movement_pattern):
            combined = f"{title} {desc}".lower()
            suitability = {
                'strength': False,
                'hypertrophy': False,
                'endurance': False,
                'power': False,
                'mobility': False
            }

            # Strength - heavy compound movements
            if any(word in combined for word in ['max', 'heavy', '1rm', '3rm', '5rm']):
                suitability['strength'] = True

            # Hypertrophy - isolation and pump exercises
            if any(word in combined for word in ['fly', 'curl', 'extension', 'raise', 'pump']):
                suitability['hypertrophy'] = True

            # Endurance - high rep, low rest
            if any(word in combined for word in ['circuit', 'amrap', 'for time', 'emom']):
                suitability['endurance'] = True

            # Power - explosive movements
            if any(word in combined for word in ['explosive', 'plyo', 'jump', 'throw', 'power']):
                suitability['power'] = True

            # Mobility - stretching and ROM
            if any(word in combined for word in ['stretch', 'mobility', 'rom', 'flexibility']):
                suitability['mobility'] = True

            # Default based on movement pattern
            if not any(suitability.values()):
                if movement_pattern in ['Push', 'Pull', 'Hinge', 'Squat']:
                    suitability['strength'] = True
                    suitability['hypertrophy'] = True
                elif movement_pattern == 'Cardio':
                    suitability['endurance'] = True

            return suitability

        goal_results = df.apply(
            lambda x: get_goal_suitability(x['Title'], x['Desc'], x['movement_pattern']), axis=1
        )
        goal_df = pd.json_normalize(goal_results)
        df = pd.concat([df, goal_df], axis=1)

        # Progressive overload chain
        def find_progressions_regressions(title, bodypart, level, movement_pattern):
            """Suggest easier and harder variations."""
            progressions = []
            regressions = []

            # This is simplified - in production, you'd have a knowledge base
            if 'squat' in title.lower():
                if 'Bodyweight' in level:
                    progressions = ['Goblet Squat', 'Barbell Back Squat']
                    regressions = ['Chair Squat', 'Wall Sit']
                elif 'Barbell' in title:
                    progressions = ['Front Squat', 'Overhead Squat']
                    regressions = ['Goblet Squat', 'Bodyweight Squat']

            elif 'pushup' in title.lower() or 'press up' in title.lower():
                if 'Incline' in title:
                    progressions = ['Floor Push-up', 'Decline Push-up']
                    regressions = ['Wall Push-up', 'Knee Push-up']
                elif 'Floor' in title or 'Standard' in title:
                    progressions = ['Decline Push-up', 'Archer Push-up']
                    regressions = ['Incline Push-up', 'Knee Push-up']

            return {
                'progressions': progressions[:3],  # Limit to 3
                'regressions': regressions[:3]
            }

        chain_results = df.apply(
            lambda x: find_progressions_regressions(
                x['Title'], x['Bodypart'], x['Level'], x['movement_pattern']
            ), axis=1
        )
        chain_df = pd.json_normalize(chain_results)
        df = pd.concat([df, chain_df], axis=1)

        return df

    def _generate_exercise_id(self, row: pd.Series) -> str:
        """Generate unique deterministic ID for exercise."""
        # Create a hash from key fields
        # UPDATED: Included Level in the hash to prevent duplicates for exercises
        # that have the same title but different difficulty levels.
        key_string = f"{row['Title']}_{row['Bodypart']}_{row['Level']}_{row['movement_pattern']}"
        return hashlib.md5(key_string.encode()).hexdigest()[:12]

    def _create_exercise_object(self, row: pd.Series) -> Dict:
        """Convert DataFrame row to Firestore-ready object."""

        exercise = {
            # Core identification
            'exercise_id': row.get('exercise_id', ''),
            'Title': row.get('Title', ''),
            'Bodypart': row.get('Bodypart', ''),
            'Level': row.get('Level', 'Intermediate'),
            'Type': row.get('Type', 'Strength'),
            'Desc': row.get('Desc', ''),
            'Equipment': row.get('Equipment', 'Body Only'),

            # Intelligent enrichment
            'movement_pattern': row.get('movement_pattern', 'General'),
            'joint_impact': row.get('joint_impact', 'Medium'),
            'equipment_accessibility': row.get('equipment_accessibility', 'gym'),
            'calories_10min': row.get('calories_10min', 30),

            # Safety flags
            'knee_friendly': row.get('knee_friendly', True),
            'back_friendly': row.get('back_friendly', True),
            'shoulder_friendly': row.get('shoulder_friendly', True),
            'beginner_friendly': row.get('beginner_friendly', True),

            # Goal suitability
            'suitability_strength': row.get('strength', False),
            'suitability_hypertrophy': row.get('hypertrophy', False),
            'suitability_endurance': row.get('endurance', False),
            'suitability_power': row.get('power', False),
            'suitability_mobility': row.get('mobility', False),

            # Progressive chain
            'progressions': row.get('progressions', []),
            'regressions': row.get('regressions', []),

            # Metadata
            'processed_at': pd.Timestamp.now().isoformat(),
            'data_source': 'enhanced_preprocessing',
            'version': '2.0'
        }

        # Clean None values
        return {k: v for k, v in exercise.items() if v is not None}

    def save_to_firestore(self, exercises: List[Dict], batch_size: int = 100):
        """Save processed exercises to Firestore."""
        # Note: This method is kept for compatibility but the master pipeline uses its own uploader.
        pass