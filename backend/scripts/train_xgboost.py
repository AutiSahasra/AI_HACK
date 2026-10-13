import sys
import os
import asyncio
import json

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import DatabaseManager
from app.services.xgboost_service import xgboost_service, FEATURE_NAMES


async def main():
    print("=" * 60)
    print(" XGBoost Category Classifier Training Pipeline")
    print("=" * 60)
    print(f"Features (strictly ordered {len(FEATURE_NAMES)}): {FEATURE_NAMES}")

    await DatabaseManager.connect()
    try:
        inc_col = DatabaseManager.get_collection("incidents")
        records = await inc_col.find({"is_synthetic": True}).to_list(5000)

        if len(records) < 10:
            print("[ERROR] Found fewer than 10 incident records in database.")
            print("Please run generate_synthetic.py first!")
            return

        print(f"[INFO] Training on {len(records)} labeled synthetic incident cases...")
        results = xgboost_service.train_and_evaluate(training_records=records, test_size=0.2, random_state=42)

        metrics = results["metrics"]
        print(f"\n[OK] Model Version: {results['version']}")
        print(f"[OK] Macro-F1 Score: {metrics['macro_f1']}")
        print(f"[OK] Train Samples: {metrics['train_samples']} | Test Samples: {metrics['test_samples']}")
        print("\n--- Per-Class Metrics ---")
        rep = metrics["classification_report"]
        for cls_name in xgboost_service.label_names:
            if cls_name in rep:
                c_metrics = rep[cls_name]
                print(f"  {cls_name:15s} Precision: {c_metrics['precision']:.3f} | Recall: {c_metrics['recall']:.3f} | F1: {c_metrics['f1-score']:.3f}")

        # Register in model_registry
        reg_doc = await xgboost_service.register_model(results, dataset_version="synth-seed-42")
        print(f"\n[SUCCESS] Registered in MongoDB model_registry (ID: {reg_doc.get('_id')}) as active model version.")
    finally:
        await DatabaseManager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
