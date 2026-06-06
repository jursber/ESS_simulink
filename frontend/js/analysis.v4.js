// ===== analysis.js =====

// --- 方案槽位 ---
const SLOT_NAMES = ['方案 A', '方案 B', '方案 C'];
let slots = [null, null, null]; // 3 个槽位

function getActiveSlots() {
  return slots.map((s, i) => s !== null ? i : -1).filter(i => i >= 0);
}

function refreshSlotUI() {
  slots.forEach((snap, i) => {
    const btn = document.getElementById(`slot-${i}`);
    if (!btn) return;
    btn.classList.toggle('active', snap !== null);
  });
  const hasActive = slots.some(s => s !== null);
  const compareBtn = document.getElementById('slot-compare');
  if (compareBtn) compareBtn.disabled = !hasActive;
}

function updateAddBtnState() {
  const btn = document.getElementById('slot-add');
  if (!btn) return;
  const tagCalc = document.getElementById('tag-calc');
  const isCalcDone = tagCalc && tagCalc.classList.contains('done');
  const hasEmpty = slots.some(s => s === null);
  btn.disabled = !isCalcDone || !hasEmpty;
}

function addSlot() {
  const emptyIdx = slots.findIndex(s => s === null);
  if (emptyIdx < 0) return;
  const tagCalc = document.getElementById('tag-calc');
  if (!tagCalc || !tagCalc.classList.contains('done')) return;

  const snap = {
    scenarioId: document.getElementById('sel-scenario').value,
    pricingMode: document.getElementById('sel-pm').value,
    businessModel: document.getElementById('sel-bm').value,
    settlementMode: document.getElementById('sel-settlement').value,
    contractProfile: document.getElementById('sel-contract').value,
    dayaheadProfile: document.getElementById('sel-dayahead').value,
    result: App.state.result ? JSON.parse(JSON.stringify(App.state.result)) : null,
    label: SLOT_NAMES[emptyIdx],
    timestamp: Date.now(),
  };
  slots[emptyIdx] = snap;
  refreshSlotUI();
  updateAddBtnState();

  tagCalc.textContent = '参数已修改';
  tagCalc.classList.remove('done');
}

function toggleSlot(i) {
  if (slots[i] === null) return;
  slots[i] = null;
  refreshSlotUI();
  updateAddBtnState();
}

function openCompareModal() {
  if (!slots.some(s => s !== null)) return;
  document.getElementById('modal-compare').style.display = 'flex';
}

function closeCompareModal(e) {
  if (e && e.target !== e.currentTarget) return;
  document.getElementById('modal-compare').style.display = 'none';
}

function onParamChange() {
  const tagCalc = document.getElementById('tag-calc');
  if (tagCalc) {
    tagCalc.textContent = '参数已修改';
    tagCalc.classList.remove('done');
  }
  updateAddBtnState();
}

document.querySelectorAll('.param-select').forEach(sel => {
  sel.addEventListener('change', onParamChange);
});

// --- 加载状态 ---
function setLoading(on) {
  const overlay = document.getElementById('loading-overlay');
  const btn = document.getElementById('btn-calc');
  if (overlay) overlay.classList.toggle('active', on);
  if (btn) {
    btn.disabled = on;
    btn.classList.toggle('loading', on);
    const txt = btn.querySelector('.btn-text');
    if (txt) txt.textContent = on ? '计算中...' : '开 始 仿 真';
  }
}

// --- Fade-in ---
function fadeInResults() {
  const cards = document.querySelectorAll('#analysis-center .card');
  cards.forEach((c, i) => {
    c.classList.remove('fade-in');
    void c.offsetWidth; // reflow
    c.style.animationDelay = (i * 0.08) + 's';
    c.classList.add('fade-in');
  });
}

// --- 千分位格式化 ---
function fmt(v, d) {
  return App.charts.fmtNum(v, d);
}

