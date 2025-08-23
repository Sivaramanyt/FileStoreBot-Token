import motor.motor_asyncio
from config import DB_URI, DB_NAME

# Initialize MongoDB client and database
dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]

# Reference the 'users' collection
user_data = database['users']

# Default verification structure
default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

# Create a new user document with verification and view count fields
def new_user(user_id):
    return {
        '_id': user_id,
        'verify_status': {
            'is_verified': False,
            'verified_time': 0,
            'verify_token': "",
            'link': ""
        },
        'view_count': 0  # Initialize view count
    }

# Check if a user already exists in the database
async def present_user(user_id: int):
    found = await user_data.find_one({'_id': user_id})
    return bool(found)

# Add a new user document to the database
async def add_user(user_id: int):
    user = new_user(user_id)
    await user_data.insert_one(user)

# Get verification status for a given user
async def db_verify_status(user_id: int):
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('verify_status', default_verify)
    return default_verify

# Update verification status for a user
async def db_update_verify_status(user_id: int, verify: dict):
    await user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

# Get the entire list of user IDs (async generator)
async def full_userbase():
    user_docs = user_data.find()
    user_ids = [doc['_id'] async for doc in user_docs]
    return user_ids

# Delete a user document from the database
async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})

# Get the number of videos viewed by the user
async def get_view_count(user_id: int):
    user = await user_data.find_one({'_id': user_id})
    if user and 'view_count' in user:
        return user['view_count']
    return 0

# Increase the view count for the user by 1
async def increment_view_count(user_id: int):
    await user_data.update_one({'_id': user_id}, {'$inc': {'view_count': 1}})
    
        
