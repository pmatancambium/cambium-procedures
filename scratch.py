from pymongo import MongoClient

# MongoDB connection details
mongo_connection_string = "mongodb+srv://pmatan:Tc2s2uWKmA96DSbR@cluster0.ry1vbyd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo_db_name = "cambium-procedures"
mongo_collection_name = "procedures"

def delete_all_documents():
    try:
        # Create a MongoDB client
        client = MongoClient(mongo_connection_string)
        
        # Connect to the database
        db = client[mongo_db_name]
        
        # Access the collection
        collection = db[mongo_collection_name]
        
        # Delete all documents from the collection
        result = collection.delete_many({})
        
        print(f"Deleted {result.deleted_count} documents from the '{mongo_collection_name}' collection.")
    
    except Exception as e:
        print(f"An error occurred while deleting documents: {e}")

if __name__ == "__main__":
    delete_all_documents()