// --- 经济性评级 ---
const RATING_COLORS = {
  '极差': 'rating-极差',
  '较差': 'rating-较差',
  '差': 'rating-差',
  '达标': 'rating-达标',
  '优秀': 'rating-优秀',
  '无敌': 'rating-无敌',
};

function renderEconRatings(econRatings) {
  const config = {
    '终端用户': { val: 'econ-val-user', badge: 'econ-badge-user', suffix: ' 元/kWh' },
    '光伏投资': { val: 'econ-val-pv', badge: 'econ-badge-pv', suffix: '%' },
    '储能投资': { val: 'econ-val-ess', badge: 'econ-badge-ess', suffix: '%' },
    '售电公司': { val: 'econ-val-retail', badge: 'econ-badge-retail', suffix: ' 元/MWh' },
  };
  econRatings.forEach(r => {
    const c = config[r.subject];
    if (!c) return;
    const valEl = document.getElementById(c.val);
    if (valEl) valEl.textContent = r.value != null ? `${r.value}${c.suffix}` : '--';
    const badgeEl = document.getElementById(c.badge);
    if (badgeEl) {
      badgeEl.textContent = r.rating;
      badgeEl.className = 'econ-badge ' + (RATING_COLORS[r.rating] || 'rating-na');
    }
  });
}

// --- 光储投资分析 tab 切换 ---
let currentInvTab = 'ess';

function switchInvTab(tab) {
  const essCap = state.result?.overview?.ess_cap_mwh || 0;
  const pvCap = state.result?.overview?.pv_cap_kw || 0;
  if (essCap === 0 && pvCap === 0) return;
  if (tab === 'ess' && essCap === 0) return;
  if (tab === 'pv' && pvCap === 0) return;

  currentInvTab = tab;
  document.getElementById('tab-ess').classList.toggle('active', tab === 'ess');
  document.getElementById('tab-pv').classList.toggle('active', tab === 'pv');
  document.getElementById('inv-ess-content').style.display = tab === 'ess' ? '' : 'none';
  document.getElementById('inv-pv-content').style.display = tab === 'pv' ? '' : 'none';
  document.getElementById('inv-none-content').style.display = 'none';
}

function updateInvTabs(essCapMwh, pvCapKw) {
  const tabEss = document.getElementById('tab-ess');
  const tabPv = document.getElementById('tab-pv');
  const essContent = document.getElementById('inv-ess-content');
  const pvContent = document.getElementById('inv-pv-content');
  const noneContent = document.getElementById('inv-none-content');

  tabEss.classList.remove('inv-tab-disabled');
  tabPv.classList.remove('inv-tab-disabled');

  if (essCapMwh === 0 && pvCapKw === 0) {
    tabEss.classList.add('inv-tab-disabled');
    tabPv.classList.add('inv-tab-disabled');
    essContent.style.display = 'none';
    pvContent.style.display = 'none';
    noneContent.style.display = 'flex';
    currentInvTab = null;
  } else if (essCapMwh === 0) {
    tabEss.classList.add('inv-tab-disabled');
    switchInvTab('pv');
  } else if (pvCapKw === 0) {
    tabPv.classList.add('inv-tab-disabled');
    switchInvTab('ess');
  } else {
    switchInvTab(currentInvTab || 'ess');
  }
}

// --- 计算 ---
async function runCalculation() {
  const scenarioId = document.getElementById('sel-scenario').value;
  const pricingMode = document.getElementById('sel-pm').value;
  const businessModel = document.getElementById('sel-bm').value;
  const settlementMode = document.getElementById('sel-settlement').value;
  const contractProfile = document.getElementById('sel-contract').value;
  const dayaheadProfile = document.getElementById('sel-dayahead').value;

  setLoading(true);

  try {
    const result = await api('/calculate', {
      method: 'POST',
      body: JSON.stringify({
        scenario_id: scenarioId,
        pricing_mode: pricingMode,
        business_model: businessModel,
        wholesale_overrides: { settlement_mode: settlementMode, contract_curve_profile: contractProfile, dayahead_curve_profile: dayaheadProfile },
      }),
    });
    state.result = result;
    state.currentScenario = scenarioId;
    const tagCalc = document.getElementById('tag-calc');
    tagCalc.textContent = '计算完成';
    tagCalc.classList.add('done');
    renderResult(result);
    fadeInResults();
    updateAddBtnState();
  } catch (e) {
    console.error('Calculation failed:', e);
    alert('计算失败: ' + e.message);
  } finally {
    setLoading(false);
  }
}

