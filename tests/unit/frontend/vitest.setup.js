import fs from 'fs';
import path from 'path';

const _origReadFileSync = fs.readFileSync.bind(fs);
const INCLUDE_RE = /^[ \t]*<!--\s*@include\s+([a-zA-Z0-9_./-]+)\s*-->[ \t]*$/gm;
const SUBMODULE_IMPORT_RE = /^import\s+\{[^}]+\}\s+from\s+['"]\.\/((?:settings|chat)\/[a-zA-Z0-9_.-]+\.js)['"];?(?:\s*\/\/.*)?\s*$/gm;

function expandIndexIncludes(text, baseDir) {
  if (typeof text !== 'string' || !text.includes('<!-- @include ')) {
    return text;
  }
  return text.replace(INCLUDE_RE, (_match, relPath) => {
    const fullPath = path.resolve(baseDir, relPath);
    const partial = _origReadFileSync(fullPath, 'utf-8');
    return partial.endsWith('\n') ? partial.slice(0, -1) : partial;
  });
}

function expandStudioSubmodules(text, baseDir, prefix) {
  if (typeof text !== 'string' || !text.includes(prefix)) {
    return text;
  }
  const appended = [];
  let match;
  SUBMODULE_IMPORT_RE.lastIndex = 0;
  while ((match = SUBMODULE_IMPORT_RE.exec(text)) !== null) {
    const relPath = match[1];
    if (!relPath.startsWith(prefix.slice(2))) continue;
    const fullPath = path.resolve(baseDir, relPath);
    if (fs.existsSync(fullPath)) {
      appended.push(_origReadFileSync(fullPath, 'utf-8'));
    }
  }
  return appended.length ? `${text}\n${appended.join('\n')}` : text;
}

fs.readFileSync = function patchedReadFileSync(filePath, options, ...rest) {
  const res = _origReadFileSync(filePath, options, ...rest);
  if (typeof res === 'string' && typeof filePath === 'string') {
    const norm = filePath.replace(/\\/g, '/');
    if (norm.endsWith('/src/web/templates/index.html') || norm === 'src/web/templates/index.html') {
      return expandIndexIncludes(res, path.dirname(filePath));
    }
    if (
      norm.endsWith('/src/web/static/modules/studios/settings.js') ||
      norm === 'src/web/static/modules/studios/settings.js'
    ) {
      return expandStudioSubmodules(res, path.dirname(filePath), './settings/');
    }
    if (
      norm.endsWith('/src/web/static/modules/studios/chat.js') ||
      norm === 'src/web/static/modules/studios/chat.js'
    ) {
      return expandStudioSubmodules(res, path.dirname(filePath), './chat/stream_bubble.js');
    }
  }
  return res;
};
