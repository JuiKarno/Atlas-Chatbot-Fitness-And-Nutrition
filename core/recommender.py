import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore import FieldFilter
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random


class ContentBasedRecommender:
    def __init__(self):
        # Assumes firebase_admin is initialized externally
        self.db = firestore.client()
        
        # Gold Standards for Effectiveness
        self.GOLD_STANDARDS = {
            'Muscle Gain': ['Squats', 'Deadlifts', 'Bench Press', 'High Protein', 'Protein', 'Strength', 'Hypertrophy'],
            'Weight Loss': ['HIIT', 'Burpees', 'Lean Protein', 'Fiber-rich', 'Cardio', 'Metabolic', 'Calorie Burn'],
            'Weight Gain': ['High Protein', 'Bulking', 'Compound lifts'],
            'Maintenance': ['Balanced', 'General', 'Steady state']
        }

    def _get_smart_protocol(self, user_profile, exercise_level):
        """Generates Sets/Reps string based on User Goal."""
        goal = user_profile.get('goal', 'Maintenance')
        sets, reps, rest = "3", "10-12", "60s"
        if exercise_level == 'Beginner':
            sets = "2-3"
        elif exercise_level == 'Intermediate':
            sets = "3-4"
        elif exercise_level == 'Advanced':
            sets = "4-5"

        if 'Muscle' in goal:
            reps, rest = "8-12", "60s"
        elif 'Weight' in goal or 'Loss' in goal:
            reps, rest = "12-15", "30-45s"
        return f"{sets} Sets • {reps} Reps • {rest} Rest"

    def get_recommendations(self, user_profile, intent, target, ignore_list=[], extra_entities={}, top_k=3, likes=[],
                            dislikes=[], no_equipment=False):
        """
        Main entry point for recommendations.
        """
        if target and isinstance(target, str): target = target.title()

        # Ensure ignore_list is clean and normalized for robust comparison
        clean_ignore_list = [str(x).strip().lower() for x in ignore_list if x]
        clean_likes = [str(x).strip().lower() for x in likes if x]
        clean_dislikes = [str(x).strip().lower() for x in dislikes if x]

        print(f"\n[Recommender] Target: {target}, Intent: {intent}, No Equipment: {no_equipment}")
        print(f"   -> Likes: {clean_likes}, Dislikes: {clean_dislikes}")

        if intent in ['fitness_request', 'fitness_variation', 'fitness']:
            return self._get_fitness_recs(user_profile, target, clean_ignore_list, top_k, clean_likes, clean_dislikes, no_equipment)
        elif intent in ['nutrition_request', 'nutrition_variation', 'nutrition', 'diet', 'food']:
            return self._get_nutrition_recs(user_profile, target, clean_ignore_list, extra_entities, top_k, clean_likes,
                                            clean_dislikes)
        return []

    def _fetch_candidates(self, level, target, clean_ignore_list, clean_dislikes, min_count=5):
        """Helper to query Firestore for fitness."""
        exercises_ref = self.db.collection('fitness_exercises')
        search_terms = []
        if target and target != "General":
            synonyms = {
                "chest": ["Chest", "Pectorals", "Upper Body", "Pecs"],
                "legs": ["Legs", "Quadriceps", "Hamstrings", "Calves", "Lower Body", "Quads", "Glutes"],
                "back": ["Back", "Lats", "Lower Back", "Traps"],
                "arms": ["Arms", "Biceps", "Triceps"],
                "abs": ["Abs", "Core", "Abdominals", "Six Pack"],
                "shoulders": ["Shoulders", "Deltoids"],
                "core": ["Abs", "Core", "Abdominals", "Six Pack"]
            }
            target_lower = target.lower()
            search_terms = [target]

            if target_lower in synonyms:
                search_terms.extend(synonyms[target_lower])

            for key, values in synonyms.items():
                if target_lower in [v.lower() for v in values]:
                    search_terms.extend(values)
                    search_terms.append(key.title())

            search_terms = list(set([t.title() if isinstance(t, str) else t for t in search_terms]))[:10]

        query = exercises_ref.where(filter=FieldFilter('Level', '==', level))
        if search_terms:
            query = query.where(filter=FieldFilter('Bodypart', 'in', search_terms))

        docs = query.stream()
        candidates = []
        for doc in docs:
            d = doc.to_dict()
            title = str(d.get('Title', '')).strip().lower()
            equipment = str(d.get('Equipment', '')).strip().lower()
            desc = str(d.get('Desc', '')).strip().lower()
            ex_type = str(d.get('Type', '')).strip().lower()

            # --- DISLIKE FILTER (check title, equipment, type, and description) ---
            searchable_text = f"{title} {equipment} {ex_type} {desc}"
            if any(bad in searchable_text for bad in clean_dislikes):
                continue

            if title and title not in clean_ignore_list:
                candidates.append(d)

        # Fallback Logic
        if len(candidates) < min_count and search_terms:
            query = exercises_ref.where(filter=FieldFilter('Bodypart', 'in', search_terms)).limit(50)
            docs = query.stream()
            for doc in docs:
                d = doc.to_dict()
                title = str(d.get('Title', '')).strip().lower()
                equipment = str(d.get('Equipment', '')).strip().lower()
                desc = str(d.get('Desc', '')).strip().lower()
                ex_type = str(d.get('Type', '')).strip().lower()
                current_titles = [str(c.get('Title', '')).strip().lower() for c in candidates]

                # Dislike Filter again (check all fields)
                searchable_text = f"{title} {equipment} {ex_type} {desc}"
                if any(bad in searchable_text for bad in clean_dislikes): continue

                if title and title not in clean_ignore_list and title not in current_titles:
                    candidates.append(d)

        return candidates


    def _get_fitness_recs(self, user_profile, target, clean_ignore_list, top_k=3, likes=[], dislikes=[], no_equipment=False):
        try:
            user_level = user_profile.get('fitness_level', 'Intermediate')

            if user_level == 'Beginner':
                search_levels = ['Beginner', 'Intermediate', 'Advanced']
            elif user_level == 'Advanced':
                search_levels = ['Advanced', 'Intermediate', 'Beginner']
            else:
                search_levels = ['Intermediate', 'Beginner', 'Advanced']

            candidates = []
            seen_titles = set(clean_ignore_list)
            
            # Equipment types that are considered "bodyweight" or "no equipment"
            bodyweight_equipment = ['body only', 'bodyweight', 'body weight', 'none', 'other', '']

            for lvl in search_levels:
                level_cands = self._fetch_candidates(lvl, target, list(seen_titles), dislikes, min_count=top_k * 3)

                for cand in level_cands:
                    title_raw = cand.get('Title', '')
                    title_norm = str(title_raw).strip().lower()
                    equipment = str(cand.get('Equipment', '')).strip().lower()
                    
                    # Filter for no equipment if flag is set
                    if no_equipment and equipment not in bodyweight_equipment:
                        continue

                    if title_norm and title_norm not in seen_titles:
                        candidates.append(cand)
                        seen_titles.add(title_norm)

                if len(candidates) >= top_k * 5: break

            if len(candidates) < top_k:
                exercises_ref = self.db.collection('fitness_exercises').limit(50)
                all_docs = [d.to_dict() for d in exercises_ref.stream()]
                random.shuffle(all_docs)
                for d in all_docs:
                    title_norm = str(d.get('Title', '')).strip().lower()
                    equipment = str(d.get('Equipment', '')).strip().lower()
                    desc = str(d.get('Desc', '')).strip().lower()
                    ex_type = str(d.get('Type', '')).strip().lower()
                    searchable_text = f"{title_norm} {equipment} {ex_type} {desc}"
                    
                    # Filter for no equipment if flag is set
                    if no_equipment and equipment not in bodyweight_equipment:
                        continue
                    
                    if any(bad in searchable_text for bad in dislikes): continue
                    if title_norm not in seen_titles:
                        candidates.append(d)
                        seen_titles.add(title_norm)
                        if len(candidates) >= top_k + 5: break


            if not candidates: return []

            # Scoring Logic (TF-IDF + Cosine + Preference Boost)
            df = pd.DataFrame(candidates)
            df['features'] = (df.get('Title', '') + " " + df.get('Bodypart', '') + " " + df.get('Desc', '').fillna(''))

            try:
                tfidf = TfidfVectorizer(stop_words='english')
                tfidf_matrix = tfidf.fit_transform(df['features'])

                user_query = f"{target} {user_level} {user_profile.get('goal', '')} {' '.join(likes)}"

                user_vec = tfidf.transform([user_query])
                base_scores = cosine_similarity(user_vec, tfidf_matrix).flatten()

                # --- NEW SCORING LOGIC (Effectiveness vs Preference) ---
                user_goal = user_profile.get('goal', 'Maintenance')
                gold_standards = []
                for goal_key, keywords in self.GOLD_STANDARDS.items():
                    if goal_key in user_goal:
                        gold_standards.extend(keywords)

                final_scores = []
                for idx, cosine_score in enumerate(base_scores):
                    row = df.iloc[idx]
                    title = str(row.get('Title', '')).lower()
                    desc = str(row.get('Desc', '')).lower()
                    bodypart = str(row.get('Bodypart', '')).lower()
                    
                    combined_text = f"{title} {desc} {bodypart}"

                    # 1. Calculate Effectiveness Score (0 to 1)
                    # Count how many Gold Standard keywords match
                    match_count = sum(1 for ks in gold_standards if ks.lower() in combined_text)
                    # Normalize: 0 to 1 (capped at 3 matches for max effectiveness)
                    effectiveness = min(1.0, match_count / 3.0) 
                    
                    # Gold Standard Boost (Even if not liked)
                    if match_count > 0:
                        effectiveness += 0.4 
                    effectiveness = min(1.0, effectiveness)

                    # 2. Calculate Preference Score (0 to 1)
                    # Cosine score is our baseline preference from TF-IDF query
                    # Additionally boost if user specifically "liked" this item
                    
                    # Get equipment field for matching
                    equipment = str(row.get('Equipment', '')).lower()
                    
                    # Check if any preference matches title OR equipment (with fuzzy matching for plurals)
                    has_preference_match = any(
                        good in title or good in equipment or  # Direct match
                        good.rstrip('s') in title or good.rstrip('s') in equipment  # Singular form (dumbbells -> dumbbell)
                        for good in likes
                    )
                    
                    # Debug logging for preference matching
                    if likes:
                        print(f"[Recommender] Preference check - Title: '{title[:30]}', Equipment: '{equipment}', Likes: {likes}, Match: {has_preference_match}")
                    
                    preference_boost = 0.3 if has_preference_match else 0
                    user_pref = min(1.0, cosine_score + preference_boost)

                    # 3. Final Formula: (Eff * 0.7) + (Pref * 0.3)
                    final_score = (effectiveness * 0.7) + (user_pref * 0.3)
                    final_scores.append(final_score)

                df['score'] = final_scores
                df = df.sort_values(by='score', ascending=False)
            except Exception as e:
                print(f"TF-IDF Error: {e}")
                pass

            results = []
            for _, row in df.iterrows():
                item = row.to_dict()
                item['protocol'] = self._get_smart_protocol(user_profile, item.get('Level', 'Intermediate'))
                results.append(item)
                if len(results) >= top_k: break

            return results

        except Exception as e:
            print(f"Fitness Rec Error: {e}")
            return []

    def _get_nutrition_recs(self, user_profile, target, clean_ignore_list, extra_entities={}, top_k=3, likes=[],
                            dislikes=[]):
        try:
            nutrition_ref = self.db.collection('nutrition_items')
            query = None

            pref_val = extra_entities.get('preference')
            preference = str(pref_val).lower() if pref_val else ''

            cat_val = extra_entities.get('category')
            category = str(cat_val).lower() if cat_val else ''

            if target and target not in ["General", "Food", "Meal"]:
                meal_type_map = {'breakfast': 'Breakfast', 'lunch': 'Lunch', 'dinner': 'Dinner', 'snack': 'Snack'}
                meal_target = meal_type_map.get(target.lower(), None)
                if meal_target:
                    query = nutrition_ref.where(filter=FieldFilter('Meal_Type', '==', meal_target))

            if not query and 'protein' in preference:
                query = nutrition_ref.where(filter=FieldFilter('Protein', '>=', 20)).limit(50)

            if not query:
                query = nutrition_ref.limit(200)

            items = [doc.to_dict() for doc in query.stream()]

            if not items: return []

            candidates = []
            for item in items:
                name = str(item.get('Name', '')).strip().lower()
                if name in clean_ignore_list: continue

                # Dislike Filter
                if any(bad in name for bad in dislikes): continue

                if 'chicken' in preference or 'chicken' in category:
                    if 'chicken' not in name: continue
                if 'vegetarian' in preference and any(x in name for x in ['chicken', 'beef', 'pork', 'fish']): continue

                candidates.append(item)

            if not candidates:
                candidates = [i for i in items if str(i.get('Name', '')).strip().lower() not in clean_ignore_list]

            if not candidates: return []

            df = pd.DataFrame(candidates)

            def get_macro_tag(row):
                tags = []
                p = pd.to_numeric(row.get('Protein', 0), errors='coerce') or 0
                c = pd.to_numeric(row.get('Carbs', 0), errors='coerce') or 0
                cal = pd.to_numeric(row.get('Calories', 0), errors='coerce') or 0
                if p > 20: tags.append("high protein")
                if c < 20: tags.append("low carb")
                if cal < 400: tags.append("low calorie")
                return " ".join(tags)

            df['features'] = df.get('Name', '') + " " + df.get('Meal_Type', '') + " " + df.apply(get_macro_tag, axis=1)

            try:
                tfidf = TfidfVectorizer(stop_words='english')
                tfidf_matrix = tfidf.fit_transform(df['features'])

                user_goal = user_profile.get('goal', '')
                user_query = f"{target} {preference} {category} {user_goal} {' '.join(likes)}"

                user_vec = tfidf.transform([user_query])
                base_scores = cosine_similarity(user_vec, tfidf_matrix).flatten()

                # --- NEW SCORING LOGIC (Nutrition) ---
                user_goal = user_profile.get('goal', 'Maintenance')
                gold_standards = []
                for goal_key, keywords in self.GOLD_STANDARDS.items():
                    if goal_key in user_goal:
                        gold_standards.extend(keywords)

                final_scores = []
                for idx, cosine_score in enumerate(base_scores):
                    row = df.iloc[idx]
                    name = str(row.get('Name', '')).lower()
                    cat = str(row.get('Category', '')).lower()
                    
                    combined_text = f"{name} {cat}"

                    # 1. Effectiveness Score
                    match_count = sum(1 for ks in gold_standards if ks.lower() in combined_text)
                    # Special check for macros if available in gold standards logic
                    if 'High Protein' in gold_standards and int(row.get('Protein', 0)) > 20: match_count += 2
                    if 'Fiber-rich' in gold_standards and 'Salad' in cat: match_count += 1
                    
                    effectiveness = min(1.0, match_count / 3.0)
                    
                    # Gold Standard Boost
                    if match_count > 0:
                        effectiveness += 0.4
                    effectiveness = min(1.0, effectiveness)

                    # 2. Preference Score
                    # Check if any preference matches food name (with fuzzy matching for plurals)
                    has_preference_match = any(
                        good in name or good.rstrip('s') in name  # Direct or singular match
                        for good in likes
                    )
                    
                    # Debug logging for nutrition preference matching
                    if likes:
                        print(f"[Recommender] Nutrition preference check - Name: '{name[:30]}', Likes: {likes}, Match: {has_preference_match}")
                    
                    preference_boost = 0.3 if has_preference_match else 0
                    user_pref = min(1.0, cosine_score + preference_boost)

                    # 3. Final Formula
                    final_score = (effectiveness * 0.7) + (user_pref * 0.3)
                    final_scores.append(final_score)

                df['score'] = final_scores
                df = df.sort_values(by='score', ascending=False)
            except Exception as e:
                print(f"Nutrition TF-IDF Error: {e}")
                pass

            return df.head(top_k).to_dict(orient='records')

        except Exception as e:
            print(f"Nutrition Rec Error: {e}")
            return []