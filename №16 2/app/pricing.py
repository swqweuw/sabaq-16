from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any
import sqlite3


class BusinessError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


@dataclass
class Quote:
    items: list[dict]
    subtotal: int
    discount: int
    total: int
    coupon_code: str | None
    consumption: dict[int, int]

    def as_dict(self) -> dict:
        return {
            'items': self.items,
            'subtotal': self.subtotal,
            'discount': self.discount,
            'total': self.total,
            'coupon_code': self.coupon_code,
        }


def _positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise BusinessError(f'Поле «{field}» должно быть положительным целым числом.')
    return value


def build_quote(db: sqlite3.Connection, payload: dict) -> Quote:
    if not isinstance(payload, dict):
        raise BusinessError('Ожидается JSON-объект.')

    raw_items = payload.get('items')
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 12:
        raise BusinessError('Добавьте от 1 до 12 разных позиций.')

    items = []
    consumption: dict[int, int] = defaultdict(int)
    distinct = set()
    subtotal = 0

    for raw in raw_items:
        if not isinstance(raw, dict):
            raise BusinessError('Некорректная позиция заказа.')
        product_id = _positive_int(raw.get('product_id'), 'product_id')
        size_id = _positive_int(raw.get('size_id'), 'size_id')
        quantity = _positive_int(raw.get('quantity'), 'quantity')
        if quantity > 8:
            raise BusinessError('Не более 8 напитков одного вида.')
        temperature = raw.get('temperature', 'hot')
        if temperature not in ('hot', 'iced'):
            raise BusinessError('Неизвестный способ подачи.')

        identifier = (product_id, size_id, temperature)
        if identifier in distinct:
            raise BusinessError('Повторяющиеся позиции нужно объединить.')
        distinct.add(identifier)

        product = db.execute('''
            SELECT p.id, p.name, p.base_price, s.name as size_name, s.price_delta
              FROM products p
              JOIN product_sizes ps ON ps.product_id=p.id
              JOIN sizes s ON s.id=ps.size_id
             WHERE p.id=? AND s.id=? AND p.is_active=1
        ''', (product_id, size_id)).fetchone()
        if product is None:
            raise BusinessError('Один из напитков или размеров недоступен.')

        recipe = db.execute('''
            SELECT r.ingredient_id, r.amount
              FROM recipes r
             WHERE r.product_id=? AND r.size_id=?
        ''', (product_id, size_id)).fetchall()
        if not recipe:
            raise BusinessError('Не удалось рассчитать состав выбранного напитка.')
        for part in recipe:
            consumption[part['ingredient_id']] += part['amount'] * quantity

        unit_price = product['base_price'] + product['price_delta']
        line_total = unit_price * quantity
        subtotal += line_total
        items.append({
            'product_id': product_id,
            'size_id': size_id,
            'name': product['name'],
            'size_name': product['size_name'],
            'temperature': temperature,
            'quantity': quantity,
            'unit_price': unit_price,
            'line_total': line_total,
        })

    for ingredient_id, required in consumption.items():
        ingredient = db.execute('SELECT name, stock, unit FROM ingredients WHERE id=?', (ingredient_id,)).fetchone()
        if ingredient is None:
            raise BusinessError('В карточке напитка обнаружен неизвестный компонент.')
        if ingredient['stock'] < required:
            raise BusinessError(f'Недостаточно запаса для заказа: {ingredient["name"]}.')

    coupon_code = str(payload.get('promo_code') or '').strip().upper()
    discount = 0
    if coupon_code:
        coupon = db.execute('SELECT * FROM coupons WHERE code=? AND is_active=1', (coupon_code,)).fetchone()
        if coupon is None:
            raise BusinessError('Промокод недействителен.')
        if subtotal < coupon['min_subtotal']:
            raise BusinessError('Сумма покупки недостаточна для этого промокода.')
        discount = (subtotal * coupon['percent'] + 50) // 100

    return Quote(items, subtotal, discount, subtotal - discount, coupon_code or None, dict(consumption))
