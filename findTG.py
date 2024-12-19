from telethon import TelegramClient
import re
import openai
from pymongo import MongoClient


 
openai.api_key = 'YOUR_OPENAI_API_KEY'
api_id = 'YOUR_API_ID' 
api_hash = 'YOUR_API_HASH'
client = TelegramClient('session_name', api_id, api_hash)

# Database setup
def setup_database():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['expat_groups']
    groups = db['groups']
    group_users = db['group_users']
    matches = db['matches']
    return db

# Save group metadata to the database
def save_group_data(db, group_name, description):
    groups = db['groups']
    groups.insert_one({'group_name': group_name, 'description': description})

# Save interesting users to the database
def save_users(db, group_name, users):
    group_users = db['group_users']
    for user_id, username, score, hobbies, location in users:
        group_users.insert_one({
            'group_name': group_name,
            'user_id': user_id,
            'username': username,
            'user_interest_score': score,
            'hobbies': hobbies,
            'location': location
        })

# Save matches to the database
def save_matches(db, matches):
    matches_col = db['matches']
    for match in matches:
        matches_col.insert_one({
            'user1': match['user1'],
            'user2': match['user2'],
            'common_hobbies': match['common_hobbies'],
            'location': match['location']
        })

# Extract location from group description
def get_location_and_hobbies_from_llm(description, messages, username):
    prompt = f"""
    Analyze the following group description and messages to determine the location of the group and suggest possible hobbies and interests for the user '{username}'.

    Group Description:
    {description}

    Messages:
    {messages}

    Provide the location and a list of hobbies or interests.
    """

    response = openai.Completion.create(
        engine="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=250  # Increased token limit to accommodate both tasks
    )

    output = response.choices[0].text.strip().split('\n')
    location = output[0] if output[0] else "Not specified"
    hobbies = output[1] if len(output) > 1 else "Not specified"

    return location, hobbies

# Analyze messages for keywords and compute interest scores
def analyze_messages(messages, keywords):
    interest_score = {}
    keyword_pattern = re.compile('|'.join(re.escape(word) for word in keywords), re.IGNORECASE)
    
    for message in messages:
        if message.message:
            match = keyword_pattern.search(message.message)
            if match:
                user_id = message.sender_id
                username = message.sender.username if message.sender else "unknown"
                interest_score[user_id] = interest_score.get(user_id, 0) + 1

    max_score = max(interest_score.values(), default=1)
    top_users = [(user_id, username, score / max_score) for user_id, username, score in interest_score.items()]
    return sorted(top_users, key=lambda x: -x[2])

# Fetch groups by common words and analyze
async def fetch_groups_and_users(keywords, limit=10):
    db = setup_database()
    all_users_data = []
    
    async with client:
        dialogs = await client.get_dialogs()
        
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                group_name = dialog.name
                print(f"Analyzing group: {group_name}")
                messages = await client.get_messages(dialog, limit=limit)
                top_users = analyze_messages(messages, keywords)
            
                
                for user_id, username, score in top_users:
                    user_messages = [message.message for message in messages if message.sender_id == user_id]
                    location, hobbies = get_location_and_hobbies_from_llm(dialog.entity.about, messages, username)
                    
                    all_users_data.append({
                        'username': username, 'hobbies': hobbies, 'location': location
                    })

                save_group_data(db, group_name, dialog.entity.about or "No description")
                save_users(db, group_name, [(user_id, username, score, hobbies, location) for user_id, username, score in top_users])

                print(f"Saved data for group: {group_name}")
        
        matches = find_matches(all_users_data)
        save_matches(db, matches)
        print(f"Saved {len(matches)} matches.")
        
        db.client.close()

# Find user matches using LLM
# Find user matches using LLM and send notifications
def find_matches(users_data):
    def get_similarity_score(hobbies1, hobbies2):
        set1 = set(hobbies1.split(', '))
        set2 = set(hobbies2.split(', '))
        return len(set1.intersection(set2)) / len(set1.union(set2))  # Jaccard index for similarity

    matches = []
    for i in range(len(users_data)):
        for j in range(i + 1, len(users_data)):
            user1 = users_data[i]
            user2 = users_data[j]
            if user1['location'] == user2['location']:  # Check if users are in the same location
                similarity_score = get_similarity_score(user1['hobbies'], user2['hobbies'])
                if similarity_score > 0.5:  # Threshold for considering as a match
                    matches.append({
                        'user1': user1['username'],
                        'user2': user2['username'],
                        'common_hobbies': ', '.join(set(user1['hobbies'].split(', ')).intersection(set(user2['hobbies'].split(', ')))),
                        'location': user1['location']
                    })
                    # Send notification to both users
                    client.send_message(user1['username'], f"Hi {user1['username']}, you have matched with {user2['username']} based on your common interests in {', '.join(set(user1['hobbies'].split(', ')).intersection(set(user2['hobbies'].split(', '))))}. You both are in {user1['location']}. It might be a good idea to meet!")
                    client.send_message(user2['username'], f"Hi {user2['username']}, you have matched with {user1['username']} based on your common interests in {', '.join(set(user1['hobbies'].split(', ')).intersection(set(user2['hobbies'].split(', '))))}. You both are in {user2['location']}. It might be a good idea to meet!")

    return matches

# Main function
async def main():
    keywords = ["expat", "relocation", "job", "networking", "community", "visa"]
    await fetch_groups_and_users(keywords)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())