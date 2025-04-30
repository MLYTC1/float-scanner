from flask import Flask, request, render_template, abort
from database import Database
import re

app = Flask(__name__)
db = Database()

# List of allowed IPs
ALLOWED_IPS = [
    '212.58.114.101', '212.58.103.132', '188.129.254.239', '31.192.2.46',
    '188.169.155.171', '212.58.102.204', '188.169.60.165', '37.232.38.242',
    '178.134.158.128', '212.58.114.234', '212.58.103.63', '213.136.69.133',
    '213.166.70.154', '178.134.98.240', '155.133.22.13', '212.58.103.18',
    '188.121.202.87', '212.58.114.228', '82.211.154.207', '62.212.55.157','192.168.2.135'
]

# Limit access based on remote IP address
@app.before_request
def limit_remote_addr():
    if request.remote_addr not in ALLOWED_IPS:
        abort(403)  # Return a 403 Forbidden if the IP is not allowed

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

    # If item_search is provided, retrieve matching items with the given limit
    if item_search:
        listings = db.get_listings_by_item(item_search, limit)
    else:
        listings = db.get_listings(maxlevel, active, online, search, limit)
    
    if block_chinese:
        listings = [lst for lst in listings if not contains_chinese(lst.user_name, lst.country)]

    if max_history and is_valid_int(max_history):
        listings = [lst for lst in listings if int(lst.history) <= int(max_history)]

    if max_hours and is_valid_int(max_hours):
        listings = [lst for lst in listings if is_valid_int(lst.hours) and int(lst.hours) <= int(max_hours)]

    if min_price and is_valid_int(min_price):
        listings = [lst for lst in listings if is_valid_int(lst.item_price) and gayofa(lst.item_price) >= float(min_price)]

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

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
