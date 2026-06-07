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

  const st = App.state;
  const snap = {
    scenarioId: st.currentScenario,
    pricingMode: document.getElementById('sel-retail-pricing')?.value || 'M3',
    businessModel: 'B1',
    settlementMode: document.getElementById('sel-wholesale-rule')?.value || 'GUANGDONG_STYLE',
    contractProfile: document.getElementById('sel-contract-profile')?.value || 'mock_henan',
    dayaheadProfile: document.getElementById('sel-spot-profile')?.value || 'mock_henan',
    result: st.result ? JSON.parse(JSON.stringify(st.result)) : null,
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

// 监听所有参数变化
document.querySelectorAll('.param-select, .checkbox-item input, .toggle-item input').forEach(el => {
  el.addEventListener('change', onParamChange);
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
  const st = App.state;
  const essCap = st.result?.overview?.ess_cap_mwh || 0;
  const pvCap = st.result?.overview?.pv_cap_kw || 0;
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
  const st = App.state;
  const scenarioId = st.currentScenario || (st.scenarios[0]?.id);
  const pricingMode = document.getElementById('sel-retail-pricing')?.value || 'M3';
  const businessModel = 'B1'; // 默认商业模式
  const settlementMode = document.getElementById('sel-wholesale-rule')?.value || 'GUANGDONG_STYLE';
  const contractProfile = document.getElementById('sel-contract-profile')?.value || 'mock_henan';
  const dayaheadProfile = document.getElementById('sel-spot-profile')?.value || 'mock_henan';

  if (!scenarioId) {
    alert('没有可用的方案');
    return;
  }

  setLoading(true);

  try {
    const result = await App.api('/calculate', {
      method: 'POST',
      body: JSON.stringify({
        scenario_id: scenarioId,
        pricing_mode: pricingMode,
        business_model: businessModel,
        wholesale_overrides: { settlement_mode: settlementMode, contract_curve_profile: contractProfile, dayahead_curve_profile: dayaheadProfile },
      }),
    });
    st.result = result;
    st.currentScenario = scenarioId;
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

  document.getElementById('tag-pm').textContent = document.getElementById('sel-retail-pricing')?.selectedOptions[0]?.text || '合同分时';
  document.getElementById('tag-bm').textContent = '商业模式';

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

// ===== 拓扑图交互 =====
function updateTopology() {
  const chkLoad = document.getElementById('chk-load');
  const chkEss = document.getElementById('chk-ess');
  const chkPv = document.getElementById('chk-pv');
  const chkRetail = document.getElementById('chk-retail-mode');

  // 更新储能模块 (flow-ess)
  const essRect = document.getElementById('flow-ess');
  if (essRect) {
    const active = chkEss.checked;
    essRect.setAttribute('opacity', active ? '1' : '.25');
    essRect.setAttribute('fill', active ? 'rgba(78,159,61,0.10)' : 'rgba(78,159,61,0.03)');
  }

  // 更新光伏模块 (flow-pv)
  const pvRect = document.getElementById('flow-pv');
  const pvText = document.getElementById('flow-pv-text');
  if (pvRect) {
    const active = chkPv.checked;
    pvRect.setAttribute('opacity', active ? '1' : '.25');
    pvRect.setAttribute('fill', active ? 'rgba(242,161,4,0.08)' : 'rgba(242,161,4,0.02)');
  }
  if (pvText) {
    pvText.setAttribute('fill', chkPv.checked ? 'rgba(242,161,4,1)' : 'rgba(242,161,4,0.25)');
  }

  // 更新可调负荷模块 (flow-load-flex)
  const loadFlexRect = document.getElementById('flow-load-flex');
  const loadFlexText = document.getElementById('flow-flex-text');
  if (loadFlexRect) {
    const active = chkLoad.checked;
    loadFlexRect.setAttribute('opacity', active ? '1' : '.25');
    loadFlexRect.setAttribute('fill', active ? 'rgba(212,173,252,0.08)' : 'rgba(212,173,252,0.02)');
  }
  if (loadFlexText) {
    loadFlexText.setAttribute('fill', chkLoad.checked ? 'rgba(212,173,252,1)' : 'rgba(212,173,252,0.25)');
  }

  // 更新电力市场和售电公司（toggle控制）
  // 注意：这些元素在overview SVG中，需要通过querySelectorAll查找
  const flowNodes = document.querySelectorAll('.flow-node');
  flowNodes.forEach(node => {
    const text = node.nextElementSibling;
    if (text && text.textContent === '电力市场') {
      node.setAttribute('opacity', chkRetail.checked ? '1' : '.25');
      if (text) text.setAttribute('opacity', chkRetail.checked ? '1' : '.25');
    }
    if (text && text.textContent === '售电公司') {
      node.setAttribute('opacity', chkRetail.checked ? '1' : '.25');
      if (text) text.setAttribute('opacity', chkRetail.checked ? '1' : '.25');
    }
  });
}

// ===== 商业模式分组管理 =====
const BIZ_ENTITIES = [
  { id: 'user', label: '用户' },
  { id: 'ess', label: '储能' },
  { id: 'pv', label: '光伏' },
  { id: 'retail', label: '售电' },
];
const GROUP_NAMES = ['第一组', '第二组', '第三组', '第四组'];
const MAX_GROUPS = 4;

let bizGroups = [[]];
let activeDropdownGroup = -1;

function getAssignedEntities() {
  return bizGroups.flat();
}

function getGroupCount() {
  return bizGroups.length;
}

// 重新渲染整个 biz-groups 容器
function renderBizGroups() {
  const container = document.getElementById('biz-groups');
  if (!container) return;

  let html = '';
  for (let i = 0; i < bizGroups.length; i++) {
    const closeDisabled = bizGroups.length <= 1 ? ' disabled' : '';
    const tags = bizGroups[i].map(entityId => {
      const entity = BIZ_ENTITIES.find(e => e.id === entityId);
      return `<span class="biz-tag">${entity.label}<span class="biz-tag-close" onclick="App.analysis.removeBizEntity(${i},'${entityId}')">&times;</span></span>`;
    }).join('');

    html += `<div class="biz-group" data-group="${i}">
      <div class="biz-group-hd">
        <span>${GROUP_NAMES[i]}</span>
        <div class="biz-group-hd-btns">
          <button class="biz-group-add" onclick="App.analysis.toggleBizDropdown(${i})">+</button>
          <button class="biz-group-close${closeDisabled}" onclick="App.analysis.removeGroup(${i})" title="关闭此组">&times;</button>
        </div>
      </div>
      <div class="biz-group-body" id="biz-group-${i}">${tags}</div>
    </div>`;
  }

  // 新增按钮占位
  if (bizGroups.length < MAX_GROUPS) {
    html += `<button class="biz-group-placeholder-add" id="biz-group-add-btn" onclick="App.analysis.addGroup()" title="新增分组">+</button>`;
  }

  container.innerHTML = html;
  updateDispatchOptions();
}

// 更新调度目标 select
function updateDispatchOptions() {
  const sel = document.getElementById('sel-dispatch-target');
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML = bizGroups.map((_, i) =>
    `<option value="group${i}">${GROUP_NAMES[i]}最优</option>`
  ).join('');
  // 尝试保持之前的选择
  if (prev && sel.querySelector(`option[value="${prev}"]`)) {
    sel.value = prev;
  }
}

// 新增一组
function addGroup() {
  if (bizGroups.length >= MAX_GROUPS) return;
  bizGroups.push([]);
  renderBizGroups();
  onParamChange();
}

// 关闭一组
function removeGroup(idx) {
  if (bizGroups.length <= 1) return;
  bizGroups.splice(idx, 1);
  renderBizGroups();
  onParamChange();
}

function toggleBizDropdown(groupIdx) {
  const dropdown = document.getElementById('biz-dropdown');
  if (!dropdown) return;

  if (activeDropdownGroup === groupIdx) {
    dropdown.style.display = 'none';
    activeDropdownGroup = -1;
    return;
  }

  activeDropdownGroup = groupIdx;
  const assigned = getAssignedEntities();

  const availableEntities = BIZ_ENTITIES.filter(e => !assigned.includes(e.id));
  dropdown.innerHTML = availableEntities
    .map(e => `<div class="biz-dropdown-item" onclick="App.analysis.addBizEntity('${e.id}')">${e.label}</div>`)
    .join('');

  if (dropdown.innerHTML === '') {
    dropdown.innerHTML = '<div class="biz-dropdown-item disabled">无可用主体</div>';
  }

  const groupEl = document.querySelector(`.biz-group[data-group="${groupIdx}"] .biz-group-add`);
  if (groupEl) {
    const rect = groupEl.getBoundingClientRect();
    dropdown.style.position = 'fixed';
    dropdown.style.top = (rect.bottom + 4) + 'px';
    dropdown.style.left = rect.left + 'px';
    dropdown.style.zIndex = '1000';
  }

  dropdown.style.display = 'block';
}

function addBizEntity(entityId) {
  if (activeDropdownGroup < 0) return;
  const assigned = getAssignedEntities();
  if (assigned.includes(entityId)) return;

  bizGroups[activeDropdownGroup].push(entityId);
  renderBizGroups();

  const dropdown = document.getElementById('biz-dropdown');
  if (dropdown) dropdown.style.display = 'none';
  activeDropdownGroup = -1;

  onParamChange();
}

function removeBizEntity(groupIdx, entityId) {
  bizGroups[groupIdx] = bizGroups[groupIdx].filter(id => id !== entityId);
  renderBizGroups();
  onParamChange();
}

// 点击外部关闭下拉
document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('biz-dropdown');
  if (!dropdown || dropdown.style.display === 'none') return;
  if (e.target.closest('.biz-dropdown') || e.target.closest('.biz-group-add')) return;
  dropdown.style.display = 'none';
  activeDropdownGroup = -1;
});

// ===== 零售电价联动 =====
const PRICING_CURVE_MAP = {
  'M1': [
    { value: 'admin_guangdong', label: '广东行政分时' },
    { value: 'admin_jiangsu', label: '江苏行政分时' },
  ],
  'M3': [
    { value: 'contract_guangdong', label: '广东合同分时' },
    { value: 'contract_jiangsu', label: '江苏合同分时' },
  ],
  'M5': [
    { value: 'flat_0.5', label: '固定 0.5 元/kWh' },
    { value: 'flat_0.6', label: '固定 0.6 元/kWh' },
  ],
  'M4-contract': [
    { value: 'contract_spot_guangdong', label: '广东中长期联动' },
  ],
  'M4': [
    { value: 'spot_guangdong', label: '广东现货' },
    { value: 'spot_shandong', label: '山东现货' },
  ],
};

function onRetailPricingChange() {
  const retailPricing = document.getElementById('sel-retail-pricing').value;
  const curveSelect = document.getElementById('sel-pricing-curve');
  const curves = PRICING_CURVE_MAP[retailPricing] || [];
  curveSelect.innerHTML = curves.map(c => `<option value="${c.value}">${c.label}</option>`).join('');
  onParamChange();
}

// --- App 注册 ---
App.analysis = {
  switchInvTab, updateInvTabs, runCalculation, renderResult, renderMiniBars, renderEconRatings,
  addSlot, toggleSlot, openCompareModal, closeCompareModal,
  updateTopology, toggleBizDropdown, addBizEntity, removeBizEntity, onRetailPricingChange,
  addGroup, removeGroup,
};
