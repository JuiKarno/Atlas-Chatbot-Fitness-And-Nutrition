import sys
import os
import json
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# Add project root to path to import local modules
# This assumes the script is located in atlas_chatbot_v2/tools/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)

try:
    from config.settings import Config
    from preprocessing_pipeline.fitness_processor import FitnessDataProcessor
    from preprocessing_pipeline.nutrition_processor import NutritionDataProcessor
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"Current Path: {sys.path}")
    sys.exit(1)

# --- CONFIGURATION ---
RAW_FITNESS_PATH = os.path.join(project_root, 'raw_data', 'fitness_raw.csv')
RAW_NUTRITION_PATH = os.path.join(project_root, 'raw_data', 'nutrition_raw.csv')

# Initialize Firestore
if not firebase_admin._apps:
    try:
        # Check if config has credentials path, otherwise look for default
        cred_path = getattr(Config, 'FIREBASE_CREDENTIALS', 'serviceAccountKey.json')

        # Ensure we look in the project root if a relative path is given
        if not os.path.isabs(cred_path):
            cred_path = os.path.join(project_root, cred_path)

        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase initialized with: {cred_path}")
        else:
            print(f"❌ Service account key not found at: {cred_path}")
            print("Please ensure 'serviceAccountKey.json' is in the project root.")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        sys.exit(1)

db = firestore.client()


def upload_batch(collection_name, data_list, batch_size=400):
    """Uploads a list of dictionaries to Firestore in batches."""
    if not data_list:
        print(f"⚠️  No data to upload for {collection_name}")
        return

    print(f"🔥 Uploading {len(data_list)} items to '{collection_name}'...")

    total = len(data_list)
    batch = db.batch()
    count = 0
    uploaded_count = 0

    for item in data_list:
        # Determine Doc ID (Fitness uses 'exercise_id', Nutrition uses 'food_id')
        doc_id = item.get('exercise_id') or item.get('food_id')

        if not doc_id:
            continue  # Skip invalid items

        # Create document reference
        doc_ref = db.collection(collection_name).document(str(doc_id))

        # Add set operation to batch
        batch.set(doc_ref, item)
        count += 1

        # Commit if batch limit reached
        if count >= batch_size:
            batch.commit()
            uploaded_count += count
            print(f"   Saved {uploaded_count}/{total} documents...")
            batch = db.batch()  # Start new batch
            count = 0

    # Commit remaining items
    if count > 0:
        batch.commit()
        uploaded_count += count

    print(f"✅ Finished uploading {uploaded_count} documents to '{collection_name}'.")


def main():
    # --- 1. PROCESS FITNESS DATA ---
    if os.path.exists(RAW_FITNESS_PATH):
        print("\n💪 Starting Advanced Fitness Processing...")
        try:
            fitness_df = pd.read_csv(RAW_FITNESS_PATH, on_bad_lines='skip')

            # Initialize processor
            processor = FitnessDataProcessor()
            # Process data (Clean -> Enrich -> Score)
            enriched_exercises = processor.process_raw_data(fitness_df)

            # Save processed data locally for inspection
            output_dir = os.path.join(project_root, 'enhanced_datasets')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            fitness_output_path = os.path.join(output_dir, 'fitness_enhanced.json')
            with open(fitness_output_path, 'w') as f:
                json.dump(enriched_exercises, f, indent=2)
            print(f"   Saved processed fitness data to: {fitness_output_path}")

            # Upload to Firestore
            upload_batch('fitness_exercises', enriched_exercises)
        except Exception as e:
            print(f"❌ Error processing fitness data: {e}")
    else:
        print(f"❌ File not found: {RAW_FITNESS_PATH}")

    # --- 2. PROCESS NUTRITION DATA ---
    if os.path.exists(RAW_NUTRITION_PATH):
        print("\n🍎 Starting Advanced Nutrition Processing...")
        try:
            nutrition_df = pd.read_csv(RAW_NUTRITION_PATH, on_bad_lines='skip')

            # Initialize processor
            processor = NutritionDataProcessor()
            # Process data (Clean -> Enrich -> Score)
            enriched_food = processor.process_raw_data(nutrition_df)

            # Save processed data locally for inspection
            nutrition_output_path = os.path.join(output_dir, 'nutrition_enhanced.json')
            with open(nutrition_output_path, 'w') as f:
                json.dump(enriched_food, f, indent=2)
            print(f"   Saved processed nutrition data to: {nutrition_output_path}")

            # Upload to Firestore
            upload_batch('nutrition_items', enriched_food)
        except Exception as e:
            print(f"❌ Error processing nutrition data: {e}")
    else:
        print(f"❌ File not found: {RAW_NUTRITION_PATH}")


if __name__ == "__main__":
    main()