import sys
import os
import pandas as pd
import json

# Add project root to path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)

try:
    from preprocessing_pipeline.fitness_processor import FitnessDataProcessor
    from preprocessing_pipeline.nutrition_processor import NutritionDataProcessor
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

# Paths
RAW_FITNESS_PATH = os.path.join(project_root, 'raw_data', 'fitness_raw.csv')
RAW_NUTRITION_PATH = os.path.join(project_root, 'raw_data', 'nutrition_raw.csv')


def diagnose_fitness():
    print("\n🔎 DIAGNOSING FITNESS DATA...")
    if not os.path.exists(RAW_FITNESS_PATH):
        print("❌ Fitness file not found.")
        return

    # Load just 5 rows
    df = pd.read_csv(RAW_FITNESS_PATH, on_bad_lines='skip', nrows=5)
    print(f"   Raw Columns: {list(df.columns)}")
    print(f"   Sample Raw BodyPart: {df['BodyPart'].tolist() if 'BodyPart' in df.columns else 'Column Missing'}")

    processor = FitnessDataProcessor()
    # Process only these 5 rows
    processed = processor.process_raw_data(df)

    print("\n   --- Processed Fitness Item #1 ---")
    if processed:
        print(json.dumps(processed[0], indent=2))
        if 'Bodypart' not in processed[0] or not processed[0]['Bodypart']:
            print("   ⚠️ WARNING: 'Bodypart' field is missing or empty!")
    else:
        print("   ⚠️ No data processed.")


def diagnose_nutrition():
    print("\n🔎 DIAGNOSING NUTRITION DATA...")
    if not os.path.exists(RAW_NUTRITION_PATH):
        print("❌ Nutrition file not found.")
        return

    # Load just 5 rows
    df = pd.read_csv(RAW_NUTRITION_PATH, on_bad_lines='skip', nrows=5)
    print(f"   Raw Columns: {list(df.columns)}")

    processor = NutritionDataProcessor()
    processed = processor.process_raw_data(df)

    print("\n   --- ID Generation Check ---")
    ids = [item['food_id'] for item in processed]
    print(f"   Generated IDs: {ids}")

    if len(set(ids)) < len(ids):
        print("   ❌ CRITICAL ERROR: Duplicate IDs detected! This causes overwrite.")
    else:
        print("   ✅ IDs are unique.")

    print("\n   --- Processed Nutrition Item #1 ---")
    if processed:
        print(json.dumps(processed[0], indent=2))


if __name__ == "__main__":
    diagnose_fitness()
    diagnose_nutrition()