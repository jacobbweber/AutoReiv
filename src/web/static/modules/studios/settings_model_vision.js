/**
 * CARD-475 (D2): per-model "Can view images" checkbox in the Settings model table.
 * Unknown models are text-only. Ticking the box tells AutoReiv the model takes pictures;
 * unticking it forces text-only. The backend stores it as an override
 * (POST /api/settings/model-capabilities) that beats provider metadata and the name guess.
 */

const SOURCE_LABELS = {
  override: 'set by you',
  provider: 'provider says yes',
  name: 'guessed from name',
  provider_rejected: 'provider refused images',
  default: 'text only',
};

export function visionSourceLabel(source) {
  return SOURCE_LABELS[source] || SOURCE_LABELS.default;
}

/** Table cell HTML for one discovered model row. `esc` is the shared escapeHtml. */
export function modelVisionCell(model, esc) {
  const id = esc(String(model?.id || ''));
  const checked = model?.can_view_images ? ' checked' : '';
  const label = esc(visionSourceLabel(model?.vision_source));
  return `<td class="p-2.5">
    <label class="inline-flex items-center gap-1.5 cursor-pointer" title="Tick if this model can view pictures. Unticked models only see the file name.">
      <input type="checkbox" class="model-vision-toggle accent-sky-500" data-model-id="${id}"${checked} aria-label="Can view images">
      <span class="model-vision-source text-[10px] text-slate-400">${label}</span>
    </label>
  </td>`;
}

/** Delegate checkbox changes on the model table body (wired once). */
export function wireModelVisionToggles(tbody, { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {}) {
  if (!tbody || !fetchFn || tbody.dataset?.visionWired === '1') return;
  if (tbody.dataset) tbody.dataset.visionWired = '1';
  tbody.addEventListener('change', async (event) => {
    const box = event.target;
    if (!box?.classList?.contains('model-vision-toggle')) return;
    const modelId = box.dataset?.modelId;
    if (!modelId) return;
    const wanted = !!box.checked;
    box.disabled = true;
    try {
      const res = await fetchFn('/api/settings/model-capabilities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId, vision: wanted }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      box.checked = !!data.can_view_images;
      const label = box.parentElement?.querySelector?.('.model-vision-source');
      if (label) label.textContent = visionSourceLabel(data.vision_source);
    } catch (err) {
      box.checked = !wanted;
      console.warn('[AutoReiv UI] Could not save "Can view images":', err);
    } finally {
      box.disabled = false;
    }
  });
}
