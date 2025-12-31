import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Initialize
cred_path = os.path.join(BASE_DIR, 'serviceAccountKey.json')
if not os.path.exists(cred_path):
    print("❌ Error: serviceAccountKey.json not found.")
    exit()

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()


def check_collection(name, expected_fields):
    print(f"\n--- 🔍 Checking Collection: '{name}' ---")
    ref = db.collection(name).limit(3)
    docs = list(ref.stream())

    if not docs:
        print(f"❌ ERROR: Collection '{name}' is EMPTY or does not exist.")
        return

    print(f"✅ Found {len(docs)} sample documents.\n")

    for i, doc in enumerate(docs):
        data = doc.to_dict()
        print(f"📄 Document ID: {doc.id}")

        # Check specific fields
        missing = []
        for field in expected_fields:
            if field in data:
                print(f"   ok: {field} = '{data[field]}'")
            else:
                missing.append(field)
                print(f"   ❌ MISSING: {field}")

        # Print actual keys to help debug
        print(f"   ℹ️  Actual Keys found: {list(data.keys())}")
        print("-" * 30)

    if missing:
        print(f"\n⚠️ CRITICAL: Your code expects fields {expected_fields}, but they are missing or named differently.")
    else:
        print(f"\n✅ Data looks compatible with Recommender!")


if __name__ == '__main__':
    # 1. Check Fitness
    # Recommender expects: Title, Bodypart, Level
    check_collection('fitness_exercises', ['Title', 'Bodypart', 'Level'])

    # 2. Check Nutrition
    # Recommender expects: Name, Calories, Protein, Meal_Type
    check_collection('nutrition_items', ['Name', 'Calories', 'Protein', 'Meal_Type'])