// --- 渲染 ---
function renderResult(r) {
  const { time_series, overview, welfare, investment } = r;

  // 概览
  document.getElementById('lbl-ess').textContent = `${overview.ess_cap_mwh.toFixed(2)} MWh / ${(overview.ess_power_kw / 1000).toFixed(2)} MW`;
  document.getElementById('lbl-pv').textContent = overview.pv_cap_kw ? `${overview.pv_cap_kw.toFixed(0)} kWp` : '0 kWp';
  document.getElementById('lbl-flex').textContent = overview.flex_load_kw ? `${(overview.flex_load_kw / 1000).toFixed(2)} MW` : '0 MW';
  document.getElementById('lbl-prod').textContent = `${(overview.prod_load_mwh).toFixed(2)} MW`;

  document.getElementById('tag-pm').textContent = document.getElementById('sel-pm').selectedOptions[0]?.text || '合同分时';
  document.getElementById('tag-bm').textContent = document.getElementById('sel-bm').selectedOptions[0]?.text || '储售一体';

  // 多方收益
  document.getElementById('welfare-badge').textContent = `总社会福利提升 ${fmt(welfare.total_welfare_wan)} 万元`;
  document.getElementById('w-bill-no').textContent = `${fmt(welfare.user_bill_no_ess_wan)} 万`;
  document.getElementById('w-return').textContent = `${fmt(welfare.user_return_wan)} 万`;
  document.getElementById('w-total').textContent = `${fmt(welfare.user_total_wan)} 万`;

  const pvi = r.pv_investment;
  if (pvi) {
    const wPvOut = document.getElementById('w-inv-pv-out');
    const wPvSelf = document.getElementById('w-inv-pv-self');
    if (wPvOut) wPvOut.textContent = `${fmt(pvi.annual_feed_in_wan)} 万`;
    if (wPvSelf) wPvSelf.textContent = `${fmt(pvi.annual_self_wan)} 万`;
  }

  // 光储投资分析 - 储能
  document.getElementById('ess-fin-total').textContent = `${fmt(investment.initial_invest_wan)} 万元`;
  document.getElementById('ess-fin-irr').textContent = investment.irr_pct != null ? `${investment.irr_pct.toFixed(2)}%` : 'N/A';
  document.getElementById('ess-fin-roi').textContent = investment.roi_years != null ? `${investment.roi_years.toFixed(2)} 年` : 'N/A';
  document.getElementById('ess-fin-cf').textContent = `${fmt(investment.cum_cf_wan)} 万元`;
  document.getElementById('ess-op-daily-arb').textContent = `${fmt(investment.daily_arbitrage_yuan)} 元`;
  document.getElementById('ess-op-annual-arb').textContent = `${fmt(investment.annual_arbitrage_wan)} 万元`;
  document.getElementById('ess-op-charge').textContent = `${fmt(investment.total_charge_kwh)} kWh`;
  document.getElementById('ess-op-annual-charge').textContent = `${fmt(investment.annual_charge_mwh)} MWh`;
  document.getElementById('ess-op-discharge').textContent = `${fmt(investment.total_discharge_kwh)} kWh`;
  document.getElementById('ess-op-annual-discharge').textContent = `${fmt(investment.annual_discharge_mwh)} MWh`;
  document.getElementById('ess-op-cycles').textContent = `${investment.equivalent_cycles.toFixed(2)} 次`;
  document.getElementById('ess-op-annual-cycles').textContent = `${fmt(investment.annual_cycles)} 次`;

  // 光储投资分析 - 光伏
  if (pvi) {
    document.getElementById('pv-fin-total').textContent = `${fmt(pvi.initial_invest_wan)} 万元`;
    document.getElementById('pv-fin-irr').textContent = pvi.irr_pct != null ? `${pvi.irr_pct.toFixed(2)}%` : 'N/A';
    document.getElementById('pv-fin-roi').textContent = pvi.payback_years != null ? `${pvi.payback_years.toFixed(1)} 年` : 'N/A';
    document.getElementById('pv-fin-cf').textContent = `${fmt(pvi.cum_cf_wan)} 万元`;
    document.getElementById('pv-op-daily-out').textContent = `${fmt(pvi.daily_feed_in_yuan)} 元`;
    document.getElementById('pv-op-annual-out').textContent = `${fmt(pvi.annual_feed_in_wan)} 万元`;
    document.getElementById('pv-op-daily-self').textContent = `${fmt(pvi.daily_self_yuan)} 元`;
    document.getElementById('pv-op-annual-self').textContent = `${fmt(pvi.annual_self_wan)} 万元`;
    document.getElementById('pv-op-gen').textContent = `${fmt(pvi.daily_gen_kwh)} kWh`;
    document.getElementById('pv-op-annual-gen').textContent = `${fmt(pvi.annual_gen_mwh)} MWh`;
    document.getElementById('pv-op-self-rate').textContent = `${(pvi.self_rate * 100).toFixed(1)}%`;
    document.getElementById('pv-op-annual-self-rate').textContent = `${(pvi.self_rate * 100).toFixed(1)}%`;
  } else {
    ['pv-fin-total','pv-fin-irr','pv-fin-roi','pv-fin-cf','pv-op-daily-out','pv-op-annual-out','pv-op-daily-self','pv-op-annual-self','pv-op-gen','pv-op-annual-gen','pv-op-self-rate','pv-op-annual-self-rate'].forEach(id => {
      document.getElementById(id).textContent = '--';
    });
  }
  updateInvTabs(overview.ess_cap_mwh || 0, overview.pv_cap_kw || 0);

  // 运营状态标签
  document.getElementById('op-cycles-day').textContent = investment.equivalent_cycles ? `${investment.equivalent_cycles.toFixed(2)} 次/日` : '--';
  document.getElementById('op-dod-max').textContent = '--';
  document.getElementById('op-dod-min').textContent = '--';
  document.getElementById('op-pv-self-rate').textContent = pvi ? `${(pvi.self_rate * 100).toFixed(1)}%` : '--';
  document.getElementById('op-pv-util-hours').textContent = (pvi && overview.pv_cap_kw) ? `${(pvi.daily_gen_kwh / overview.pv_cap_kw).toFixed(1)} h` : '--';
  document.getElementById('op-load-cv').textContent = r.load_cv != null ? r.load_cv.toFixed(4) : '--';

  renderEconRatings(r.econ_ratings || []);

  // ECharts
  renderDispatchChart(time_series);
  renderWelfareCharts(time_series);
  renderEnergyAnalysisCharts(time_series);
  // 能量流动图
  updateFlowDiagram(overview);
}

function renderMiniBars(id, items) {
  const el = document.getElementById(id);
  el.innerHTML = items.map(it => `
    <div class="mini-bar-row">
      <span class="bar-label">${it.label}</span>
      <div class="bar-wrap"><div class="bar-fill ${it.cls}" style="width:${Math.min(100, Math.max(0, it.pct))}%"></div></div>
    </div>
  `).join('');
}

// --- App 注册 ---
App.analysis = {
  switchInvTab, updateInvTabs, runCalculation, renderResult, renderMiniBars, renderEconRatings,
  addSlot, toggleSlot, openCompareModal, closeCompareModal,
};
