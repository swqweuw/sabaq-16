'use strict';
const money = n => new Intl.NumberFormat('ru-RU').format(n) + ' ₸';
const escapeHtml = str => String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const statusNames = { new: 'Новый', preparing: 'В работе', ready: 'Готов', completed: 'Выдан' };

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
  const result = await response.json();
  if (!response.ok) throw Error(result.error || `Ошибка ${response.status}`);
  return result;
}
function toast(message) {
  const box = document.querySelector('#toast'); box.hidden = false; box.textContent = message;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => box.hidden = true, 4500);
}
async function refresh() {
  try {
    const result = await api('/api/admin/overview');
    document.querySelector('#metric-orders').textContent = result.summary.order_count;
    document.querySelector('#metric-active').textContent = result.summary.active;
    document.querySelector('#metric-revenue').textContent = money(result.summary.revenue);
    const queue = document.querySelector('#orders-table');
    queue.innerHTML = result.orders.length ? `<table><thead><tr><th>Заказ</th><th>Время</th><th>Сумма</th><th>Статус</th><th></th></tr></thead><tbody>${result.orders.map(o => `
      <tr><td><strong>${escapeHtml(o.public_code)}</strong><small>${escapeHtml(o.customer_name)}</small></td><td>${escapeHtml(o.pickup_slot)}</td>
      <td>${money(o.total)}</td><td><span class="status status-${escapeHtml(o.status)}">${statusNames[o.status]}</span></td>
      <td>${o.status === 'completed' ? '✓' : `<button class="table-button" data-advance="${escapeHtml(o.public_code)}">Далее →</button>`}</td></tr>`).join('')}</tbody></table>` : '<p class="empty-state">Пока заказов нет.</p>';
    const inventory = document.querySelector('#inventory-table');
    inventory.innerHTML = `<table><thead><tr><th>Ингредиент</th><th>Запас</th><th>Пополнить</th></tr></thead><tbody>${result.inventory.map(i => `
      <tr><td>${escapeHtml(i.name)}</td><td><span class="${i.stock <= i.min_stock ? 'low-stock' : ''}">${i.stock} ${escapeHtml(i.unit)}</span></td>
      <td><button class="table-button" data-restock="${i.id}">+100</button></td></tr>`).join('')}</tbody></table>`;
  } catch (error) { toast(error.message); }
}
document.querySelector('#refresh-data').addEventListener('click', refresh);
document.querySelector('#orders-table').addEventListener('click', async event => {
  const button = event.target.closest('[data-advance]'); if (!button) return;
  try { await api(`/api/admin/orders/${encodeURIComponent(button.dataset.advance)}/advance`, { method: 'POST' }); await refresh(); }
  catch (error) { toast(error.message); }
});
document.querySelector('#inventory-table').addEventListener('click', async event => {
  const button = event.target.closest('[data-restock]'); if (!button) return;
  try { await api(`/api/admin/ingredients/${button.dataset.restock}/restock`, { method: 'POST', body: JSON.stringify({ amount: 100 }) }); await refresh(); }
  catch (error) { toast(error.message); }
});
refresh();
