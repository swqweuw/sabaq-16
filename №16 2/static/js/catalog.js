/* Чистая логика поиска. Можно тестировать без браузера через Node.js. */
(function (root) {
  'use strict';
  function filterProducts(products, category, query) {
    const needle = String(query || '').trim().toLocaleLowerCase('ru');
    return products.filter(product => {
      const categoryMatches = category === 'all' || product.category === category;
      const textMatches = !needle || `${product.name} ${product.description}`.toLocaleLowerCase('ru').includes(needle);
      return categoryMatches && textMatches;
    });
  }
  const api = { filterProducts };
  root.CoffeeCatalog = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
