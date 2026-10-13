import sys
import os
import asyncio

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import DatabaseManager
from app.core.db_indexes import initialize_all_indexes


async def main():
    print("=" * 60)
    print(" MongoDB Schema & Index Initializer (Idempotent)")
    print("=" * 60)
    await DatabaseManager.connect()
    try:
        results = await initialize_all_indexes()
        for col_name, idx_list in results.items():
            print(f"[OK] Collection '{col_name}': {len(idx_list)} indexes created/verified")
            for idx in idx_list:
                print(f"     - {idx}")
        print("\nAll 5 collections initialized successfully:")
        print("  1. incidents")
        print("  2. log_events")
        print("  3. knowledge_articles")
        print("  4. analysis_runs")
        print("  5. model_registry")
    finally:
        await DatabaseManager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
