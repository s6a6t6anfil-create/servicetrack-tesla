import test from 'node:test';
import assert from 'node:assert/strict';
import {money, searchParams, escapeHTML} from '../static/helpers.js';

test('money: exact currency formatting, zero and rounding', () => {
  // Arrange: server decimals arrive as strings; normalize only locale spaces.
  const cases = [['0.00', '0,00 ₴'], ['1234.56', '1 234,56 ₴'], ['1.236', '1,24 ₴']];
  for (const [value, expected] of cases) {
    const actual = money(value).replace(/\u00a0|\u202f/g, ' '); // Act
    assert.equal(actual, expected); // Assert
  }
});
test('money: non-finite and malformed values have a safe fallback', () => {
  for (const value of ['bad', '1,25', NaN, Infinity, -Infinity, undefined]) {
    assert.equal(money(value), '—');
  }
});
test('searchParams: exact order number and all order filters', () => {
  const params = searchParams('orders', ' st-0007 ', 'ready', true);
  assert.deepEqual(Object.fromEntries(params), {number:'st-0007', status:'ready', overdue:'true'});
});
test('searchParams: whitespace, partial numbers and query injection remain data', () => {
  assert.equal(searchParams('orders', '   ', '', false).toString(), '');
  assert.equal(searchParams('orders', 'ST-', '', false).get('search'), 'ST-');
  const params = searchParams('customers', ' A&B=1 + #? ', 'delivered', true);
  assert.deepEqual(Object.fromEntries(new URLSearchParams(params.toString())), {search:'A&B=1 + #?'});
});
test('escapeHTML: escapes all markup characters and preserves Ukrainian text', () => {
  const raw = `<img src="x" onerror='alert(1)'>& Україна`;
  const actual = escapeHTML(raw);
  assert.equal(actual, '&lt;img src=&quot;x&quot; onerror=&#39;alert(1)&#39;&gt;&amp; Україна');
});
test('escapeHTML: absent and scalar values are rendered predictably', () => {
  for (const [raw, expected] of [[null, ''], [undefined, ''], [0, '0'], [false, 'false']]) {
    assert.equal(escapeHTML(raw), expected);
  }
});
