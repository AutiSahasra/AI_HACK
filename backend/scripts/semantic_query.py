import sys
import os
import argparse
import asyncio

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import DatabaseManager
from app.services.minilm_service import minilm_service, MODEL_ID


async def main():
    parser = argparse.ArgumentParser(description="MiniLM 384-dimensional Semantic Retrieval CLI (PDF Section 6)")
    parser.add_argument("--query", type=str, default="database connections failing with timeout during high traffic checkout", help="Query symptom or problem text")
    parser.add_argument("--top_k", type=int, default=3, help="Number of matches to return (default: 3)")
    args = parser.parse_args()

    print("=" * 60)
    print(f" MiniLM Semantic Retrieval Query Demonstration")
    print("=" * 60)
    print(f"Model ID: {MODEL_ID} (384 dimensions)")
    print(f"Query: \"{args.query}\"\n")

    await DatabaseManager.connect()
    try:
        kb_col = DatabaseManager.get_collection("knowledge_articles")
        articles = await kb_col.find({}).to_list(100)

        if not articles:
            print("[WARN] No knowledge articles found in DB. Run generate_synthetic.py first!")
            return

        matches = minilm_service.retrieve_top_matches(
            query_text=args.query,
            corpus=articles,
            top_k=args.top_k,
        )

        print(f"Top {len(matches)} Semantically Similar Runbooks/Articles:")
        for idx, m in enumerate(matches, 1):
            print(f" {idx}. [{m['similarity_score']:.4f}] {m['id']}: {m['title']} ({m['category']})")
            print(f"    Summary: {m['summary'][:120]}...\n")
    finally:
        await DatabaseManager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
