INSERT INTO products(id, sku, name, category, description, base_price, accent) VALUES
(1, 'ESPRESSO', 'Эспрессо', 'coffee', 'Плотный вкус, шоколадные ноты.', 790, 'espresso'),
(2, 'LATTE', 'Латте', 'coffee', 'Мягкий кофе со сливочным молоком.', 1450, 'latte'),
(3, 'CAPPUCCINO', 'Капучино', 'coffee', 'Двойной акцент на кофе и пену.', 1350, 'cappuccino'),
(4, 'MATCHA', 'Матча-латте', 'special', 'Японский чай и бархатистое молоко.', 1650, 'matcha'),
(5, 'CHAI', 'Пряный чай латте', 'tea', 'Чай с ароматными специями и молоком.', 1450, 'chai'),
(6, 'BERRY', 'Ягодный чай', 'tea', 'Чай с насыщенным ягодным вкусом.', 1200, 'berry');

INSERT INTO sizes(id, code, name, price_delta) VALUES
(1, 'M', '300 мл', 0),
(2, 'L', '450 мл', 350);

INSERT INTO product_sizes(product_id, size_id)
SELECT p.id, s.id FROM products p CROSS JOIN sizes s;

INSERT INTO ingredients(id, code, name, stock, min_stock, unit) VALUES
(1, 'BEANS', 'Кофейные зёрна', 1200, 120, 'г'),
(2, 'MILK', 'Молоко', 9000, 1800, 'мл'),
(3, 'WATER', 'Вода', 20000, 2500, 'мл'),
(4, 'MATCHA_POWDER', 'Порошок матча', 200, 30, 'г'),
(5, 'BLACK_TEA', 'Чёрный чай', 500, 50, 'г'),
(6, 'SPICE', 'Пряная смесь', 4, 3, 'г'),
(7, 'BERRY_SYRUP', 'Ягодный сироп', 3000, 400, 'мл');

-- product_id, size_id, ingredient_id, amount
INSERT INTO recipes(product_id, size_id, ingredient_id, amount) VALUES
(1,1,1,18), (1,1,3,50),
(1,2,1,36), (1,2,3,100),
(2,1,1,18), (2,1,2,240),
(2,2,1,36), (2,2,2,320),
(3,1,1,18), (3,1,2,180),
(3,2,1,36), (3,2,2,260),
(4,1,4,5),  (4,1,2,220),
(4,2,4,8),  (4,2,2,300),
(5,1,5,6),  (5,1,6,2),  (5,1,2,240),
(5,2,5,10), (5,2,6,3),  (5,2,2,330),
(6,1,5,8),  (6,1,7,60), (6,1,3,250),
(6,2,5,12), (6,2,7,90), (6,2,3,360);

INSERT INTO coupons(code, percent, min_subtotal, is_active) VALUES
('WELCOME10', 10, 1500, 1),
('STUDENT15', 15, 2400, 1),
('OLD20', 20, 1000, 0);
