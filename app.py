from flask import Flask, request, render_template
from database import Database
import re

app = Flask(__name__)
db = Database()

@app.route("/")
def index():
    maxlevel = request.args.get("level")
    active = request.args.get("played")
    online = request.args.get("online")
    search = request.args.get("search") or ""
    max_history = request.args.get("history")
    item_search = request.args.get("item_search") or ""
    max_hours = request.args.get("max_hours")
    min_price = request.args.get("min_price")
    limit = int(request.args.get("limit", 50))  # Default to 50 if no limit is provided
    block_chinese = request.args.get("block_chinese")
    refresh_interval = request.args.get("refresh_interval")

    def gayofa(price):
        return price / 100

    def contains_chinese(text, country):
        chinese_flag_url = "https://community.akamai.steamstatic.com/public/images/countryflags/cn.gif"
        
        if text is None:
            text_contains_chinese = False
        else:
            text_contains_chinese = bool(re.search('[\u4e00-\u9fff]', str(text)))

        flag_is_chinese = country == chinese_flag_url

        return text_contains_chinese or flag_is_chinese
    
    def is_valid_int(value):
        try:
            int(value)
            return True
        except ValueError:
            return False

    listings = db.get_listings(maxlevel, active, online, search, limit)
    
    if block_chinese:
        listings = [lst for lst in listings if not contains_chinese(lst.user_name, lst.country)]

    if max_history and is_valid_int(max_history):
        listings = [lst for lst in listings if int(lst.history) <= int(max_history)]

    if max_hours and is_valid_int(max_hours):
        listings = [lst for lst in listings if is_valid_int(lst.hours) and int(lst.hours) <= int(max_hours)]

    if min_price and is_valid_int(min_price):
        listings = [lst for lst in listings if is_valid_int(lst.item_price) and gayofa(lst.item_price) >= float(min_price)]

    if item_search:
        listings = [lst for lst in listings if item_search.lower() in lst.item_name.lower()]

    return render_template(
        "index.html",
        listings=listings,
        int=int,
        gayofa=gayofa,
        maxlevel=maxlevel,
        active=active,
        online=online,
        search=search,
        max_history=max_history,
        block_chinese=block_chinese,
        item_search=item_search,
        max_hours=max_hours,
        min_price=min_price,
        refresh_interval=refresh_interval
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
