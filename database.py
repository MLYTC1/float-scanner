import sqlite3

class Database:
    
    def __init__(self):
        self.conn = sqlite3.connect('ponchiki.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_table()  # Ensure the table is created upon initialization
    
    def create_table(self):
        self.c.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT,
            item TEXT,
            hours TEXT,
            active TEXT,
            online TEXT,
            level TEXT,
            country TEXT,
            avatar TEXT,
            float TEXT,
            price TEXT,
            status TEXT,
            url TEXT,
            history TEXT,
            user_name TEXT
        )
        ''')
        self.conn.commit()

    def import_db(self, user):
        try:
            self.c.execute('''INSERT INTO listings(
                    image_url,
                    item,
                    hours,
                    active,
                    online,
                    level,
                    country,
                    avatar,
                    float,
                    price,
                    status,
                    url,
                    history,
                    user_name
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (user['image_url'], user['item_name'], user['hours'], user['active'], user['online'], 
                user['level'], user['country'], user['avatar_url'], user['item_float'], 
                user['item_price'], user['status'], user['user_url'], user['history'], user['user_name'])
            )
            self.conn.commit()
            print(f"{user['item_name']}      {user['level']}      {user['country']}")
        except Exception as error:
            print(error)
    
    def get_listings(self, maxlevel, active, online, search, limit):
        if maxlevel is None:
            maxlevel = 400
        
        query = "SELECT * FROM listings WHERE level < ?"
        params = [maxlevel]
        
        if active == "1":
            query += ' AND active = ?'
            params.append(active)
            
        if online == "1":
            query += ' AND online = ?'
            params.append(online)
            
        if search:
            query += " AND user_name LIKE ?"
            params.append(f'%{search}%')
        
        query += ' ORDER BY id DESC'
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        print(query)
    
        # Manually handling the cursor
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        finally:
            cursor.close()  # Make sure to close the cursor after use
        
        out = []
        for row in rows:
            listing = Listing(
                id=row[0],
                image=row[1],
                item_name=row[2],
                hours=row[3],
                level=row[4],
                country=row[5],
                user_avatar=row[6],
                item_float=row[7],
                item_price=row[8],
                online=row[9],
                active=row[10],
                status=row[11],
                user_url=row[12],
                history=row[13],
                user_name=row[14]
            )
            out.append(listing)
        
        return out


class Listing:
    id: str
    image: str
    item_name: str
    hours: str
    active: bool
    online: bool
    level: str
    country: str
    user_avatar: str
    item_float: str
    item_price: str
    status: str
    user_url: str
    history: str
    user_name: str
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return f"{self.item_name} {self.item_price} {self.user_name}"