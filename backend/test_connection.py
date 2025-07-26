import pymongo

try:
    # We'll use a timeout to ensure it doesn't hang indefinitely.
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)

    # The ismaster command is cheap and does not require auth.
    client.admin.command('ismaster')

    print("Successfully connected to MongoDB!")
    print(f"Connected to database: {client.get_database('conversation_history_db').name}")

except pymongo.errors.ServerSelectionTimeoutError as err:
    print("Could not connect to MongoDB.")
    print(f"Error: {err}")
except Exception as err:
    print("An unexpected error occurred.")
    print(f"Error: {err}")