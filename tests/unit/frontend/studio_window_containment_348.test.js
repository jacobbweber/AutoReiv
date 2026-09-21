import { describe, it, expect } from 'vitest';
import { loadPageHtml } from './template_helper.js';

describe('CARD-348 Studio Window Box Content Containment', () => {
  const html = loadPageHtml();

  it('tab-view.desktop-view-hosted enforces height via --dw-h CSS variable', () => {
    expect(html).toMatch(
      /body\.radical-desktop-demo\s+\.tab-view\.desktop-view-hosted\s*\{[^}]*height:\s*var\(--dw-h,\s*30rem\)\s*!important/s,
    );
  });

  it('view-factory.desktop-view-hosted does not set height: 100% !important (prevents viewport spillover)', () => {
    expect(html).not.toMatch(
      /#view-factory\.desktop-view-hosted\s*,\s*[^}]*#factoryStudio\s*\{[^}]*height:\s*100%\s*!important/s,
    );
    expect(html).not.toMatch(
      /body\.radical-desktop-demo\s+#view-factory\.desktop-view-hosted\s*\{[^}]*height:\s*100%\s*!important/s,
    );
    expect(html).toMatch(
      /body\.radical-desktop-demo\s+#view-factory\.desktop-view-hosted\s+#factoryStudio\s*\{[^}]*height:\s*100%\s*!important/s,
    );
  });

  it('view-lumina.desktop-view-hosted does not set height: 100% !important (prevents viewport spillover)', () => {
    expect(html).not.toMatch(
      /#view-lumina\.desktop-view-hosted\s*,\s*[^}]*#luminaStudio\s*\{[^}]*height:\s*100%\s*!important/s,
    );
    expect(html).not.toMatch(
      /body\.radical-desktop-demo\s+#view-lumina\.desktop-view-hosted\s*\{[^}]*height:\s*100%\s*!important/s,
    );
    expect(html).toMatch(
      /body\.radical-desktop-demo\s+#view-lumina\.desktop-view-hosted\s+#luminaStudio\s*\{[^}]*height:\s*100%\s*!important/s,
    );
  });

  it('view-education mobile media query excludes hosted desktop windows', () => {
    expect(html).toMatch(
      /#view-education:not\(\.desktop-view-hosted\)\s*\{[^}]*height:\s*100%\s*!important/s,
    );
  });

  it('CARD-314 comment and attributes remain intact for backward compatibility', () => {
    expect(html).toContain('CARD-314: Factory fills hosted');
    expect(html).toContain('data-card="314"');
  });
});