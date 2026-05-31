// ===== analysis.js =====

// --- 方案槽位 ---
const SLOT_LETTERS = ['A', 'B', 'C', 'D', 'E'];
let slots = [null, null, null, null, null]; // null = 空, object = 快照

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

  // 快照当前参数和结果
  const snap = {
    scenarioId: document.getElementById('sel-scenario').value,
    pricingMode: document.getElementById('sel-pm').value,
    businessModel: document.getElementById('sel-bm').value,
    settlementMode: document.getElementById('sel-settlement').value,
    contractProfile: document.getElementById('sel-contract').value,
    dayaheadProfile: document.getElementById('sel-dayahead').value,
    result: App.state.result ? JSON.parse(JSON.stringify(App.state.result)) : null,
    label: SLOT_LETTERS[emptyIdx],
    timestamp: Date.now(),
  };
  slots[emptyIdx] = snap;
  refreshSlotUI();
  updateAddBtnState();

  // 记录后标记为已修改，禁用 + 按钮
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

// 监听参数变化，禁用 + 按钮
function onParamChange() {
  const tagCalc = document.getElementById('tag-calc');
  if (tagCalc) {
    tagCalc.textContent = '参数已修改';
    tagCalc.classList.remove('done');
  }
  updateAddBtnState();
}

// 绑定参数区 select 变化
document.querySelectorAll('.param-select').forEach(sel => {
  sel.addEventListener('change', onParamChange);
});

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
    '终端用户': { val: 'econ-val-user', badge: 'econ-badge-user', suffix: '元/kWh' },
    '光伏投资': { val: 'econ-val-pv', badge: 'econ-badge-pv', suffix: '%' },
    '储能投资': { val: 'econ-val-ess', badge: 'econ-badge-ess', suffix: '%' },
    '售电公司': { val: 'econ-val-retail', badge: 'econ-badge-retail', suffix: '元/MWh' },
  };
  econRatings.forEach(r => {
    const c = config[r.subject];
    if (!c) return;
    // 数值
    const valEl = document.getElementById(c.val);
    if (valEl) valEl.textContent = r.value != null ? `${r.value}${c.suffix}` : '--';
    // 等级标签
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
    updateAddBtnState();
  } catch (e) {
    console.error('Calculation failed:', e);
    alert('计算失败: ' + e.message);
  }
}

// --- 渲染 ---
function renderResult(r) {
  const { time_series, overview, welfare, investment } = r;

  // 概览 - 更新架构图上的容量标注
  document.getElementById('lbl-ess').textContent = `${overview.ess_cap_mwh.toFixed(2)} MWh / ${(overview.ess_power_kw / 1000).toFixed(2)} MW`;
  document.getElementById('lbl-pv').textContent = overview.pv_cap_kw ? `${overview.pv_cap_kw.toFixed(0)} kWp` : '0 kWp';
  document.getElementById('lbl-flex').textContent = overview.flex_load_kw ? `${(overview.flex_load_kw / 1000).toFixed(2)} MW` : '0 MW';
  document.getElementById('lbl-prod').textContent = `${(overview.prod_load_mwh).toFixed(2)} MW`;

  // 更新模式标签
  document.getElementById('tag-pm').textContent = document.getElementById('sel-pm').selectedOptions[0]?.text || '合同分时';
  document.getElementById('tag-bm').textContent = document.getElementById('sel-bm').selectedOptions[0]?.text || '储售一体';

  // 多方收益
  document.getElementById('welfare-badge').textContent = `总社会福利提升 ${welfare.total_welfare_wan.toFixed(2)}万元`;
  document.getElementById('w-bill-no').textContent = `${welfare.user_bill_no_ess_wan.toFixed(1)} 万`;
  document.getElementById('w-return').textContent = `${welfare.user_return_wan.toFixed(1)} 万`;
  document.getElementById('w-total').textContent = `${welfare.user_total_wan.toFixed(1)} 万`;
  // 新增标签（API暂无对应字段时显示 --）
  ['w-demand-saving','w-inv-share','w-inv-demand','w-inv-pv-out','w-inv-pv-self','w-cp-long','w-cp-day','w-cp-real','w-cp-ess'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el.textContent === '--') el.textContent = '--';
  });

  // 光储投资分析 - 储能
  document.getElementById('ess-fin-total').textContent = `${investment.initial_invest_wan.toFixed(1)} 万元`;
  document.getElementById('ess-fin-irr').textContent = investment.irr_pct != null ? `${investment.irr_pct.toFixed(2)}%` : 'N/A';
  document.getElementById('ess-fin-roi').textContent = investment.roi_years != null ? `${investment.roi_years.toFixed(2)} 年` : 'N/A';
  document.getElementById('ess-fin-cf').textContent = `${Math.round(investment.cum_cf_wan)} 万元`;
  document.getElementById('ess-op-daily-arb').textContent = `${investment.daily_arbitrage_yuan.toFixed(0)} 元`;
  document.getElementById('ess-op-annual-arb').textContent = `${investment.annual_arbitrage_wan.toFixed(1)} 万元`;
  document.getElementById('ess-op-charge').textContent = `${investment.total_charge_kwh.toFixed(0)} kWh`;
  document.getElementById('ess-op-annual-charge').textContent = `${investment.annual_charge_mwh.toFixed(1)} MWh`;
  document.getElementById('ess-op-discharge').textContent = `${investment.total_discharge_kwh.toFixed(0)} kWh`;
  document.getElementById('ess-op-annual-discharge').textContent = `${investment.annual_discharge_mwh.toFixed(1)} MWh`;
  document.getElementById('ess-op-cycles').textContent = `${investment.equivalent_cycles.toFixed(2)} 次`;
  document.getElementById('ess-op-annual-cycles').textContent = `${investment.annual_cycles.toFixed(0)} 次`;
  // 光储投资分析 - 光伏（暂用占位值）
  document.getElementById('pv-fin-total').textContent = '--';
  document.getElementById('pv-fin-irr').textContent = '--';
  document.getElementById('pv-fin-roi').textContent = '--';
  document.getElementById('pv-fin-cf').textContent = '--';
  document.getElementById('pv-op-daily-out').textContent = '--';
  document.getElementById('pv-op-annual-out').textContent = '--';
  document.getElementById('pv-op-daily-self').textContent = '--';
  document.getElementById('pv-op-annual-self').textContent = '--';
  document.getElementById('pv-op-gen').textContent = '--';
  document.getElementById('pv-op-annual-gen').textContent = '--';
  document.getElementById('pv-op-self-rate').textContent = '--';
  document.getElementById('pv-op-annual-self-rate').textContent = '--';
  // tab 状态
  updateInvTabs(overview.ess_cap_mwh || 0, overview.pv_cap_kw || 0);

  // 运营状态标签
  document.getElementById('op-cycles-day').textContent = investment.equivalent_cycles ? `${investment.equivalent_cycles.toFixed(2)} 次/日` : '--';
  document.getElementById('op-dod-max').textContent = '--';
  document.getElementById('op-dod-min').textContent = '--';
  document.getElementById('op-pv-self-rate').textContent = overview.pv_cap_kw ? '--' : '--';
  document.getElementById('op-pv-util-hours').textContent = overview.pv_cap_kw ? '--' : '--';
  document.getElementById('op-load-cv').textContent = r.load_cv != null ? r.load_cv.toFixed(4) : '--';

  // 经济性评级
  renderEconRatings(r.econ_ratings || []);

  // ECharts 调度曲线
  renderDispatchChart(time_series);
  // 多方收益图表
  renderWelfareCharts(time_series);
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

