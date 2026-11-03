"""Локальный HTTP-сервер без сторонних библиотек (Python 3.10+)."""
from __future__ import annotations

import json
import mimetypes
import re
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from .db import DEFAULT_DB, PROJECT_ROOT, database_session, initialize_database
from .pricing import BusinessError, build_quote

STEPS = {'new': 'preparing', 'preparing': 'ready', 'ready': 'completed'}


def json_bytes(data) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class CoffeeHandler(BaseHTTPRequestHandler):
    server_version = 'CoffeeLab/1.0'

    def respond(self, code: int, payload, content_type: str = 'application/json; charset=utf-8'):
        body = json_bytes(payload) if isinstance(payload, (dict, list)) else payload
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise BusinessError('Некорректный размер запроса.', 400)
        if not 0 < length <= 100_000:
            raise BusinessError('JSON-запрос пустой или слишком большой.', 400)
        try:
            return json.loads(self.rfile.read(length).decode('utf-8'))
        except (UnicodeError, ValueError):
            raise BusinessError('Не удалось прочитать JSON.', 400)

    def route(self, method: str):
        path = urlsplit(self.path).path
        if method == 'GET' and path in ('/', '/manager'):
            file = PROJECT_ROOT / 'templates' / ('index.html' if path == '/' else 'manager.html')
            return self.respond(200, file.read_bytes(), 'text/html; charset=utf-8')
        if method == 'GET' and path.startswith('/static/'):
            static_root = (PROJECT_ROOT / 'static').resolve()
            file = (static_root / unquote(path[len('/static/'):])).resolve()
            if not file.is_relative_to(static_root) or not file.is_file():
                raise BusinessError('Файл не найден.', 404)
            mime = mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
            return self.respond(200, file.read_bytes(), mime + ('; charset=utf-8' if mime.startswith('text/') or mime == 'application/javascript' else ''))

        with database_session(self.server.database) as db:
            if method == 'GET' and path == '/api/menu':
                products = [dict(row) for row in db.execute('''
                    SELECT id, sku, name, category, description, base_price, accent
                      FROM products WHERE is_active=1 ORDER BY id''')]
                sizes = [dict(row) for row in db.execute('SELECT id,code,name,price_delta FROM sizes ORDER BY id')]
                return self.respond(200, {'products': products, 'sizes': sizes})

            if method == 'POST' and path == '/api/quote':
                quote = build_quote(db, self.read_json())
                return self.respond(200, quote.as_dict())

            if method == 'POST' and path == '/api/orders':
                payload = self.read_json()
                result = create_order(db, payload)
                return self.respond(201, result)

            matched = re.fullmatch(r'/api/orders/(CL-[A-Z0-9]{8})', path)
            if method == 'GET' and matched:
                public_code = matched.group(1)
                row = db.execute('SELECT * FROM orders WHERE public_code=?', (public_code,)).fetchone()
                if row is None:
                    raise BusinessError('Заказ не найден.', 404)
                order = dict(row)
                order['items'] = [dict(item) for item in db.execute('''
                    SELECT p.name,s.name AS size_name,oi.temperature,oi.quantity,
                           oi.unit_price,oi.line_total FROM order_items oi
                      JOIN products p ON oi.product_id=p.id
                      JOIN sizes s ON oi.size_id=s.id WHERE oi.order_id=?''', (row['id'],))]
                return self.respond(200, order)

            if method == 'GET' and path == '/api/admin/overview':
                orders = [dict(row) for row in db.execute('''
                    SELECT public_code,customer_name,pickup_slot,status,total,created_at
                      FROM orders ORDER BY id DESC LIMIT 50''')]
                summary = dict(db.execute('''
                    SELECT COUNT(*) AS order_count,
                           COALESCE(SUM(CASE WHEN status='completed' THEN total ELSE 0 END),0) AS revenue,
                           COALESCE(SUM(CASE WHEN status IN ('new','preparing') THEN 1 ELSE 0 END),0) AS active
                      FROM orders''').fetchone())
                inventory = [dict(row) for row in db.execute('''
                    SELECT id,name,stock,min_stock,unit FROM ingredients ORDER BY id''')]
                return self.respond(200, {'orders': orders, 'summary': summary, 'inventory': inventory})

            matched = re.fullmatch(r'/api/admin/orders/(CL-[A-Z0-9]{8})/advance', path)
            if method == 'POST' and matched:
                code = matched.group(1)
                try:
                    db.execute('BEGIN IMMEDIATE')
                    row = db.execute('SELECT status FROM orders WHERE public_code=?', (code,)).fetchone()
                    if row is None:
                        raise BusinessError('Заказ не найден.', 404)
                    next_status = STEPS.get(row['status'])
                    if next_status is None:
                        raise BusinessError('Заказ уже завершён.')
                    db.execute('UPDATE orders SET status=? WHERE public_code=?', (next_status, code))
                    db.commit()
                except BaseException:
                    db.rollback()
                    raise
                return self.respond(200, {'public_code': code, 'status': next_status})

            matched = re.fullmatch(r'/api/admin/ingredients/(\d+)/restock', path)
            if method == 'POST' and matched:
                ingredient_id = int(matched.group(1))
                payload = self.read_json()
                amount = payload.get('amount') if isinstance(payload, dict) else None
                if type(amount) is not int or not 1 <= amount <= 10000:
                    raise BusinessError('Количество должно быть целым числом от 1 до 10000.')
                updated = db.execute('UPDATE ingredients SET stock=stock+? WHERE id=?', (amount, ingredient_id))
                if updated.rowcount != 1:
                    raise BusinessError('Ингредиент не найден.', 404)
                return self.respond(200, {'ok': True})

        raise BusinessError('Адрес не найден.', 404)

    def handle_route(self, method: str):
        try:
            self.route(method)
        except BusinessError as error:
            self.respond(error.status, {'error': str(error)})
        except (sqlite3.Error, OSError, ValueError) as error:
            # Детали остаются в терминале, клиент не получает секреты и SQL.
            print(f'[server] {type(error).__name__}: {error}', flush=True)
            self.respond(500, {'error': 'Внутренняя ошибка сервера.'})

    def do_GET(self):
        self.handle_route('GET')

    def do_POST(self):
        self.handle_route('POST')

    def log_message(self, format, *args):
        if not getattr(self.server, 'quiet', False):
            super().log_message(format, *args)


