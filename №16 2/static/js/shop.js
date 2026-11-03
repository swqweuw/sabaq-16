'use strict';

const $ = (selector) => document.querySelector(selector);
const state = { products: [], sizes: [], category: 'all', search: '', cart: [], promo: '', quoteId: 0 };
const money = (n) => new Intl.NumberFormat('ru-RU').format(n) + ' ₸';
const escapeHtml = (text) => String(text).replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

async function requestJson(url, options = {}) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Ошибка ${response.status}`);
  return payload;
}

function toast(message) {
  const box = $('#toast');
  box.textContent = message;
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { box.hidden = true; }, 6000);
}

function renderMenu() {
  const products = CoffeeCatalog.filterProducts(state.products, state.category, state.search);
  $('#menu-grid').innerHTML = products.length ? products.map(p => `
    <article class="drink-card" data-product-id="${p.id}">
      <div class="drink-art art-${escapeHtml(p.accent)}"><div class="art-ring"></div><div class="art-mug"><span>C.</span></div></div>
      <div class="drink-info">
        <div class="drink-tag">${p.category === 'coffee' ? 'КОФЕ' : p.category === 'tea' ? 'ЧАЙ' : 'ОСОБЕННОЕ'}</div>
        <h3>${escapeHtml(p.name)}</h3><p>${escapeHtml(p.description)}</p>
        <div class="drink-options">
          <label>Размер <select class="size-select" aria-label="Размер ${escapeHtml(p.name)}">
            ${state.sizes.map(s => `<option value="${s.id}">${escapeHtml(s.name)} ${s.price_delta ? '(+' + money(s.price_delta) + ')' : ''}</option>`).join('')}
          </select></label>
          <label>Подача <select class="temperature-select" aria-label="Подача ${escapeHtml(p.name)}"><option value="hot">Горячий</option><option value="iced">Со льдом</option></select></label>
        </div>
        <div class="drink-bottom"><strong>от ${money(p.base_price)}</strong><button class="add-button" type="button" data-add="${p.id}">+ Добавить</button></div>
      </div>
    </article>`).join('') : '<div class="empty-state">По вашему запросу ничего не найдено.</div>';
}

function renderCart() {
  const itemCount = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  $('#cart-count').textContent = String(itemCount);
  const panel = $('#cart-items');
  if (!state.cart.length) {
    panel.innerHTML = '<p class="empty-cart">Здесь пока пусто. Добавь любимый напиток ☕</p>';
    return;
  }
  panel.innerHTML = state.cart.map((item, index) => {
    const p = state.products.find(p => p.id === item.product_id);
    const s = state.sizes.find(s => s.id === item.size_id);
    return `<div class="cart-line"><div class="cart-line-top"><div><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(s.name)} · ${item.temperature === 'hot' ? 'горячий' : 'со льдом'}</small></div><button class="remove-item" data-remove="${index}" title="Удалить" type="button">×</button></div>
      <div class="cart-line-bottom"><div class="quantity"><button type="button" data-minus="${index}">−</button><span>${item.quantity}</span><button type="button" data-plus="${index}">+</button></div><strong>${money((p.base_price + s.price_delta) * item.quantity)}</strong></div></div>`;
  }).join('');
}

function setTotals(quote) {
  $('#subtotal').textContent = money(quote?.subtotal ?? 0);
  $('#discount').textContent = '−' + money(quote?.discount ?? 0);
  $('#total').textContent = money(quote?.total ?? 0);
}

async function updateQuote(showErrors = false) {
  const requestId = ++state.quoteId;
  if (!state.cart.length) { setTotals(null); return; }
  try {
    const quote = await requestJson('/api/quote', {
      method: 'POST', body: JSON.stringify({ items: state.cart, promo_code: state.promo })
    });
    if (requestId === state.quoteId) setTotals(quote);
  } catch (error) {
    if (requestId === state.quoteId) {
      setTotals(null);
      if (showErrors) toast(error.message);
    }
  }
}

function cartChanged() { renderCart(); updateQuote(true); $('#order-result').hidden = true; }

function addProduct(productId, card) {
  const sizeId = Number(card.querySelector('.size-select').value);
  const temperature = card.querySelector('.temperature-select').value;
  const item = state.cart.find(item => item.product_id === productId && item.size_id === sizeId && item.temperature === temperature);
  if (item) {
    if (item.quantity >= 8) return toast('Лимит: 8 напитков одной позиции.');
    item.quantity += 1;
  } else {
    if (state.cart.length >= 12) return toast('Не более 12 разных позиций.');
    state.cart.push({ product_id: productId, size_id: sizeId, temperature, quantity: 1 });
  }
  cartChanged();
}

async function checkout() {
  if (!state.cart.length) return toast('Сначала выбери напиток.');
  const button = $('#submit-order');
  button.disabled = true;
  try {
    const customer_name = $('#customer-name').value.trim();
    const pickup_slot = document.getElementById('pickup-slot').value;
    const note = $('#order-note').value.trim();
    const order = await requestJson('/api/orders', {
      method: 'POST',
      body: JSON.stringify({ items: state.cart, promo_code: state.promo, customer_name, pickup_slot, note })
    });
    state.cart = [];
    state.promo = '';
    $('#promo-code').value = '';
    renderCart(); setTotals(null);
    const result = $('#order-result');
    result.replaceChildren();
    const heading = document.createElement('strong'); heading.textContent = `Заказ ${order.public_code} принят!`;
    const detail = document.createElement('p'); detail.textContent = `К оплате при получении: ${money(order.total)}.`;
    const track = document.createElement('a'); track.href = `/api/orders/${encodeURIComponent(order.public_code)}`;
    track.target = '_blank'; track.rel = 'noopener'; track.textContent = 'Посмотреть статус (JSON) ↗';
    result.append(heading, detail, track); result.hidden = false;
    toast('Заказ отправлен бариста.');
  } catch (error) {
    toast('Не удалось оформить заказ: ' + error.message);
  } finally {
    button.disabled = false;
  }
}

async function init() {
  try {
    const payload = await requestJson('/api/menu');
    state.products = payload.products; state.sizes = payload.sizes;
    renderMenu(); renderCart(); setTotals(null);
  } catch (error) {
    $('#menu-grid').textContent = 'Не удалось загрузить меню: ' + error.message;
  }
}

$('#menu-search').addEventListener('input', event => { state.search = event.target.value; renderMenu(); });
$('#category-tabs').addEventListener('click', event => {
  const button = event.target.closest('[data-category]');
  if (!button) return;
  state.category = button.dataset.category;
  document.querySelectorAll('[data-category]').forEach(b => b.classList.toggle('active', b === button));
  renderMenu();
});
$('#menu-grid').addEventListener('click', event => {
  const button = event.target.closest('[data-add]');
  if (button) addProduct(Number(button.dataset.add), button.closest('.drink-card'));
});
$('#cart-items').addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  const type = ['plus', 'minus', 'remove'].find(type => button.dataset[type] !== undefined);
  if (!type) return;
  const index = Number(button.dataset[type]);
  if (type === 'remove') state.cart.splice(index, 1);
  if (type === 'plus' && state.cart[index].quantity < 8) state.cart[index].quantity++;
  if (type === 'minus') { state.cart[index].quantity--; if (!state.cart[index].quantity) state.cart.splice(index, 1); }
  cartChanged();
});
$('#apply-promo').addEventListener('click', () => {
  state.promo = $('#promo-code').value.trim().toUpperCase();
  updateQuote(true);
});
$('#submit-order').addEventListener('click', checkout);
init();
