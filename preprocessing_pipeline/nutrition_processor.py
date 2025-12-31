import hashlib

import pandas as pd
import numpy as np
import re
import json
from typing import Dict, List, Any


class NutritionDataProcessor:
    """Transforms raw nutrition data into intelligent food database."""

    def __init__(self):
        # Food categories mapping
        self.food_categories = {
            'protein': ['chicken', 'beef', 'fish', 'tofu', 'tempeh', 'egg', 'meat', 'pork', 'lamb'],
            'carb': ['rice', 'pasta', 'bread', 'potato', 'oat', 'quinoa', 'cereal', 'noodle'],
            'vegetable': ['broccoli', 'spinach', 'carrot', 'lettuce', 'kale', 'cabbage', 'asparagus'],
            'fruit': ['apple', 'banana', 'orange', 'berry', 'melon', 'grape', 'mango', 'pineapple'],
            'dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream'],
            'fat': ['avocado', 'oil', 'nut', 'seed', 'butter', 'mayonnaise'],
            'processed': ['chip', 'cookie', 'cake', 'soda', 'candy', 'fried', 'fast food']
        }

        # Meal type classification
        self.meal_types = {
            'breakfast': ['breakfast', 'morning', 'oats', 'cereal', 'pancake', 'waffle'],
            'lunch': ['lunch', 'sandwich', 'wrap', 'salad', 'soup'],
            'dinner': ['dinner', 'steak', 'roast', 'grilled', 'baked', 'stir fry'],
            'snack': ['snack', 'bar', 'trail mix', 'fruit', 'nuts', 'yogurt']
        }

        # Dietary restriction flags
        self.dietary_flags = {
            'vegetarian': ['meat', 'chicken', 'beef', 'pork', 'fish', 'seafood'],
            'vegan': ['meat', 'chicken', 'beef', 'pork', 'fish', 'dairy', 'egg', 'honey', 'milk', 'cheese'],
            'halal': ['pork', 'bacon', 'ham', 'alcohol'],
            'gluten_free': ['wheat', 'gluten', 'barley', 'rye'],
            'dairy_free': ['milk', 'cheese', 'butter', 'cream', 'yogurt']
        }

    def process_raw_data(self, raw_df: pd.DataFrame) -> List[Dict]:
        """Main processing pipeline for nutrition data."""
        print(f"🍎 Processing {len(raw_df)} raw nutrition items...")

        # 1. Clean and standardize
        df = self._clean_nutrition_data(raw_df)

        # 2. Enrich with nutritional intelligence
        df = self._enrich_nutrition_data(df)

        # 3. Categorize for dietary needs
        df = self._categorize_nutrition_data(df)

        # 4. Generate health scores
        df = self._calculate_health_scores(df)

        # 5. Convert to Firestore-ready format
        processed_items = []
        for _, row in df.iterrows():
            food_item = self._create_food_object(row)
            processed_items.append(food_item)

        print(f"✅ Processed {len(processed_items)} nutrition items with health scoring")
        return processed_items

    def _clean_nutrition_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize nutrition data."""
        # Standardize column names
        # UPDATED: Added 'Food_Item' to map correctly from raw CSV
        column_map = {
            'food': 'Name', 'food_name': 'Name', 'item': 'Name', 'Food_Item': 'Name',
            'calories': 'Calories', 'cal': 'Calories', 'energy': 'Calories', 'Calories (kcal)': 'Calories',
            'protein': 'Protein', 'prot': 'Protein', 'Protein (g)': 'Protein',
            'carbs': 'Carbs', 'carbohydrates': 'Carbs', 'carb': 'Carbs', 'Carbohydrates (g)': 'Carbs',
            'fat': 'Fat', 'lipid': 'Fat', 'Fat (g)': 'Fat',
            'category': 'Category', 'type': 'Category',
            'meal_time': 'Meal_Type', 'time': 'Meal_Type', 'Meal_Type': 'Meal_Type'
        }

        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

        # Ensure required columns exist
        required = ['Name', 'Calories', 'Protein', 'Carbs', 'Fat']
        for col in required:
            if col not in df.columns:
                df[col] = 0

        # Clean and title case names
        if 'Name' in df.columns:
            df['Name'] = df['Name'].astype(str).str.title().str.strip()

        # Convert numeric columns
        numeric_cols = ['Calories', 'Protein', 'Carbs', 'Fat']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Fill missing categories
        if 'Category' not in df.columns:
            df['Category'] = 'General'

        if 'Meal_Type' not in df.columns:
            df['Meal_Type'] = 'General'

        return df

    def _enrich_nutrition_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add intelligent nutritional fields."""

        # Infer missing micronutrients (estimated)
        def estimate_micronutrients(name, category, calories):
            name_lower = name.lower()

            # Vitamin C - fruits and vegetables
            vitamin_c = 0
            if any(word in name_lower for word in ['orange', 'citrus', 'berry', 'broccoli', 'pepper']):
                vitamin_c = min(calories / 10, 100)

            # Fiber estimate
            fiber = 0
            if category in ['Vegetable', 'Fruit', 'Whole Grain']:
                fiber = max(calories / 50, 2)
            elif 'processed' in category.lower():
                fiber = max(calories / 200, 0.5)

            # Sodium estimate (processed foods higher)
            sodium = 0
            if any(word in name_lower for word in ['processed', 'canned', 'frozen', 'fast food', 'chip']):
                sodium = calories * 2
            else:
                sodium = calories * 0.5

            return {
                'fiber_g': round(fiber, 1),
                'sodium_mg': int(sodium),
                'vitamin_c_mg': int(vitamin_c),
                'calcium_mg': int(calories * 0.5)  # Rough estimate
            }

        micronutrient_results = df.apply(
            lambda x: estimate_micronutrients(x.get('Name', ''), x.get('Category', ''), x.get('Calories', 0)),
            axis=1
        )
        micronutrient_df = pd.json_normalize(micronutrient_results)
        df = pd.concat([df, micronutrient_df], axis=1)

        # Calculate macronutrient percentages
        def calculate_macro_percentages(calories, protein, carbs, fat):
            if calories <= 0:
                return {'protein_pct': 0, 'carbs_pct': 0, 'fat_pct': 0}

            protein_cals = protein * 4
            carbs_cals = carbs * 4
            fat_cals = fat * 9

            return {
                'protein_pct': round((protein_cals / calories) * 100, 1),
                'carbs_pct': round((carbs_cals / calories) * 100, 1),
                'fat_pct': round((fat_cals / calories) * 100, 1)
            }

        macro_results = df.apply(
            lambda x: calculate_macro_percentages(
                x.get('Calories', 0),
                x.get('Protein', 0),
                x.get('Carbs', 0),
                x.get('Fat', 0)
            ), axis=1
        )
        macro_df = pd.json_normalize(macro_results)
        df = pd.concat([df, macro_df], axis=1)

        # Determine primary food category
        def determine_food_category(name, existing_category):
            name_lower = name.lower()

            for category, keywords in self.food_categories.items():
                if any(keyword in name_lower for keyword in keywords):
                    return category.capitalize()

            return existing_category if existing_category else 'General'

        df['primary_category'] = df.apply(
            lambda x: determine_food_category(x.get('Name', ''), x.get('Category', '')),
            axis=1
        )

        # Estimate preparation time
        def estimate_prep_time(name, category):
            name_lower = name.lower()

            if any(word in name_lower for word in ['raw', 'fresh', 'salad', 'fruit']):
                return 5
            elif any(word in name_lower for word in ['canned', 'packaged', 'bar', 'snack']):
                return 2
            elif any(word in name_lower for word in ['cooked', 'baked', 'grilled', 'roast']):
                return 30
            elif any(word in name_lower for word in ['complex', 'recipe', 'meal', 'dinner']):
                return 45
            else:
                return 15  # Default

        df['prep_time_min'] = df.apply(
            lambda x: estimate_prep_time(x.get('Name', ''), x.get('Category', '')),
            axis=1
        )

        return df

    def _categorize_nutrition_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Categorize for dietary needs and preferences."""

        # Determine dietary compatibility
        def check_dietary_compatibility(name, ingredients=""):
            name_lower = name.lower()
            ingredients_lower = ingredients.lower() if isinstance(ingredients, str) else ""
            combined = f"{name_lower} {ingredients_lower}"

            compatibility = {}

            for diet, restricted in self.dietary_flags.items():
                # Check if contains restricted items
                contains_restricted = any(item in combined for item in restricted)
                compatibility[f'{diet}_friendly'] = not contains_restricted

            return compatibility

        dietary_results = df.apply(
            lambda x: check_dietary_compatibility(x.get('Name', ''), x.get('ingredients', '')),
            axis=1
        )
        dietary_df = pd.json_normalize(dietary_results)
        df = pd.concat([df, dietary_df], axis=1)

        # Determine best meal type
        def determine_optimal_meal_type(name, calories, protein):
            name_lower = name.lower()

            # High protein + moderate calories = good for any meal
            protein_calorie_ratio = (protein * 4) / max(calories, 1)

            for meal_type, keywords in self.meal_types.items():
                if any(keyword in name_lower for keyword in keywords):
                    return meal_type.capitalize()

            # Heuristic based on nutrition
            if calories < 200:
                return 'Snack'
            elif protein_calorie_ratio > 0.3:  # High protein ratio
                return 'Lunch' if calories < 500 else 'Dinner'
            elif calories > 600:
                return 'Dinner'
            else:
                return 'Lunch'

        df['optimal_meal_type'] = df.apply(
            lambda x: determine_optimal_meal_type(
                x.get('Name', ''),
                x.get('Calories', 0),
                x.get('Protein', 0)
            ), axis=1
        )

        # Flavor profile (simplified)
        def estimate_flavor_profile(name, category):
            name_lower = name.lower()

            if any(word in name_lower for word in ['sweet', 'fruit', 'honey', 'sugar', 'cake']):
                return 'Sweet'
            elif any(word in name_lower for word in ['spicy', 'chili', 'pepper', 'curry', 'hot']):
                return 'Spicy'
            elif any(word in name_lower for word in ['savory', 'umami', 'meaty', 'cheese']):
                return 'Savory'
            elif any(word in name_lower for word in ['bitter', 'dark', 'coffee', 'kale']):
                return 'Bitter'
            else:
                return 'Neutral'

        df['flavor_profile'] = df.apply(
            lambda x: estimate_flavor_profile(x.get('Name', ''), x.get('Category', '')),
            axis=1
        )

        return df

    def _calculate_health_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate various health scores for ranking."""

        # Nutrient Density Score (0-100)
        def calculate_nutrient_density(calories, protein, fiber, vitamin_c):
            if calories <= 0:
                return 50

            # Base score from protein and fiber density
            protein_score = min((protein * 4 / calories) * 1000, 50)
            fiber_score = min((fiber / calories) * 1000, 30)
            vitamin_score = min(vitamin_c / 10, 20)

            return round(protein_score + fiber_score + vitamin_score, 1)

        df['nutrient_density_score'] = df.apply(
            lambda x: calculate_nutrient_density(
                x.get('Calories', 0),
                x.get('Protein', 0),
                x.get('fiber_g', 0),
                x.get('vitamin_c_mg', 0)
            ), axis=1
        )

        # Satiety Score (estimated)
        def calculate_satiety_score(calories, protein, fiber, fat):
            if calories <= 0:
                return 50

            # Protein and fiber increase satiety, very low calories decrease it
            protein_effect = min(protein * 5, 40)
            fiber_effect = min(fiber * 3, 30)
            fat_effect = min(fat * 2, 20)
            calorie_penalty = max(0, (500 - calories) / 10)  # Very low calorie foods less satisfying

            return round(protein_effect + fiber_effect + fat_effect - calorie_penalty, 1)

        df['satiety_score'] = df.apply(
            lambda x: calculate_satiety_score(
                x.get('Calories', 0),
                x.get('Protein', 0),
                x.get('fiber_g', 0),
                x.get('Fat', 0)
            ), axis=1
        )

        # Weight Loss Friendliness Score
        def calculate_weight_loss_score(calories, protein_pct, fiber_g, sodium_mg):
            # Lower calories = better
            calorie_score = max(0, 100 - (calories / 10))

            # Higher protein percentage = better
            protein_score = min(protein_pct * 2, 40)

            # Higher fiber = better
            fiber_score = min(fiber_g * 5, 30)

            # Lower sodium = better
            sodium_penalty = max(0, (sodium_mg - 500) / 100)

            return round(max(0, calorie_score + protein_score + fiber_score - sodium_penalty), 1)

        df['weight_loss_score'] = df.apply(
            lambda x: calculate_weight_loss_score(
                x.get('Calories', 0),
                x.get('protein_pct', 0),
                x.get('fiber_g', 0),
                x.get('sodium_mg', 0)
            ), axis=1
        )

        # Muscle Gain Score
        def calculate_muscle_gain_score(calories, protein, protein_pct):
            # Need sufficient calories and high protein
            calorie_sufficiency = min(calories / 20, 50)  # Up to 1000 calories = max score
            protein_absolute = min(protein * 3, 30)
            protein_relative = min(protein_pct, 20)

            return round(calorie_sufficiency + protein_absolute + protein_relative, 1)

        df['muscle_gain_score'] = df.apply(
            lambda x: calculate_muscle_gain_score(
                x.get('Calories', 0),
                x.get('Protein', 0),
                x.get('protein_pct', 0)
            ), axis=1
        )

        return df

    def _create_food_object(self, row: pd.Series) -> Dict:
        """Convert DataFrame row to Firestore-ready object."""

        # UPDATED: Use Name + Calories + Protein to create a truly unique hash ID
        unique_string = f"{row.get('Name', 'Unknown')}_{row.get('Calories', 0)}_{row.get('Protein', 0)}"

        food_item = {
            # Core identification
            'food_id': hashlib.md5(unique_string.encode()).hexdigest()[:12],
            'Name': row.get('Name', ''),
            'primary_category': row.get('primary_category', 'General'),
            'Category': row.get('Category', 'General'),
            'Meal_Type': row.get('Meal_Type', 'General'),
            'optimal_meal_type': row.get('optimal_meal_type', 'General'),

            # Macronutrients
            'Calories': float(row.get('Calories', 0)),
            'Protein': float(row.get('Protein', 0)),
            'Carbs': float(row.get('Carbs', 0)),
            'Fat': float(row.get('Fat', 0)),
            'fiber_g': float(row.get('fiber_g', 0)),

            # Micronutrients (estimated)
            'sodium_mg': float(row.get('sodium_mg', 0)),
            'vitamin_c_mg': float(row.get('vitamin_c_mg', 0)),
            'calcium_mg': float(row.get('calcium_mg', 0)),

            # Macronutrient percentages
            'protein_pct': float(row.get('protein_pct', 0)),
            'carbs_pct': float(row.get('carbs_pct', 0)),
            'fat_pct': float(row.get('fat_pct', 0)),

            # Health scores (0-100)
            'nutrient_density_score': float(row.get('nutrient_density_score', 50)),
            'satiety_score': float(row.get('satiety_score', 50)),
            'weight_loss_score': float(row.get('weight_loss_score', 50)),
            'muscle_gain_score': float(row.get('muscle_gain_score', 50)),

            # Dietary compatibility
            'vegetarian_friendly': bool(row.get('vegetarian_friendly', True)),
            'vegan_friendly': bool(row.get('vegan_friendly', False)),
            'halal_friendly': bool(row.get('halal_friendly', True)),
            'gluten_free_friendly': bool(row.get('gluten_free_friendly', True)),
            'dairy_free_friendly': bool(row.get('dairy_free_friendly', True)),

            # Practical information
            'prep_time_min': int(row.get('prep_time_min', 15)),
            'flavor_profile': row.get('flavor_profile', 'Neutral'),

            # Metadata
            'processed_at': pd.Timestamp.now().isoformat(),
            'data_source': 'enhanced_preprocessing',
            'version': '2.0'
        }

        # Clean None values
        return {k: v for k, v in food_item.items() if v is not None}