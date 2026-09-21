import fs from 'fs';
import path from 'path';

/**
 * Helper for frontend unit tests asserting on presentation markup and styling contracts [CARD-396].
 * Combines index.html with modular external stylesheets from src/web/static/css/*.
 */
export function loadPageHtml() {
  const indexPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const html = fs.readFileSync(indexPath, 'utf-8');
  const cssDir = path.resolve(__dirname, '../../../src/web/static/css');
  let allCss = '';
  if (fs.existsSync(cssDir)) {
    const files = fs.readdirSync(cssDir).filter((f) => f.endsWith('.css'));
    for (const f of files) {
      allCss += '\n' + fs.readFileSync(path.join(cssDir, f), 'utf-8');
    }
  }
  return html + '\n<style>\n' + allCss + '\n</style>';
}
