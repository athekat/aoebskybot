import requests
import json
import os #To check if the previous JSON file exists
from datetime import datetime
from atproto import Client
import pytz #Buenos Aires time conversion

# -----------------------------
BLUESKY_IDENTIFIER = os.environ.get("BSKY_USERNAME")
BLUESKY_APP_PASSWORD = os.environ.get("BSKY_APP_PASSWORD")
# -----------------------------

# --- Buenos Aires Timezone ---
BUENOS_AIRES_TZ = pytz.timezone('America/Argentina/Buenos_Aires')


def make_bluesky_post(text_content):
    """
    Logs into Bluesky and sends a text post.
    """
    if not BLUESKY_IDENTIFIER or not BLUESKY_APP_PASSWORD:
        print("Bluesky credentials not configured. Skipping post.")
        print("Please set BLUESKY_IDENTIFIER and BLUESKY_APP_PASSWORD in the script.")
        return None

    client = Client()
    try:
        # Login to Bluesky
        client.login(BLUESKY_IDENTIFIER, BLUESKY_APP_PASSWORD)
        print("Successfully logged into Bluesky!")

        # Send the post
        response = client.send_post(text_content)
        print("Post created successfully!")
        print(f"URI: {response.uri}")
        print(f"CID: {response.cid}")
        return response
    except Exception as e:
        print(f"An error occurred while posting to Bluesky: {e}")
        return None

def check_player_statuses_and_post_changes(players):
    """
    Checks player statuses, compares with previous run, and posts changes to Bluesky.
    """
    PREVIOUS_STATUS_FILE = "mostrecentmatch.json"
    
    # 1. Load previous player statuses
    previous_results = {}
    if os.path.exists(PREVIOUS_STATUS_FILE):
        try:
            with open(PREVIOUS_STATUS_FILE, 'r') as f:
                previous_results = json.load(f)
            print(f"Loaded previous statuses from {PREVIOUS_STATUS_FILE}")
        except json.JSONDecodeError as e:
            print(f"Error reading previous JSON file ({PREVIOUS_STATUS_FILE}): {e}. Starting with empty previous data.")
            previous_results = {} # If the file is corrupted, treat as if no previous data exists
    else:
        print(f"No previous status file found at {PREVIOUS_STATUS_FILE}. This might be the first run.")

    current_results = {}  
    changed_posts = []   

    # 2. Fetch current player statuses
    for playerdic in players:
        player_name = playerdic['name']
        api_url = playerdic['api_url']
        
        # Default status for unknown or error cases
        outcome = "status unknown"
        finished_info = "" # Will store finished time or remain empty
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()

            if data['matches']:
                last_match = data['matches'][0]
                finished_raw = last_match.get('finished') # Use .get() to safely access key
                
                if finished_raw:
                    outcome = "finished playing at"
                    # Convert UTC to Buenos Aires time
                    utc_dt = datetime.fromisoformat(finished_raw.replace('Z', '+00:00')).replace(tzinfo=pytz.utc)
                    buenos_aires_dt = utc_dt.astimezone(BUENOS_AIRES_TZ)
                    finished_info = buenos_aires_dt.strftime("%H:%M (%Y-%m-%d)")
                else:
                    outcome = "is playing now."
                    finished_info = "" # Match is ongoing, no finished time
            else: 
                print(f"No recent matches found for player: {player_name}")
                outcome = "has no recent matches"
                finished_info = ""

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for player {player_name}: {e}")
            outcome = f"encountered an API error: {e}"
            finished_info = "" # Ensure empty on API error
        except json.JSONDecodeError:
            print(f"Error decoding JSON for player {player_name}. API might have returned invalid data.")
            outcome = "returned invalid data"
            finished_info = ""
        
        # Construct the full status message for comparison and posting
        status_message = f"{player_name} {outcome} {finished_info}".strip()
        current_results[player_name] = status_message

        # 3. Compare current status with previous status
        previous_status = previous_results.get(player_name) # .get() returns None if player was not in previous_results

        if previous_status is None:
            # This player is new, or this is the first run for this player
            print(f"NEW PLAYER STATUS: {status_message}")
            changed_posts.append(status_message)
        elif previous_status != status_message:
            # Player's status has changed since the last run
            print(f"STATUS CHANGED: {status_message} (Previously: {previous_status})")
            changed_posts.append(status_message)
        else:
            # Status is the same, no action needed for Bluesky
            print(f"NO CHANGE: {status_message}")

    # 4. Save the current results to be used as 'previous' in the next run
    try:
        with open(PREVIOUS_STATUS_FILE, 'w') as f:
            json.dump(current_results, f, indent=4) # indent=4 makes the JSON file human-readable
        print(f"\nUpdated player statuses saved to {PREVIOUS_STATUS_FILE}")
    except IOError as e:
        print(f"Error writing to file {PREVIOUS_STATUS_FILE}: {e}")

    # 5. Post all identified changes to Bluesky
    if changed_posts:
        print(f"\n--- Posting {len(changed_posts)} changed statuses to Bluesky ---")
        for post_text in changed_posts:
            print(f"Attempting to post: '{post_text}'")
            make_bluesky_post(post_text)

    else:
        print("\nNo status changes detected. No new posts to Bluesky.")

# Define the players to monitor
players = [
    {"name": "Carpincho", "api_url": "https://data.aoe2companion.com/api/matches?profile_ids=6446904&search=&page=1"},
    {"name": "alanthekat", "api_url": "https://data.aoe2companion.com/api/matches?profile_ids=1263162&search=&page=1"},
    {"name": "thexcarpincho", "api_url": "https://data.aoe2companion.com/api/matches?profile_ids=18660623&search=&page=1"},
    {"name": "Dicopato", "api_url": "https://data.aoe2companion.com/api/matches?profile_ids=255507&search=&page=1"},
    {"name": "Dicopatito", "api_url": "https://data.aoe2companion.com/api/matches?profile_ids=6237950&search=&page=1"},
    {"name": "Nanox", "api_url": "https://data.aoe2companion.com/api/matches?profile_ids=439001&search=&page=1"},
    {"name": "Sir Monkey", "api_url": "https://data.aoe2companion.com/api/matches?profile_ids=903496&search=&page=1"}
]

if __name__ == "__main__":
    # This block will be executed when the script is run directly
    check_player_statuses_and_post_changes(players)
