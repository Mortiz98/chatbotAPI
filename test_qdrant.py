import asyncio
from services.vector_service import VectorService


async def main():
    print("🚀 Starting Qdrant test...\n")

    vector_service = VectorService()

    # 1. Create collection
    print("📦 Step 1: Create collection")
    vector_service.create_collection_if_not_exists()

    # 2. Add sample documents about learning
    print("\n📄 Step 2: Add sample documents")

    sample_documents = [
        {
            "text": "Machine Learning is a branch of artificial intelligence that allows computers to learn from data without being explicitly programmed.",
            "metadata": {"category": "ai", "topic": "machine_learning"},
        },
        {
            "text": "Python is an ideal programming language for beginners due to its clear and readable syntax. It is widely used in data science and web development.",
            "metadata": {"category": "programming", "topic": "python"},
        },
        {
            "text": "The Pomodoro technique is a time management method that divides work into 25-minute intervals separated by short breaks. It increases productivity and reduces fatigue.",
            "metadata": {"category": "productivity", "topic": "pomodoro"},
        },
        {
            "text": "Deep Learning uses neural networks with multiple layers to solve complex problems like image recognition and natural language processing.",
            "metadata": {"category": "ai", "topic": "deep_learning"},
        },
        {
            "text": "FastAPI is a modern and fast web framework for creating APIs with Python. It supports native typing, automatic validation with Pydantic, and interactive documentation generation.",
            "metadata": {"category": "programming", "topic": "fastapi"},
        },
        {
            "text": "The spaced repetition technique consists of reviewing study material at increasing intervals to improve long-term information retention.",
            "metadata": {"category": "memory", "topic": "spaced_repetition"},
        },
        {
            "text": "SQL (Structured Query Language) is a standard language for managing and manipulating relational databases. It is used to query, insert, update, and delete data.",
            "metadata": {"category": "databases", "topic": "sql"},
        },
        {
            "text": "The Feynman method consists of explaining a complex concept in a simple way as if you were teaching it to someone else. It identifies gaps in your understanding.",
            "metadata": {"category": "learning", "topic": "feynman"},
        },
    ]

    for doc in sample_documents:
        point_id = vector_service.add_document(doc["text"], doc["metadata"])
        print(f"   ✅ Added: {doc['metadata']['topic']}")

    # 3. View documents
    print("\n📚 Step 3: View all documents")
    docs = vector_service.get_all_documents()
    print(f"   Total documents: {len(docs)}")

    # 4. Test searches
    print("\n🔍 Step 4: Test searches\n")

    searches = [
        "how to learn programming",
        "memory techniques",
        "artificial intelligence",
        "python frameworks",
    ]

    for query in searches:
        print(f"   Query: '{query}'")
        results = vector_service.search(query, limit=3)
        for r in results:
            print(f"      - Score: {r['score']:.3f} | {r['text'][:60]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
