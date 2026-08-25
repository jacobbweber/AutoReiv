/**
 * Trailing-edge debounce utility [REQ-FE-004]
 * @param {Function} fn Function to debounce
 * @param {number} wait Milliseconds to wait
 * @returns {Function} Debounced function
 */
export function debounce(fn, wait = 100) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), wait);
  };
}
