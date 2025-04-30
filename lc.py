import asyncio
import aiohttp
from DrissionPage import ChromiumPage
from bs4 import BeautifulSoup
from database import Database
from datetime import datetime, timedelta
import re
import urllib.parse
import os

# Initialize the database
db = Database()

# Get item hash name with full condition for the URL
def get_item_hashname(item_name, item_float):
    conditions = {
        "FN": "Factory New",
        "MW": "Minimal Wear",
        "FT": "Field-Tested",
        "WW": "Well-Worn",
        "BS": "Battle-Scarred"
    }
    
    condition_match = re.search(r'\b(FN|MW|FT|WW|BS)\b', item_float)
    if condition_match:
        item_condition = conditions.get(condition_match.group(1), "")
    else:
        item_condition = ""
    
    if not item_condition:
        print(f"Warning: item_float '{item_float}' not recognized.")

    full_item_hashname = f"{item_name.strip()} ({item_condition})" if item_condition else item_name.strip()
    print(f"Constructed item hash name: {full_item_hashname}")
    
    return full_item_hashname

# Store prices in a text file
def store_price_in_file(item_name, price):
    with open('prices.txt', 'a', encoding='utf-8') as f:
        f.write(f"{item_name} - {price}\n")

# Retrieve price from file if available
def get_price_from_file(item_name):
    if not os.path.exists('prices.txt'):
        return None
    
    with open('prices.txt', 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().rsplit(' - ', 1)
            if len(parts) != 2:
                continue  # Skip malformed lines
            stored_item, stored_price = parts
            if stored_item == item_name:
                return stored_price
    return None

# Manually set session token
def get_manual_cookies():
    return {
        'session': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdGVhbV9pZCI6Ijc2NTYxMTk5MTY5NTk2NjY0Iiwibm9uY2UiOjAsImltcGVyc29uYXRlZCI6ZmFsc2UsImlzcyI6ImNzdGVjaCIsImV4cCI6MTcyODM0NzQ2NH0.jJZu6Qz4NeN4oX7-FoeFszZxb7cRvqkVU4Nq7qQRWSI'}

# Global flag and timestamp for API pause
api_pause = False
api_resume_time = None

# Background task to handle API pause without blocking
async def pause_api(duration):
    global api_pause, api_resume_time
    api_pause = True
    api_resume_time = datetime.now() + timedelta(seconds=duration)
    print(f"Pausing API requests for {duration // 60} minutes.")
    await asyncio.sleep(duration)
    api_pause = False
    print("Resuming API requests.")

# Fetch item price with manually set session token, or retrieve from file
async def get_item_price(session, item_hashname):
    global api_pause, api_resume_time

    # Try to retrieve price from the file first
    stored_price = get_price_from_file(item_hashname)
    if stored_price:
        print(f"Item - {item_hashname}: {stored_price} (retrieved from file)")
        return stored_price

    # If the API is paused, skip making the request and return 0
    if api_pause:
        print(f"API paused (until {api_resume_time}). Skipping API request for {item_hashname}.")
        return 0
    
    # If the price is not found in the file, proceed with fetching it from the API
    encoded_item_hashname = urllib.parse.quote(item_hashname, safe='')
    url = f"https://csfloat.com/api/v1/listings?market_hash_name={encoded_item_hashname}"
    
    cookies = get_manual_cookies()
    
    try:
        async with session.get(url, cookies=cookies) as response:
            data = await response.json()
            if data and len(data) > 0:
                price = data[0].get('price', 0)
                print(f"Item - {item_hashname}: {price}")
                
                store_price_in_file(item_hashname, price)
                return price
            return 0
    except Exception as e:
        print(f"Error fetching item price: {e}")

        # If an error occurs, start a background task to pause API requests for 10 minutes
        asyncio.create_task(pause_api(600))
        return get_price_from_file(item_hashname) or 0

# Filter user data
async def filter_user(user, session):
    await insert_db(user, session)

# Insert user data into the database
async def insert_db(user, session):
    try:
        db.import_db(user)
    except Exception as e:
        print(f"Error inserting user into database: {e}")

# Check Steam profile
async def check_steam(data, session):
    activity = 0
    url = data['user_url']
    item_hashname = get_item_hashname(data['item_name'], data['item_float'])
    user_data = {
        "user_name": "",
        "hours": "-",
        "level": "0",
        "country": "-",
        "status": "Not Available",
        "image_url": data['image_url'],
        "avatar_url": data['avatar_url'],
        "user_url": data['user_url'],
        "item_name": data['item_name'],
        "item_float": data['item_float'],
        "history": data['history'],
        "item_price": await get_item_price(session, item_hashname),
        "active": False,
        "online": False
    }
    try:
        async with session.get(url) as res:
            text = await res.text()
            bs4 = BeautifulSoup(text, "html.parser")

            if any(keyword in bs4.find(class_="actual_persona_name").text.lower() for keyword in ["mr. monkey #", "skinport", "dmarket", "bot", "dashskins", "skinbaron"]):
                return False

            user_data["user_name"] = bs4.find(class_="actual_persona_name").text or ""

            level_span = bs4.find('span', class_="friendPlayerLevelNum")
            user_data['level'] = level_span.text if level_span else "0"

            recent_game_content = bs4.find_all(class_="game_info")
            for game in recent_game_content:
                game_details = BeautifulSoup(str(game), "html.parser")
                game_link = game_details.find("a")['href']
                if game_link == "https://steamcommunity.com/app/730":
                    hours_text = game_details.find(class_="game_info_details").text.strip()
                    user_data['hours'] = hours_text.split(" hrs")[0].replace(",", "") if "hrs" in hours_text else "-"

            user_data['active'] = activity >= 3

            country_img = bs4.find("img", class_="profile_flag")
            user_data['country'] = country_img['src'] if country_img else "-"

            status_header = bs4.find(class_="profile_in_game_header")
            user_data['status'] = status_header.text if status_header else "Not Available"
            user_data['online'] = user_data['status'] != "Currently Offline"

            await filter_user(user_data, session)
    except Exception as e:
        print(f"Error checking Steam profile: {e}")

# Check user in file and process
async def check_user(data, session):
    try:
        url = data['user_url']
        with open("users.txt", "r", encoding="utf-8") as users:
            if url not in users.read():
                with open("users.txt", "a", encoding="utf-8") as usersW:
                    usersW.write(url + "\n")
                await check_steam(data, session)
    except Exception as e:
        print(f"Error checking user: {e}")

# Scrape data from the page
async def scrap(p, session):
    bs4 = BeautifulSoup(p.html, "html.parser")

    trs = bs4.find_all("tr", class_="mat-mdc-row")
    for tr in trs:
        data = {
            "image_url": "",
            "avatar_url": "",
            "user_url": "",
            "item_name": "",
            "item_float": "",
            "history": "0"
        }
        try:
            name1 = tr.find(class_="prefix").text
            name2 = tr.find(class_="suffix").text
            item_name = name1 + " |" + name2.replace(" (Ruby)", " (Ruby)").replace(" (Phase 1)", " (Phase 1)").replace(" (Phase 2)", " (Phase 2)").replace(" (Phase 3)", " (Phase 3)").replace(" (Phase 4)", " (Phase 4)").replace(" (Emerald)", " (Emerald)")
            data['item_name'] = item_name

            image_container = tr.find(class_="icon")
            if image_container and image_container.find(class_="ng-star-inserted"):
                data['image_url'] = image_container.find(class_="ng-star-inserted")['src']

            user_avatar = tr.find(class_="playerAvatar")
            if user_avatar:
                data['user_url'] = user_avatar['href'].split("/inventory")[0]
                data['avatar_url'] = user_avatar.find(class_="ng-star-inserted")['src']

            history_btn = tr.find(class_="history-btn-container")
            if history_btn:
                badge_content = history_btn.find(class_="mat-badge-content")
                data['history'] = badge_content.text if badge_content else "0"

            data['item_float'] = tr.find(class_="float-container").text if tr.find(class_="float-container") else ""

            await check_user(data, session)
        except Exception as e:
            print(f"Error scraping data: {e}")

# Main loop
async def main():
    p = ChromiumPage()
    p.get('https://csfloat.com/')
    
    # Ensure login by interacting with the page if needed
    i = p.get_frame('@src^https://challenges.cloudflare.com/cdn-cgi')

    last_activity_time = datetime.now()  # Track the last activity time
    
    if p.ele("@class:user", timeout=10):
        p.get('https://csfloat.com/db?rarity=6&order=4&min=0&max=1&only=1&maxAge=1')
        async with aiohttp.ClientSession() as session:
            while True:
                if p.ele('@class:playerAvatar'):
                    last_activity_time = datetime.now()  # Update activity time when the page is active
                    await scrap(p, session)
                    await asyncio.sleep(7)
                    p.refresh()
                else:
                    # Check inactivity duration
                    if datetime.now() - last_activity_time > timedelta(minutes=1):
                        print("Website inactive for more than 2 minutes. Forcing refresh.")
                        p.refresh()
                        last_activity_time = datetime.now()  # Update activity time after refresh

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
