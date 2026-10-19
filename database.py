import aiosqlite

DB_NAME = "shop.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица товаров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                price INTEGER,
                photo_url TEXT
            )
        """)
        # Таблица корзины
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, product_id)
            )
        """)
        # Добавим тестовые товары, если таблица пуста
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        count = (await cursor.fetchone())[0]
        if count == 0:
            await db.execute("INSERT INTO products (name, description, price, photo_url) VALUES (?, ?, ?, ?)",
                             ("Кружка", "Керамическая кружка 300мл", 500, "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=500"))
            await db.execute("INSERT INTO products (name, description, price, photo_url) VALUES (?, ?, ?, ?)",
                             ("Футболка", "Хлопковая футболка, размер M", 1500, "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500"))
            await db.execute("INSERT INTO products (name, description, price, photo_url) VALUES (?, ?, ?, ?)",
                             ("Блокнот", "Блокнот А5, 100 листов", 300, "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=500"))
            await db.commit()

async def get_products():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name, price, photo_url FROM products")
        return await cursor.fetchall()

async def get_product(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name, description, price, photo_url FROM products WHERE id = ?", (product_id,))
        return await cursor.fetchone()

async def add_to_cart(user_id, product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)
            ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = quantity + 1
        """, (user_id, product_id))
        await db.commit()

async def get_cart(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT p.id, p.name, p.price, c.quantity 
            FROM cart c JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = ?
        """, (user_id,))
        return await cursor.fetchall()

async def clear_cart(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()

