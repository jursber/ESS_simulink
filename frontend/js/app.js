// ===== app.js =====
window.App = window.App || { state: {}, charts: {}, flow: {}, analysis: {}, params: {}, compare: {} };

// --- 状态 ---
let state = { scenarios: [], currentScenario: null, options: null, result: null };

// --- API ---
const API = '/api';
async function api(path, opts = {}) {
  const res = await fetch(API + path, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(err.detail || 'API Error'); }
  return res.json();
}

// --- 初始化 ---
async function init() {
  try {
    const [scenarios, options] = await Promise.all([api('/scenarios'), api('/options')]);
    state.scenarios = scenarios;
    state.options = options;
    populateSelects();
    if (scenarios.length > 0) selectScenario(scenarios[0].id);
  } catch (e) {
    console.error('Init failed:', e);
  }
}

function populateSelects() {
  const { pricing_modes, business_models, settlement_modes, contract_profiles, dayahead_profiles } = state.options;
  fillSelect('sel-pm', pricing_modes);
  fillSelect('sel-bm', business_models);
  fillSelect('sel-settlement', settlement_modes);
  fillSelect('sel-contract', contract_profiles);
  fillSelect('sel-dayahead', dayahead_profiles);
  fillScenarioSelect('sel-scenario');
}

function fillSelect(id, items) {
  const sel = document.getElementById(id);
  sel.innerHTML = items.map(it => `<option value="${it.value}">${it.label}</option>`).join('');
}

function fillScenarioSelect(id) {
  const sel = document.getElementById(id);
  sel.innerHTML = state.scenarios.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
}

async function selectScenario(id) {
  state.currentScenario = id;
  document.getElementById('sel-scenario').value = id;
  await runCalculation();
}

// --- 导航 ---
let currentPage = 'analysis';
let paramsDirty = false;

function markParamsDirty() { paramsDirty = true; }

function bindDirtyTracking() {
  document.querySelectorAll('#params-content input, #params-content select').forEach(el => {
    el.addEventListener('change', markParamsDirty);
    el.addEventListener('input', markParamsDirty);
  });
}

// 覆盖 renderPanelContent，在渲染后绑定 dirty tracking
const _origRenderPanel = typeof renderPanelContent === 'function' ? renderPanelContent : null;

document.querySelectorAll('.top-nav-item[data-page]').forEach(item => {
  item.addEventListener('click', async () => {
    const page = item.dataset.page;
    // dirty check
    if (currentPage === 'params' && paramsDirty) {
      if (!confirm('当前修改未保存，切换后将丢失。是否继续？')) return;
      paramsDirty = false;
    }
    currentPage = page;
    document.querySelectorAll('.top-nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    document.querySelectorAll('.page-wrap').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');
    // 加载按钮状态
    const btnLoad = document.querySelector('.topbar-actions .btn');
    if (btnLoad) btnLoad.disabled = (page === 'params');
    if (page === 'params') { await App.params.loadGlobalParams(); App.params.initParamsMenu(); }
  });
});

function loadScenarios() { init(); }
function saveScenario() { alert('保存方案功能待实现'); }
function resetParams() {
  if (currentPage === 'params') {
    if (!confirm('这会将当前页面所有参数重置为系统初始值，但您已录入的自定义数据不会被删除。是否确定？')) return;
    paramsDirty = false;
    App.params.loadGlobalParams().then(() => {
      if (App.params.currentPanel) App.params.renderPanelContent(App.params.currentPanel);
    });
  } else {
    if (state.scenarios.length > 0) selectScenario(state.scenarios[0].id);
  }
}

// --- 参数变化监听 ---
document.querySelectorAll('.param-select').forEach(sel => {
  sel.addEventListener('change', () => {
    const tagCalc = document.getElementById('tag-calc');
    tagCalc.textContent = '参数已修改';
    tagCalc.classList.remove('done');
  });
});

// --- App 命名空间注册 ---
App.state = state;
App.api = api;
App.init = init;
App.selectScenario = selectScenario;
App.fillSelect = fillSelect;
App.markParamsDirty = markParamsDirty;
App.bindDirtyTracking = bindDirtyTracking;
App.loadScenarios = loadScenarios;
App.saveScenario = saveScenario;
App.resetParams = resetParams;
App.getCurrentPage = () => currentPage;
App.setCurrentPage = (p) => { currentPage = p; };
App.getParamsDirty = () => paramsDirty;
App.setParamsDirty = (v) => { paramsDirty = v; };

