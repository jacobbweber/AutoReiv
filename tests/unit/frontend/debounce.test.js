import { describe, it, expect, vi } from 'vitest';
import { debounce } from '../../../src/web/static/modules/utils/debounce.js';

describe('debounce utility [REQ-FE-004]', () => {
  it('delays execution until wait time has elapsed', async () => {
    vi.useFakeTimers();
    const mockFn = vi.fn();
    const debounced = debounce(mockFn, 100);

    debounced();
    debounced();
    debounced();

    expect(mockFn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(99);
    expect(mockFn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(mockFn).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it('passes the latest arguments to the callback', () => {
    vi.useFakeTimers();
    const mockFn = vi.fn();
    const debounced = debounce(mockFn, 50);

    debounced('first');
    debounced('second');
    debounced('third');

    vi.advanceTimersByTime(50);
    expect(mockFn).toHaveBeenCalledWith('third');

    vi.useRealTimers();
  });
});