def create_order(db: sqlite3.Connection, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise BusinessError('Укажите данные заказа в формате JSON.')
    customer = str(payload.get('customer_name') or '').strip()
    pickup = str(payload.get('pickup_slot') or '').strip()
    note = str(payload.get('note') or '').strip()
    if not 2 <= len(customer) <= 60:
        raise BusinessError('Укажите имя от 2 до 60 символов.')
    if pickup not in {f'{hour:02}:00' for hour in range(9, 21)}:
        raise BusinessError('Выберите корректное время самовывоза.')
    if len(note) > 250:
        raise BusinessError('Комментарий слишком длинный.')

    try:
        db.execute('BEGIN IMMEDIATE')
        quote = build_quote(db, payload)
        code = 'CL-' + uuid4().hex[:8].upper()
        created_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
        cursor = db.execute('''
            INSERT INTO orders(public_code,customer_name,pickup_slot,note,status,
                               subtotal,discount,total,coupon_code,created_at)
            VALUES (?,?,?,?,'new',?,?,?,?,?)
        ''', (code, customer, pickup, note, quote.subtotal, quote.discount,
              quote.total, quote.coupon_code, created_at))
        order_id = cursor.lastrowid
        for item in quote.items:
            db.execute('''
                INSERT INTO order_items(order_id,product_id,size_id,temperature,quantity,unit_price,line_total)
                VALUES (?,?,?,?,?,?,?)''',
                (order_id, item['product_id'], item['size_id'], item['temperature'],
                 item['quantity'], item['unit_price'], item['line_total']))
        for ingredient_id, quantity in quote.consumption.items():
            db.execute('UPDATE ingredients SET stock=stock-? WHERE id=?', (quantity, ingredient_id))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {'public_code': code, 'status': 'new', 'total': quote.total, 'message': 'Заказ принят.'}


def make_server(host: str = '127.0.0.1', port: int = 5000,
                database: str | Path = DEFAULT_DB, quiet: bool = False) -> ThreadingHTTPServer:
    initialize_database(database)
    server = ThreadingHTTPServer((host, port), CoffeeHandler)
    server.database = str(database)
    server.quiet = quiet
    daemon = True
    return server


def run_server(host: str = '127.0.0.1', port: int = 5000) -> None:
    server = make_server(host, port)
    print(f'COFFEELAB запущен: http://{host}:{port}', flush=True)
    print(f'Панель бариста: http://{host}:{port}/manager', flush=True)
    print('Остановить: Ctrl+C', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
