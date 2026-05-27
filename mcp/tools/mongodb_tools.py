import os
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient

# Fallback string for local dev or hackathon sandbox clusters
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://localhost")
DB_NAME = os.getenv("MONGO_DB_NAME", "migration_knowledgebase")

# Initialize the async MongoDB cluster client
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client[DB_NAME]

async def query_migration_knowledgebase(query_string: str, framework_context: str = None) -> Dict[str, Any]:
    """
    Executes an Atlas Vector Search query against documentation embedding matrices.
    """
    try:
        # 1. Generate text embeddings from the query string using a mock placeholder 
        # (Replace this with a real call to an embedding model like 'text-embedding-004' if needed)
        query_vector = [0.0] * 768  # Simulating a 768-dimension embedding array
        
        # 2. Build out the standard MongoDB Atlas Vector Search aggregation stage
        vector_search_stage = {
            "$vectorSearch": {
                "index": "vector_index",      # Your Atlas vector index design identifier
                "path": "embedding",          # Document schema key containing array floats
                "queryVector": query_vector,
                "numCandidates": 10,
                "limit": 3
            }
        }
        
        pipeline = [vector_search_stage]
        
        # 3. Apply metadata filtering criteria if a context limit like 'pydantic_v2' is given
        if framework_context:
            vector_search_stage["$vectorSearch"]["filter"] = {
                "framework": {"$eq": framework_context}
            }
            
        # 4. Fire the query pipeline against the collections block
        collection = db["documentation_matches"]
        cursor = collection.aggregate(pipeline)
        
        results = []
        async for doc in cursor:
            results.append({
                "topic": doc.get("topic", "Unknown migration paradigm"),
                "legacy_syntax": doc.get("legacy_syntax", ""),
                "updated_syntax": doc.get("updated_syntax", ""),
                "import_change": doc.get("import_change", ""),
                "notes": doc.get("notes", "")
            })
            
        return {"documentation_matches": results}
        
    except Exception as e:
        return {"error": f"MongoDB vector match failed: {str(e)}"}