import { describe, it, expect } from 'vitest';
import {
  buildMcpSaveBody,
  formatMcpCommandText,
  serverToSaveBody,
  splitMcpCommandText,
} from '../../../src/web/static/modules/studios/tools_studio_catalog.js';

/**
 * CARD-627 - MCP command round-trip: stored arrays stay intact on Test/Enable/Disable;
 * the form splits like a shell (quotes keep spaces; Windows backslashes stay literal).
 */

describe('CARD-627 splitMcpCommandText / formatMcpCommandText', () => {
  it('keeps quoted code as one argument (python -c ...)', () => {
    expect(splitMcpCommandText('python -c "import nonexistent_card516_mod"')).toEqual([
      'python', '-c', 'import nonexistent_card516_mod',
    ]);
    expect(splitMcpCommandText("python -c 'import sys; print(1)'")).toEqual([
      'python', '-c', 'import sys; print(1)',
    ]);
  });

  it('keeps Windows path spaces and literal backslashes', () => {
    const line = '"C:\\Program Files\\Python\\python.exe" -c "print(1)"';
    expect(splitMcpCommandText(line)).toEqual([
      'C:\\Program Files\\Python\\python.exe', '-c', 'print(1)',
    ]);
  });

  it('format then split round-trips spaced args', () => {
    const cmd = ['python', '-c', 'import sys; print(1)'];
    expect(splitMcpCommandText(formatMcpCommandText(cmd))).toEqual(cmd);
    const win = ['C:\\Program Files\\app\\server.exe', '--arg', 'two words'];
    expect(splitMcpCommandText(formatMcpCommandText(win))).toEqual(win);
  });
});

describe('CARD-627 buildMcpSaveBody uses shell split', () => {
  it('does not re-split quoted -c code on spaces', () => {
    const built = buildMcpSaveBody({
      name: 'probe',
      transport: 'stdio',
      commandText: 'python -c "import nonexistent_card516_mod"',
      enabled: true,
    });
    expect(built.ok).toBe(true);
    expect(built.body.command).toEqual(['python', '-c', 'import nonexistent_card516_mod']);
  });
});

describe('CARD-627 serverToSaveBody keeps the stored array', () => {
  it('Disable/Enable/Test body matches the stored command byte-for-byte', () => {
    const server = {
      name: 'c627',
      transport: 'stdio',
      command: ['python.exe', '-c', 'import nonexistent_card516_mod'],
      url: null,
      headers: null,
      env: { A: '1' },
      enabled: true,
    };
    const body = serverToSaveBody(server, false);
    expect(body.command).toEqual(['python.exe', '-c', 'import nonexistent_card516_mod']);
    expect(body.command).not.toBe(server.command);
    expect(body.enabled).toBe(false);
    expect(body.env).toEqual({ A: '1' });
    const again = serverToSaveBody({ ...server, enabled: false }, true);
    expect(again.command).toEqual(server.command);
    expect(again.enabled).toBe(true);
  });

  it('never joins then whitespace-splits a spaced path argument', () => {
    const server = {
      name: 'win',
      transport: 'stdio',
      command: ['C:\\Program Files\\Python\\python.exe', '-c', 'print(1)'],
      enabled: true,
    };
    expect(serverToSaveBody(server, true).command).toEqual(server.command);
  });
});
