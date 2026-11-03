PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('coffee', 'tea', 'special')),
    description TEXT NOT NULL,
    base_price INTEGER NOT NULL CHECK (base_price >= 0),
    accent TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS sizes (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    price_delta INTEGER NOT NULL CHECK (price_delta >= 0)
);

CREATE TABLE IF NOT EXISTS product_sizes (
    product_id INTEGER NOT NULL REFERENCES products(id),
    size_id INTEGER NOT NULL REFERENCES sizes(id),
    PRIMARY KEY(product_id, size_id)
);

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    stock INTEGER NOT NULL CHECK (stock >= 0),
    min_stock INTEGER NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    unit TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipes (
    product_id INTEGER NOT NULL,
    size_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    amount INTEGER NOT NULL CHECK (amount > 0),
    PRIMARY KEY(product_id, size_id, ingredient_id),
    FOREIGN KEY (product_id, size_id) REFERENCES product_sizes(product_id, size_id)
);

CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY,
    percent INTEGER NOT NULL CHECK (percent BETWEEN 1 AND 80),
    min_subtotal INTEGER NOT NULL CHECK (min_subtotal >= 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_code TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    pickup_slot TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('new','preparing','ready','completed')),
    subtotal INTEGER NOT NULL CHECK(subtotal >= 0),
    discount INTEGER NOT NULL CHECK(discount >= 0),
    total INTEGER NOT NULL CHECK(total >= 0),
    coupon_code TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    size_id INTEGER NOT NULL REFERENCES sizes(id),
    temperature TEXT NOT NULL CHECK(temperature IN ('hot','iced')),
    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 8),
    unit_price INTEGER NOT NULL,
    line_total INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
