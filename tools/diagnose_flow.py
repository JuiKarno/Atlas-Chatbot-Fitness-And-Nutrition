import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import firebase_admin
from firebase_admin import credentials, firestore
from config.settings import Config
from core.nlu_engine import SmartNLUEngine
from core.recommender import ContentBasedRecommender

# --- INIT ---
if not firebase_admin._apps:
    key_path = Config.FIREBASE_CREDENTIALS if hasattr(Config, 'FIREBASE_CREDENTIALS') else 'serviceAccountKey.json'
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def test_flow(user_message, user_profile, mock_history=[]):
    print(f"\n{'='*60}")
    print(f"TESTING MESSAGE: '{user_message}'")
    print(f"USER PROFILE: {user_profile}")
    print(f"{'='*60}")

    # 1. NLU
    print("\n[1] Running NLU...")
    try:
        nlu = SmartNLUEngine()
        analysis = nlu.analyze_message(user_message, mock_history)
        print(f"   -> Intent: {analysis.get('intent')}")
        print(f"   -> Entities: {analysis.get('entities')}")
    except Exception as e:
        print(f"   ❌ NLU Error: {e}")
        return

    intent = analysis.get('intent')
    entities = analysis.get('entities', {})
    if isinstance(entities, str): entities = {'target': entities}
    target = entities.get('target')

    # 2. Recommender
    print("\n[2] Running Recommender...")
    rec_engine = ContentBasedRecommender()
    
    # Mock ignore list (simulate a user asking for "different" exercises)
    ignore_list = []
    if "different" in user_message or "another" in user_message:
        print("   -> Simulating 'different' request (adding dummy ignore items)")
        # You can manually add titles here to test filtering if you know them
        # ignore_list = ["Crunch", "Plank"] 
    
    results = rec_engine.get_recommendations(
        user_profile, 
        intent, 
        target, 
        ignore_list=ignore_list, 
        top_k=3
    )

    print(f"\n[3] Results Found: {len(results)}")
    for i, res in enumerate(results):
        print(f"   {i+1}. {res.get('Title')} (Level: {res.get('Level')}, Bodypart: {res.get('Bodypart')})")

    if len(results) < 3:
        print("\n❌ ISSUE: Returned fewer than 3 results!")
    else:
        print("\n✅ SUCCESS: Returned 3 results.")

if __name__ == "__main__":
    # Test Case 1: Beginner asking for Core (The problematic case)
    profile_beginner = {'fitness_level': 'Beginner', 'goal': 'Weight Loss'}
    test_flow("suggest core exercises", profile_beginner)

    # Test Case 2: Advanced asking for Chest (Control case)
    profile_advanced = {'fitness_level': 'Advanced', 'goal': 'Muscle Gain'}
    test_flow("chest workout", profile_advanced)