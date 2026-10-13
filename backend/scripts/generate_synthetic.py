import sys
import os
import argparse
import asyncio

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import DatabaseManager
from app.services.synthetic_generator import generate_synthetic_dataset


async def main():
    parser = argparse.ArgumentParser(description="Deterministic Synthetic Data Generator (PDF Section 9 & 13)")
    parser.add_argument("--count", type=int, default=350, help="Number of synthetic incidents to generate (default: 350)")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed for deterministic generation (default: 42)")
    parser.add_argument("--clear", action="store_true", default=True, help="Clear existing synthetic records before insert")
    args = parser.parse_args()

    print("=" * 60)
    print(f" Generating Synthetic Dataset (Count: {args.count}, Seed: {args.seed})")
    print("=" * 60)

    incidents, log_events, knowledge_articles = generate_synthetic_dataset(count=args.count, seed=args.seed)

    await DatabaseManager.connect()
    try:
        inc_col = DatabaseManager.get_collection("incidents")
        logs_col = DatabaseManager.get_collection("log_events")
        kb_col = DatabaseManager.get_collection("knowledge_articles")

        if args.clear:
            await inc_col.delete_many({"is_synthetic": True})
            await logs_col.delete_many({"is_synthetic": True})
            await kb_col.delete_many({"is_synthetic": True})
            print("[INFO] Cleared prior synthetic records.")

        await inc_col.insert_many(incidents)
        await logs_col.insert_many(log_events)
        await kb_col.insert_many(knowledge_articles)

        print(f"[OK] Inserted {len(incidents)} synthetic incident cases (all marked is_synthetic=True, label_source='synthetic_rule')")
        print(f"[OK] Inserted {len(log_events)} correlated log events with MiniLM embeddings")
        print(f"[OK] Inserted {len(knowledge_articles)} knowledge articles with 384-dim MiniLM vectors")
        print(f"[SAMPLE] First Incident: {incidents[0]['incident_key']} - {incidents[0]['title']}")
    finally:
        await DatabaseManager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
