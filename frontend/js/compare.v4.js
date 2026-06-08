// ===== compare/workspace pages =====
(function () {
  var App = window.App;
  const fmt = (v, d = 2) => {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return '--';
    return Number(v).toLocaleString('zh-CN', { maximumFractionDigits: d, minimumFractionDigits: d });
  };
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = {
    lanes: [],
    scenarios: [],
    docs: [],
    activeDoc: null,
  };

  function scenarioOptions(selected) {
    return (App.state.scenarios || state.scenarios).map(s =>
      `<option value="${s.id}" ${s.id === selected ? 'selected' : ''}>${esc(s.name)}</option>`
    ).join('');
  }

  function pricingOptions(selected) {
    return (App.state.options?.pricing_modes || []).map(o =>
      `<option value="${o.value}" ${o.value === selected ? 'selected' : ''}>${esc(o.label)}</option>`
    ).join('');
  }

  function businessOptions(selected) {
    return (App.state.options?.business_models || []).map(o =>
      `<option value="${o.value}" ${o.value === selected ? 'selected' : ''}>${esc(o.label)}</option>`
    ).join('');
  }

  function ensureLanes() {
    const scenarios = App.state.scenarios || [];
    if (state.lanes.length || !scenarios.length) return;
    state.lanes = scenarios.slice(0, Math.min(4, scenarios.length)).map((s, i) => ({
      scenario_id: s.id,
      pricing_mode: i % 2 === 0 ? 'M1' : 'M3',
      business_model: ['B1', 'B3a', 'B2c', 'B4'][i] || 'B1',
      alias: `方案 ${String.fromCharCode(65 + i)}`,
    }));
  }

  async function ensureBaseData() {
    if (!App.state.options || !(App.state.scenarios || []).length) {
      const [scenarios, options] = await Promise.all([App.api('/scenarios'), App.api('/options')]);
      App.state.scenarios = scenarios;
      App.state.options = options;
    }
  }

  function renderLanes() {
    ensureLanes();
    const el = document.getElementById('compare-lanes');
    if (!el) return;
    el.innerHTML = state.lanes.map((lane, i) => `
      <div class="compare-lane">
        <button class="lane-remove" onclick="App.compare.removeLane(${i})" title="移除此列">&times;</button>
        <div class="lane-badge">${esc(lane.alias)}</div>
        <div class="params-field"><label>方案</label><select onchange="App.compare.updateLane(${i},'scenario_id',this.value)">${scenarioOptions(lane.scenario_id)}</select></div>
        <div class="params-field"><label>电价模式</label><select onchange="App.compare.updateLane(${i},'pricing_mode',this.value)">${pricingOptions(lane.pricing_mode)}</select></div>
        <div class="params-field"><label>商业模式</label><select onchange="App.compare.updateLane(${i},'business_model',this.value)">${businessOptions(lane.business_model)}</select></div>
      </div>
    `).join('');
  }

  function addLane() {
    if (state.lanes.length >= 4) return;
    const scenarios = App.state.scenarios || [];
    if (!scenarios.length) return;
    const idx = state.lanes.length;
    state.lanes.push({
      scenario_id: scenarios[idx % scenarios.length].id,
      pricing_mode: 'M1',
      business_model: 'B1',
      alias: `方案 ${String.fromCharCode(65 + idx)}`,
    });
    renderLanes();
  }

  function removeLane(i) {
    state.lanes.splice(i, 1);
    state.lanes.forEach((l, idx) => l.alias = `方案 ${String.fromCharCode(65 + idx)}`);
    renderLanes();
    runCompare();
  }

  function updateLane(i, key, value) {
    state.lanes[i][key] = value;
  }

  function loadFromSlots(slots) {
    if (!slots || !slots.length) return;
    state.lanes = slots.slice(0, 4).map((s, i) => ({
      scenario_id: s.scenarioId,
      pricing_mode: s.pricingMode || 'M1',
      business_model: s.businessModel || 'B1',
      alias: s.label || `方案 ${String.fromCharCode(65 + i)}`,
    }));
    renderLanes();
  }

  function bestClass(metric, rows, value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '';
    if (!['max', 'min'].includes(metric.direction)) return '';
    const vals = rows.map(r => r.metrics[metric.key]).filter(v => v !== null && v !== undefined && !Number.isNaN(Number(v))).map(Number);
    if (!vals.length) return '';
    const target = metric.direction === 'max' ? Math.max(...vals) : Math.min(...vals);
    return Math.abs(Number(value) - target) < 1e-9 ? 'best' : '';
  }

  function metricValue(metric, value) {
    if (metric.key === 'pv_self_rate' && value !== null && value !== undefined) return `${fmt(value * 100, 1)}%`;
    if (metric.unit === '%' && value !== null && value !== undefined) return `${fmt(value, 2)}%`;
    if (metric.unit === '-') return fmt(value, 4);
    return `${fmt(value, metric.unit === '次/日' ? 2 : 2)} ${metric.unit}`;
  }

  function renderCompareTable(data) {
    const wrap = document.getElementById('compare-matrix-wrap');
    if (!wrap) return;
    const rows = data.items || [];
    if (!rows.length) {
      wrap.innerHTML = '<div class="workspace-empty">暂无对比结果</div>';
      return;
    }
    const summary = rows.map(r => `
      <div class="compare-card">
        <div class="compare-card-title">${esc(r.name)}</div>
        <div class="compare-card-sub">${esc(r.pricing_mode_label)} · ${esc(r.business_model_label)} · ${esc(r.date)}</div>
        <div class="compare-card-kpis">
          <div><span>${fmt(r.metrics.total_welfare_wan)}</span><em>社会福利 万元</em></div>
          <div><span>${fmt(r.metrics.user_savings_wan)}</span><em>用户节费 万元</em></div>
          <div><span>${fmt(r.metrics.ess_irr_pct)}</span><em>储能 IRR %</em></div>
        </div>
      </div>
    `).join('');
    const tableRows = data.metrics.map(m => `
      <tr>
        <td class="metric-name"><span>${esc(m.label)}</span><em>${esc(m.direction)}</em></td>
        ${rows.map(r => `<td class="${bestClass(m, rows, r.metrics[m.key])}">${metricValue(m, r.metrics[m.key])}</td>`).join('')}
      </tr>
    `).join('');
    wrap.innerHTML = `
      <div class="compare-card-row">${summary}</div>
      <div class="workspace-table-card">
        <table class="data-table compare-table">
          <thead><tr><th>指标</th>${rows.map(r => `<th>${esc(r.name)}</th>`).join('')}</tr></thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    `;
  }

  async function runCompare() {
    await ensureBaseData();
    ensureLanes();
    renderLanes();
    const wrap = document.getElementById('compare-matrix-wrap');
    if (wrap) wrap.innerHTML = '<div class="loading">正在生成对比矩阵</div>';
    try {
      const data = await App.api('/compare', { method: 'POST', body: JSON.stringify({ items: state.lanes }) });
      renderCompareTable(data);
    } catch (e) {
      if (wrap) wrap.innerHTML = `<div class="workspace-empty danger">对比失败：${esc(e.message)}</div>`;
    }
  }

  async function loadScenariosPage() {
    await ensureBaseData();
    const body = document.getElementById('scenario-table-body');
    if (!body) return;
    body.innerHTML = '<tr><td colspan="8">加载中...</td></tr>';
    const list = await App.api('/scenarios');
    state.scenarios = list;
    App.state.scenarios = list;
    const details = await Promise.all(list.map(s => App.api(`/scenarios/${s.id}`).catch(() => null)));
    body.innerHTML = details.filter(Boolean).map(d => {
      const overrides = Object.keys(d.private_overrides || {}).length + Object.keys(d.ess_params || {}).length + Object.keys(d.financial_params || {}).length;
      return `
        <tr>
          <td><input class="table-input" value="${esc(d.name)}" onchange="App.scenarios.rename('${d.id}',this.value)"></td>
          <td>${esc(d.region)}</td>
          <td>${esc(d.pricing_mode)}</td>
          <td>${esc(d.business_model)}</td>
          <td>${esc(d.selected_date)}</td>
          <td>${overrides}</td>
          <td>${esc((d.created_at || '').slice(0, 10))}</td>
          <td>
            <button class="mini-action" onclick="App.scenarios.duplicate('${d.id}')">复制</button>
            <button class="mini-action" onclick="App.scenarios.use('${d.id}')">加载</button>
            <button class="mini-action danger" onclick="App.scenarios.remove('${d.id}')">删除</button>
          </td>
        </tr>
      `;
    }).join('');
    if (!body.innerHTML) body.innerHTML = '<tr><td colspan="8">暂无方案</td></tr>';
  }

  async function createScenario() {
    const name = prompt('请输入方案名称', `方案-${new Date().toLocaleDateString('zh-CN')}`);
    if (!name) return;
    await App.api('/scenarios', { method: 'POST', body: JSON.stringify({ name }) });
    await loadScenariosPage();
    await App.loadScenarios();
  }

  async function renameScenario(id, name) {
    await App.api(`/scenarios/${id}`, { method: 'PUT', body: JSON.stringify({ name }) });
    await App.loadScenarios();
  }

  async function duplicateScenario(id) {
    await App.api(`/scenarios/${id}/duplicate`, { method: 'POST', body: JSON.stringify({}) });
    await loadScenariosPage();
    await App.loadScenarios();
  }

  async function removeScenario(id) {
    if (!confirm('确认删除该方案？')) return;
    await App.api(`/scenarios/${id}`, { method: 'DELETE' });
    await loadScenariosPage();
    await App.loadScenarios();
  }

  async function useScenario(id) {
    App.selectScenario(id);
    document.querySelector('.top-nav-item[data-page="analysis"]')?.click();
  }

  async function loadModels() {
    const el = document.getElementById('model-catalog');
    if (!el) return;
    el.innerHTML = '<div class="loading">正在加载模型目录</div>';
    const data = await App.api('/models');
    el.innerHTML = data.categories.map(cat => `
      <div class="model-category">
        <div class="model-category-hd">${esc(cat.label)}</div>
        <div class="model-grid">
          ${cat.models.map(m => `
            <div class="model-card">
              <div class="model-card-hd"><span>${esc(m.name)}</span><em>${esc(m.status)}${m.draft_saved ? ' · 草稿已保存' : ''}</em></div>
              <div class="model-desc">${esc(m.description)}</div>
              <div class="model-params">
                ${(m.params || []).map(p => `
                  <label class="model-param">
                    <span>${esc(p.label)}</span>
                    <input ${p.editable ? '' : 'disabled'} value="${esc(p.value)}" data-model="${esc(m.id)}" data-param="${esc(p.key)}">
                    <em>${esc(p.unit)}</em>
                  </label>
                `).join('') || '<div class="model-empty">暂无可调超参</div>'}
              </div>
              <button class="mini-action" onclick="App.models.save('${esc(m.id)}')">保存超参草稿</button>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
  }

  async function saveModelParams(modelId) {
    const params = {};
    document.querySelectorAll(`input[data-model="${CSS.escape(modelId)}"]`).forEach(i => {
      params[i.dataset.param] = i.value;
    });
    await App.api(`/models/${encodeURIComponent(modelId)}/params`, { method: 'PUT', body: JSON.stringify(params) });
    alert('模型超参草稿已保存');
  }

  function mdToHtml(md) {
    return esc(md)
      .replace(/^# (.*)$/gm, '<h1>$1</h1>')
      .replace(/^## (.*)$/gm, '<h2>$1</h2>')
      .replace(/^### (.*)$/gm, '<h3>$1</h3>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n- (.*)/g, '<li>$1</li>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
  }

  async function loadDocs() {
    const data = await App.api('/docs');
    state.docs = data.docs || [];
    renderDocList();
    if (state.docs[0]) await openDoc(state.docs[0].id);
  }

  function renderDocList() {
    const list = document.getElementById('docs-list');
    if (!list) return;
    const q = (document.getElementById('docs-search')?.value || '').toLowerCase();
    const docs = state.docs.filter(d => !q || d.title.toLowerCase().includes(q) || d.category.toLowerCase().includes(q));
    list.innerHTML = docs.map(d => `
      <div class="docs-item ${state.activeDoc === d.id ? 'active' : ''}" onclick="App.docs.open('${esc(d.id)}')">
        <span>${esc(d.title)}</span><em>${esc(d.category)}</em>
      </div>
    `).join('');
  }

  async function openDoc(id) {
    state.activeDoc = id;
    renderDocList();
    const article = document.getElementById('docs-article');
    article.innerHTML = '<div class="loading">正在加载文档</div>';
    const doc = await App.api(`/docs/${id}`);
    article.innerHTML = `<div class="docs-article-hd"><span>${esc(doc.title)}</span><em>${esc(doc.category)}</em></div><div class="docs-content"><p>${mdToHtml(doc.content || '')}</p></div>`;
  }

  async function loadDataAssetsPanel() {
    return App.api('/data-assets');
  }

  App.compare = { init: runCompare, addLane, removeLane, updateLane, runCompare, loadFromSlots };
  App.scenarios = { load: loadScenariosPage, createScenario, rename: renameScenario, duplicate: duplicateScenario, remove: removeScenario, use: useScenario };
  App.models = { load: loadModels, save: saveModelParams };
  App.docs = { load: loadDocs, open: openDoc, filter: renderDocList };
  App.dataAssets = { load: loadDataAssetsPanel };

  document.querySelector('.top-nav-item[data-page="compare"]')?.addEventListener('click', () => setTimeout(runCompare, 0));
  document.querySelector('.top-nav-item[data-page="scenarios"]')?.addEventListener('click', () => setTimeout(loadScenariosPage, 0));
  document.querySelector('.top-nav-item[data-page="model-mgmt"]')?.addEventListener('click', () => setTimeout(loadModels, 0));
  document.querySelector('.top-nav-item[data-page="docs"]')?.addEventListener('click', () => setTimeout(loadDocs, 0));
})();
