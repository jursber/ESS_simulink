// ===== single-scenario workbench =====
(function () {
  const KEYS = ['A', 'B', 'C', 'D'];
  const state = {
    parent: null,
    activeKey: 'A',
    variants: {},
    dirtyDraft: new Set(),
    parentDirty: false,
    globalParams: null,
    loadProfiles: [],
    simpleDayCatalog: null,
  };

  const clone = (v) => JSON.parse(JSON.stringify(v || {}));
  const el = (id) => document.getElementById(id);
  const activeVariant = () => state.variants[state.activeKey];

  function defaultVariant(key = 'A') {
    return {
      key,
      name: key,
      pricing_mode: 'M1',
      business_model: 'B1',
      dispatch_target: 'group0',
      system: { net_load: true, ess: true, pv: false },
      ess_params: {},
      pv_params: {},
      financial_params: {},
      private_overrides: {},
      run_curves: {
        load_profile: 'daily_default',
        pv_curve_id: '',
        spot_curve_id: '',
        spot_price_kind: 'day_ahead',
        spot_link_ratio: 0.90,
        spot_fixed_price: 0.40,
        monthly_curve_id: '',
        monthly_link_ratio: 0.70,
        monthly_fixed_price: 0.40,
        retail_curve_id: 'admin',
      },
      wholesale_overrides: {
        settlement_mode: 'GUANGDONG_STYLE',
        contract_curve_profile: 'mock_henan',
        dayahead_curve_profile: 'mock_henan',
      },
      ui_state: {
        biz_groups: [[]],
      },
    };
  }

  function mergeVariant(key, data) {
    const base = defaultVariant(key);
    const incoming = clone(data);
    return {
      ...base,
      ...incoming,
      key,
      name: incoming.name || key,
      system: { ...base.system, ...(incoming.system || {}) },
      ess_params: { ...(incoming.ess_params || {}) },
      pv_params: { ...(incoming.pv_params || {}) },
      financial_params: { ...(incoming.financial_params || {}) },
      private_overrides: { ...(incoming.private_overrides || {}) },
      run_curves: { ...base.run_curves, ...(incoming.run_curves || {}) },
      wholesale_overrides: { ...base.wholesale_overrides, ...(incoming.wholesale_overrides || {}) },
      ui_state: {
        ...base.ui_state,
        ...(incoming.ui_state || {}),
      },
    };
  }

  async function loadParent(scenarioId, preferredKey = 'A') {
    if (!scenarioId) return;
    await initRunCurveControls();
    state.parent = await App.api(`/scenarios/${scenarioId}`);
    state.variants = {};
    const raw = state.parent.variants || {};
    const existingKeys = Object.keys(raw).filter(k => KEYS.includes(k));
    (existingKeys.length ? existingKeys : ['A']).forEach(k => {
      state.variants[k] = mergeVariant(k, raw[k] || {});
    });
    if (!state.variants.A) state.variants.A = mergeVariant('A', {});
    state.activeKey = state.variants[preferredKey] ? preferredKey : (state.variants.A ? 'A' : Object.keys(state.variants)[0]);
    state.dirtyDraft.clear();
    state.parentDirty = false;
    applyVariantToUI(activeVariant());
    renderSlots();
    markParentDirty(false);
  }

  function collectVariantFromUI() {
    const current = mergeVariant(state.activeKey, activeVariant());
    const wholesale = current.wholesale_overrides || {};
    const pricingMode = el('sel-retail-pricing')?.value || current.pricing_mode || 'M1';
    const priceChoice = selectedPricingCurve();
    return {
      ...current,
      pricing_mode: pricingMode,
      business_model: current.business_model || 'B1',
      dispatch_target: el('sel-dispatch-target')?.value || 'group0',
      ui_state: {
        ...(current.ui_state || {}),
        biz_groups: App.analysis?.getBizGroupsSnapshot?.() || current.ui_state?.biz_groups || [[]],
      },
      system: {
        net_load: true,
        ess: !!el('chk-ess')?.checked,
        pv: !!el('chk-pv')?.checked,
        retail: !!el('chk-retail-mode')?.checked,
      },
      run_curves: {
        ...(current.run_curves || {}),
        load_profile: el('sel-load-profile')?.value || current.run_curves?.load_profile || 'daily_default',
        pv_curve_id: el('sel-pv-curve-id')?.value || current.run_curves?.pv_curve_id || '',
        spot_curve_id: priceChoice.category === 'spot' ? priceChoice.value : (current.run_curves?.spot_curve_id || ''),
        spot_price_kind: priceChoice.category === 'spot' ? (priceChoice.priceKind || 'day_ahead') : (current.run_curves?.spot_price_kind || 'day_ahead'),
        monthly_curve_id: priceChoice.category === 'monthly' ? priceChoice.value : (current.run_curves?.monthly_curve_id || ''),
        retail_curve_id: priceChoice.category === 'retail' ? priceChoice.value : (current.run_curves?.retail_curve_id || 'admin'),
      },
      wholesale_overrides: {
        ...wholesale,
        settlement_mode: el('sel-wholesale-rule')?.value || wholesale.settlement_mode || 'GUANGDONG_STYLE',
        contract_curve_profile: el('sel-contract-profile')?.value || wholesale.contract_curve_profile || 'mock_henan',
        dayahead_curve_profile: el('sel-spot-profile')?.value || wholesale.dayahead_curve_profile || 'mock_henan',
      },
    };
  }

  function persistCurrentUIToMemory(markDirty = true) {
    state.variants[state.activeKey] = collectVariantFromUI();
    if (markDirty) {
      state.dirtyDraft.add(state.activeKey);
      state.parentDirty = true;
    }
    renderSlots();
    markParentDirty(state.parentDirty);
  }

  function applyVariantToUI(v) {
    if (!v) return;
    if (el('sel-retail-pricing')) el('sel-retail-pricing').value = v.pricing_mode || 'M1';
    if (App.analysis?.setBizGroupsSnapshot) App.analysis.setBizGroupsSnapshot(v.ui_state?.biz_groups || [[]]);
    if (el('sel-dispatch-target')) el('sel-dispatch-target').value = v.dispatch_target || 'group0';
    if (el('sel-wholesale-rule')) el('sel-wholesale-rule').value = v.wholesale_overrides?.settlement_mode || 'GUANGDONG_STYLE';
    if (el('sel-contract-profile')) el('sel-contract-profile').value = v.wholesale_overrides?.contract_curve_profile || 'mock_henan';
    if (el('sel-spot-profile')) el('sel-spot-profile').value = v.wholesale_overrides?.dayahead_curve_profile || 'mock_henan';
    if (el('chk-load')) {
      el('chk-load').checked = true;
      el('chk-load').disabled = true;
    }
    if (el('chk-ess')) el('chk-ess').checked = v.system?.ess !== false;
    if (el('chk-pv')) el('chk-pv').checked = !!v.system?.pv;
    if (el('chk-retail-mode')) el('chk-retail-mode').checked = !!v.system?.retail;
    if (el('sel-load-profile')) el('sel-load-profile').value = v.run_curves?.load_profile || 'daily_default';
    if (el('sel-pv-curve-id')) setSelectValue(el('sel-pv-curve-id'), v.run_curves?.pv_curve_id || '');
    refreshPricingCurveOptions(false, v);
    updateCompositionUI(false);
  }

  function renderSlots() {
    KEYS.forEach((key, i) => {
      const btn = el(`slot-${i}`);
      if (!btn) return;
      const exists = !!state.variants[key];
      btn.style.display = exists ? 'inline-flex' : 'none';
      btn.classList.toggle('active', exists && key === state.activeKey);
      btn.classList.toggle('slot-unsaved', state.dirtyDraft.has(key));
      btn.disabled = !exists;
      const text = btn.querySelector('.slot-label') || btn.querySelector('span:last-child');
      if (text) text.textContent = key;
    });
    const add = el('slot-add');
    if (add) {
      const full = Object.keys(state.variants).length >= 4;
      add.style.display = full ? 'none' : 'inline-flex';
      add.disabled = full;
    }
    const compare = el('slot-compare');
    if (compare) compare.disabled = Object.keys(state.variants).length < 2;
  }

  async function switchSlot(index) {
    const key = KEYS[index];
    if (!state.variants[key]) return;
    if (key === state.activeKey) {
      persistCurrentUIToMemory(false);
      renderSlots();
      return;
    }
    persistCurrentUIToMemory(false);
    state.activeKey = key;
    applyVariantToUI(activeVariant());
    renderSlots();
    await runCalculation();
  }

  function addSlot() {
    persistCurrentUIToMemory(false);
    const next = KEYS.find(k => !state.variants[k]);
    if (!next) return;
    const snapshot = collectVariantFromUI();
    snapshot.key = next;
    snapshot.name = next;
    state.variants[next] = mergeVariant(next, snapshot);
    state.activeKey = next;
    state.dirtyDraft.add(next);
    state.parentDirty = true;
    applyVariantToUI(activeVariant());
    renderSlots();
    markParentDirty(true);
  }

  function stashActiveVariant() {
    state.variants[state.activeKey] = collectVariantFromUI();
    state.dirtyDraft.delete(state.activeKey);
    state.parentDirty = true;
    renderSlots();
    markParentDirty(true);
  }

  async function saveParentScenario() {
    if (!state.parent?.id) return;
    persistCurrentUIToMemory(false);
    const payload = {
      name: state.parent.name,
      region: state.parent.region || 'henan',
      pricing_mode: state.variants.A?.pricing_mode || 'M1',
      business_model: state.variants.A?.business_model || 'B1',
      selected_date: state.variants.A?.selected_date || state.parent.selected_date || '2026-03-15',
      system: state.variants.A?.system || state.parent.system,
      ess_params: state.variants.A?.ess_params || {},
      pv_params: state.variants.A?.pv_params || {},
      financial_params: state.variants.A?.financial_params || {},
      private_overrides: state.variants.A?.private_overrides || {},
      wholesale_overrides: state.variants.A?.wholesale_overrides || {},
      run_curves: state.variants.A?.run_curves || {},
      variants: state.variants,
    };
    const res = await App.api(`/scenarios/${state.parent.id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    state.parent = res.scenario;
    state.dirtyDraft.clear();
    state.parentDirty = false;
    renderSlots();
    markParentDirty(false);
    const tag = el('tag-calc');
    if (tag) tag.textContent = '方案已保存';
  }

  function markParentDirty(on) {
    const tag = el('tag-calc');
    if (!tag) return;
    if (on) {
      tag.textContent = '方案未保存';
      tag.classList.remove('done');
    }
  }

  function markChanged() {
    persistCurrentUIToMemory(true);
    updateCompositionUI(false);
  }

  function setText(ids, value = '--') {
    ids.forEach(id => { if (el(id)) el(id).textContent = value; });
  }

  function clearFacilityResults(kind) {
    if (kind === 'ess') {
      setText(['lbl-ess','ess-fin-total','ess-fin-irr','ess-fin-roi','ess-fin-cf','ess-op-daily-arb','ess-op-annual-arb','ess-op-charge','ess-op-annual-charge','ess-op-discharge','ess-op-annual-discharge','ess-op-cycles','ess-op-annual-cycles','op-cycles-day']);
    }
    if (kind === 'pv') {
      setText(['lbl-pv','pv-fin-total','pv-fin-irr','pv-fin-roi','pv-fin-cf','pv-op-daily-out','pv-op-annual-out','pv-op-daily-self','pv-op-annual-self','pv-op-gen','pv-op-annual-gen','pv-op-self-rate','pv-op-annual-self-rate','op-pv-self-rate','op-pv-util-hours','w-inv-pv-out','w-inv-pv-self']);
    }
  }

  function updateCompositionUI(mark = false) {
    const hasEss = !!el('chk-ess')?.checked;
    const hasPv = !!el('chk-pv')?.checked;
    if (el('chk-load')) {
      el('chk-load').checked = true;
      el('chk-load').disabled = true;
    }
    paintNode('flow-ess', null, hasEss, '#4E9F3D', 'rgba(78,159,61,0.10)');
    paintNode('flow-pv', 'flow-pv-text', hasPv, '#4E9F3D', 'rgba(78,159,61,0.10)');
    paintNode('flow-net-load', 'flow-net-load-text', true, '#F2A104', 'rgba(242,161,4,0.10)');
    paintNode('flow-load-flex', 'flow-flex-text', false, '#F2A104', 'rgba(242,161,4,0.04)');
    toggleControl('sel-pv-curve-id', hasPv);
    toggleDeviceButton('device-ess-btn', hasEss);
    toggleDeviceButton('device-pv-btn', hasPv);
    if (!hasEss) clearFacilityResults('ess');
    if (!hasPv) clearFacilityResults('pv');
    updateInvTabs(hasEss ? 1 : 0, hasPv ? 1 : 0);
    const arch = el('tag-arch');
    if (arch) arch.textContent = hasEss && hasPv ? '光储联合' : (hasEss ? '单储能' : (hasPv ? '单光伏' : '无光储'));
    App.analysis?.syncBizGroupsToComposition?.();
    App.analysis?.updateTopology?.();
    if (mark) persistCurrentUIToMemory(true);
  }

  function paintNode(rectId, textId, active, color, fill) {
    const rect = el(rectId);
    if (rect) {
      rect.setAttribute('opacity', active ? '1' : '.8');
      rect.setAttribute('stroke', color);
      rect.setAttribute('fill', active ? fill : fill.replace('0.10', '0.03'));
      rect.classList.toggle('topo-disabled-svg', !active);
    }
    const text = textId ? el(textId) : null;
    if (text) {
      text.setAttribute('fill', active ? color : 'rgba(176,176,176,0.45)');
      text.setAttribute('opacity', active ? '1' : '.8');
    }
  }

  function toggleControl(id, enabled) {
    const target = el(id);
    if (target) target.disabled = !enabled;
  }

  function toggleDeviceButton(id, enabled) {
    const target = el(id);
    if (!target) return;
    target.classList.toggle('disabled', !enabled);
    target.setAttribute('aria-disabled', String(!enabled));
  }

  async function ensureGlobalParams() {
    if (!state.globalParams) state.globalParams = await App.api('/global-params');
    return state.globalParams;
  }

  async function ensureLoadProfiles() {
    if (!state.loadProfiles.length) {
      const data = await App.api('/params/load-profiles');
      state.loadProfiles = data.profiles || [];
    }
    return state.loadProfiles;
  }

  async function ensureSimpleDayCatalog() {
    if (!state.simpleDayCatalog) state.simpleDayCatalog = await App.api('/simple-day/catalog');
    return state.simpleDayCatalog;
  }

  function optionHtml(items, valueKey = 'id') {
    return (items || []).map(item => {
      const value = item[valueKey];
      return `<option value="${value}" data-category="${item.category || ''}" data-curve-id="${item.curve_id || value}" data-price-kind="${item.price_kind || ''}">${item.label || item.id}</option>`;
    }).join('');
  }

  function selectedPricingCurve() {
    const select = el('sel-pricing-curve');
    const option = select?.selectedOptions?.[0];
    return {
      value: option?.dataset?.curveId || select?.value || '',
      category: option?.dataset?.category || '',
      priceKind: option?.dataset?.priceKind || '',
      rawValue: select?.value || '',
    };
  }

  function setSelectValue(select, value) {
    if (!select) return;
    if (value && [...select.options].some(opt => opt.value === value)) {
      select.value = value;
    } else if (select.options.length) {
      select.selectedIndex = 0;
    }
  }

  async function initRunCurveControls() {
    const catalog = await ensureSimpleDayCatalog().catch(() => null);
    const profiles = catalog?.load || await ensureLoadProfiles().catch(() => []);
    const sel = el('sel-load-profile');
    if (sel && profiles.length) {
      sel.innerHTML = profiles.map(p => `<option value="${p.id || p.name}">${p.label || p.id || p.name}</option>`).join('');
    }
    const pvSel = el('sel-pv-curve-id');
    if (pvSel && catalog?.pv?.length) {
      pvSel.innerHTML = optionHtml(catalog.pv);
    }
    const priceSel = el('sel-pricing-curve');
    if (priceSel) {
      refreshPricingCurveOptions(false);
    }
  }

  function refreshPricingCurveOptions(mark = true, variant = null) {
    const priceSel = el('sel-pricing-curve');
    if (!priceSel || !state.simpleDayCatalog) return;
    const v = variant || activeVariant() || {};
    const pricingMode = el('sel-retail-pricing')?.value || v.pricing_mode || 'M1';
    const items = pricingCurveItemsForMode(pricingMode);
    priceSel.innerHTML = optionHtml(items);
    let selected = v.run_curves?.retail_curve_id || defaultRetailCurveForMode(pricingMode);
    if (pricingMode === 'M4') {
      const kind = v.run_curves?.spot_price_kind || 'day_ahead';
      selected = v.run_curves?.spot_curve_id ? `${v.run_curves.spot_curve_id}::${kind}` : '';
    } else if (pricingMode === 'M4-contract') {
      selected = v.run_curves?.monthly_curve_id || '';
    }
    setSelectValue(priceSel, selected || '');
    if (mark) markChanged();
  }

  function defaultRetailCurveForMode(pricingMode) {
    if (pricingMode === 'M3') return 'contract';
    if (pricingMode === 'M5') return 'flat';
    return 'admin';
  }

  function pricingCurveItemsForMode(pricingMode) {
    const catalog = state.simpleDayCatalog || {};
    if (pricingMode === 'M4') {
      return (catalog.spot || []).flatMap(item => {
        const meta = item.meta || {};
        const out = [];
        if (meta.has_day_ahead !== 'False') {
          out.push({
            id: `${item.id}::day_ahead`,
            curve_id: item.id,
            price_kind: 'day_ahead',
            label: `${item.label} / 日前`,
            category: 'spot',
          });
        }
        if (meta.has_real_time !== 'False') {
          out.push({
            id: `${item.id}::real_time`,
            curve_id: item.id,
            price_kind: 'real_time',
            label: `${item.label} / 实时`,
            category: 'spot',
          });
        }
        return out;
      }).slice(0, 400);
    }
    if (pricingMode === 'M4-contract') return catalog.monthly || [];
    const targetMode = defaultRetailCurveForMode(pricingMode);
    return (catalog.retail || []).filter(item => (item.meta || {}).mode === targetMode);
  }

  function openDeviceModal(kind) {
    const hasEss = !!el('chk-ess')?.checked;
    const hasPv = !!el('chk-pv')?.checked;
    if (kind === 'ess' && !hasEss) return;
    if (kind === 'pv' && !hasPv) return;
    ensureGlobalParams().then(params => {
      const v = activeVariant();
      const values = kind === 'ess'
        ? { ...(params.ess || {}), ...(params.financial || {}), ...(v.ess_params || {}), ...(v.financial_params || {}) }
        : { ...(params.pv || {}), ...(v.pv_params || {}) };
      showModal(kind === 'ess' ? '储能参数' : '光伏参数', deviceFields(kind, values), (form) => {
        const parsed = readFormFields(form);
        if (kind === 'ess') {
          const essParsed = {};
          const finParsed = {};
          const essPercent = new Set(['eta_roundtrip', 'eta_charge', 'soc_min', 'soc_max', 'r_degrade', 'r_ess_share', 'r_om']);
          const essBool = new Set(['degrade_enabled', 'cycle_enabled']);
          const essInt = new Set(['design_life', 'cycle_life']);
          Object.entries(parsed).forEach(([key, value]) => {
            if (['r_user_b1', 'r_user_b2'].includes(key)) {
              finParsed[key] = Number(value) / 100;
            } else if (key === 'cap_rated') {
              essParsed[key] = Number(value) * 1000;
            } else if (essPercent.has(key)) {
              essParsed[key] = Number(value) / 100;
            } else if (essBool.has(key)) {
              essParsed[key] = !!value;
            } else if (essInt.has(key)) {
              essParsed[key] = parseInt(value, 10);
            } else {
              essParsed[key] = Number(value);
            }
          });
          state.variants[state.activeKey].ess_params = { ...(state.variants[state.activeKey].ess_params || {}), ...essParsed };
          state.variants[state.activeKey].financial_params = { ...(state.variants[state.activeKey].financial_params || {}), ...finParsed };
        } else {
          const pvParsed = {};
          const pvPercent = new Set(['self_use_discount', 'r_om', 'r_degrade_first', 'r_degrade']);
          const pvInt = new Set(['design_life']);
          Object.entries(parsed).forEach(([key, value]) => {
            if (pvPercent.has(key)) pvParsed[key] = Number(value) / 100;
            else if (pvInt.has(key)) pvParsed[key] = parseInt(value, 10);
            else pvParsed[key] = Number(value);
          });
          state.variants[state.activeKey].pv_params = { ...(state.variants[state.activeKey].pv_params || {}), ...pvParsed };
        }
        markChanged();
      });
    });
  }

  function deviceFields(kind, v) {
    const pct = (value, fallback, digits = 1) => (Number(value ?? fallback) * 100).toFixed(digits);
    if (kind === 'ess') {
      return [
        { type: 'section', label: '基本参数' },
        ['cap_rated', '额定容量 (MWh)', ((v.cap_rated ?? 1000) / 1000).toFixed(2), 'number', '0.1'],
        ['power_rated', '额定功率 (MW)', v.power_rated ?? 0.5, 'number', '0.1'],
        ['eta_roundtrip', '往返效率 RTE (%)', pct(v.eta_roundtrip, 0.87, 0), 'number', '1'],
        ['eta_charge', '单程充电效率 η (%)', pct(v.eta_charge, 0.92, 0), 'number', '1'],
        ['soc_min', 'SOC 下限 (%)', pct(v.soc_min, 0.10, 0), 'number', '1'],
        ['soc_max', 'SOC 上限 (%)', pct(v.soc_max, 0.90, 0), 'number', '1'],
        ['design_life', '设计寿命 (年)', v.design_life ?? 10, 'number', '1'],
        ['r_degrade', '储能容量年衰减比例 (%)', pct(v.r_degrade, 0.025), 'number', '0.1'],
        { id: 'degrade_enabled', label: '启用容量衰减约束', value: !!v.degrade_enabled, type: 'checkbox' },
        ['cycle_life', '储能循环次数 (100% DoD)', v.cycle_life ?? 5000, 'number', '100'],
        { id: 'cycle_enabled', label: '启用循环次数约束', value: !!v.cycle_enabled, type: 'checkbox' },
        ['r_ess_share', '储能收益分成比例 (%)', pct(v.r_ess_share, 0.20, 0), 'number', '1'],
        { type: 'section', label: '电价参数' },
        ['r_user_b1', '用户侧峰谷套利收益分享比例 (%)', pct(v.r_user_b1, 0, 0), 'number', '1'],
        ['r_user_b2', '售电公司额外收益分享比例 (%)', pct(v.r_user_b2, 0, 0), 'number', '1'],
        { type: 'section', label: '经济参数' },
        ['unit_cost', '建设单价 (元/Wh)', v.unit_cost ?? 0.9, 'number', '0.1'],
        ['r_om', '年运维支出比例 (%)', pct(v.r_om, 0.01), 'number', '0.1'],
      ];
    }
    return [
      { type: 'section', label: '基本参数' },
      ['cap_rated', '额定装机容量 (kWp)', v.cap_rated ?? 1.0, 'number', '0.1'],
      { type: 'radio', id: 'project_type', label: '项目类型', value: 'distributed', disabled: true, options: [['distributed', '分布式'], ['centralized', '集中式']] },
      { type: 'section', label: '电价参数' },
      ['feed_in_tariff', '光伏上网电价 (元/kWh)', v.feed_in_tariff ?? 0.4, 'number', '0.01'],
      ['self_use_discount', '本地消纳电费折扣 (%)', pct(v.self_use_discount, 0.80, 0), 'number', '1'],
      { id: 'mechanism_enabled', label: '启用机制电价', value: false, type: 'checkbox', disabled: true },
      ['mechanism_price', '机制电价 (元/MWh)', 0, 'number', '1', true],
      ['mechanism_ratio', '机制电价比例 (%)', 0, 'number', '1', true],
      { type: 'section', label: '经济参数' },
      ['unit_cost', '单位造价 (元/Wp)', v.unit_cost ?? 3.5, 'number', '0.1'],
      ['r_om', '年运维费用比例 (%)', pct(v.r_om, 0.015), 'number', '0.1'],
      ['design_life', '设计寿命 (年)', v.design_life ?? 25, 'number', '1'],
      ['r_degrade_first', '首年衰减率 (%)', pct(v.r_degrade_first, 0.02), 'number', '0.1'],
      ['r_degrade', '年衰减率 (%)', pct(v.r_degrade, 0.005), 'number', '0.1'],
    ];
  }

  async function openLoadModal() {
    const profiles = await ensureLoadProfiles();
    const v = activeVariant();
    const selected = profiles.find(p => p.name === (v.run_curves?.load_profile || el('sel-load-profile')?.value)) || profiles[0];
    showModal('净生产负荷曲线', [
      ['profile_name', '曲线', selected?.name || 'daily_default', 'select', profiles.map(p => [p.name, p.label || p.name])],
      ['avg_load', '平均负荷 (MW)', selected?.avg_load_mw || '', 'number', '0.01'],
      ['max_load', '最大负荷 (MW)', selected?.max_load_mw || '', 'number', '0.01'],
      ['max_demand', '最大需量 (MW)', selected?.max_demand_mw || '', 'number', '0.01', true],
      ['max_demand_period', '最大需量出现时刻', selected?.max_demand_period || '', 'text', '', true],
      ['randomness', '随机度 (%)', v.run_curves?.randomness || 0, 'number', '1'],
    ], (form) => {
      const parsed = readFormFields(form);
      state.variants[state.activeKey].run_curves = {
        ...(state.variants[state.activeKey].run_curves || {}),
        load_profile: parsed.profile_name,
        avg_load: parsed.avg_load,
        max_load: parsed.max_load,
        randomness: parsed.randomness,
      };
      if (el('sel-load-profile')) el('sel-load-profile').value = parsed.profile_name;
      markChanged();
    });
  }

  function showModal(title, fields, onSave) {
    const overlay = el('workbench-modal') || createModal();
    const body = overlay.querySelector('.workbench-modal-body');
    body.classList.remove('wide');
    overlay.querySelector('.workbench-modal-title').textContent = title;
    body.innerHTML = fields.map(renderModalField).join('');
    overlay.querySelector('.workbench-save').onclick = () => {
      onSave(body);
      overlay.style.display = 'none';
    };
    overlay.style.display = 'flex';
  }

  function renderModalField(field) {
    if (!Array.isArray(field)) {
      if (field.type === 'section') {
        return `<div class="wb-section-title">${field.label}</div>`;
      }
      if (field.type === 'checkbox') {
        return `<label class="wb-field"><span>${field.label}</span><label style="display:flex;align-items:center;gap:8px;color:var(--text-1);font-size:var(--fs-12)"><input name="${field.id}" type="checkbox" ${field.value ? 'checked' : ''} ${field.disabled ? 'disabled' : ''}> 启用</label></label>`;
      }
      if (field.type === 'radio') {
        const options = (field.options || []).map(([value, label]) => `<label style="display:flex;align-items:center;gap:6px;color:var(--text-1);font-size:var(--fs-12)"><input name="${field.id}" type="radio" value="${value}" ${value === field.value ? 'checked' : ''} ${field.disabled ? 'disabled' : ''}>${label}</label>`).join('');
        return `<div class="wb-field"><span>${field.label}</span><div style="display:flex;gap:12px;flex-wrap:wrap">${options}</div></div>`;
      }
    }
    const [id, label, value, type, meta, disabled] = field;
    if (type === 'select') {
      return `<label class="wb-field"><span>${label}</span><select name="${id}" ${disabled ? 'disabled' : ''}>${(meta || []).map(([v,l]) => `<option value="${v}" ${v === value ? 'selected' : ''}>${l}</option>`).join('')}</select></label>`;
    }
    return `<label class="wb-field"><span>${label}</span><input name="${id}" type="${type}" step="${meta || ''}" value="${value ?? ''}" ${disabled ? 'disabled' : ''}></label>`;
  }

  function showHtmlModal(title, html, onSave, onShown) {
    const overlay = el('workbench-modal') || createModal();
    const body = overlay.querySelector('.workbench-modal-body');
    body.classList.add('wide');
    overlay.querySelector('.workbench-modal-title').textContent = title;
    body.innerHTML = html;
    overlay.querySelector('.workbench-save').onclick = () => {
      onSave?.(body);
      overlay.style.display = 'none';
    };
    overlay.style.display = 'flex';
    onShown?.(body);
  }

  function createModal() {
    const overlay = document.createElement('div');
    overlay.id = 'workbench-modal';
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `<div class="modal-box workbench-modal-box">
      <div class="modal-hd"><span class="modal-title workbench-modal-title"></span><span class="modal-close workbench-close">&times;</span></div>
      <div class="modal-body workbench-modal-body"></div>
      <div class="modal-actions"><button class="btn workbench-close-btn">取消</button><button class="btn primary workbench-save">保存</button></div>
    </div>`;
    overlay.style.display = 'none';
    document.body.appendChild(overlay);
    overlay.querySelectorAll('.workbench-close,.workbench-close-btn').forEach(btn => {
      btn.addEventListener('click', () => { overlay.style.display = 'none'; });
    });
    return overlay;
  }

  function readFormFields(container) {
    const out = {};
    container.querySelectorAll('input,select').forEach(input => {
      if (input.disabled) return;
      if (!input.name) return;
      if (input.type === 'checkbox') {
        out[input.name] = input.checked;
      } else if (input.type === 'radio') {
        if (input.checked) out[input.name] = input.value;
      } else {
        out[input.name] = input.type === 'number' ? Number(input.value) : input.value;
      }
    });
    return out;
  }

  let pricingCurveChart = null;
  const WB_TARIFF_CURVES = {
    typical: {
      label: '典型峰谷平',
      periods: [
        {period:'谷段', start:0, end:8, price:0.28},
        {period:'峰段', start:8, end:12, price:0.95},
        {period:'平段', start:12, end:17, price:0.58},
        {period:'峰段', start:17, end:21, price:0.95},
        {period:'平段', start:21, end:24, price:0.58},
      ],
    },
    midday_valley: {
      label: '午间深谷',
      periods: [
        {period:'谷段', start:0, end:6, price:0.25},
        {period:'平段', start:6, end:9, price:0.50},
        {period:'峰段', start:9, end:12, price:0.90},
        {period:'深谷', start:12, end:15, price:0.15},
        {period:'平段', start:15, end:18, price:0.50},
        {period:'峰段', start:18, end:22, price:0.90},
        {period:'谷段', start:22, end:24, price:0.25},
      ],
    },
    summer_peak: {
      label: '夏季尖峰',
      periods: [
        {period:'谷段', start:0, end:6, price:0.30},
        {period:'平段', start:6, end:8, price:0.55},
        {period:'峰段', start:8, end:11, price:0.95},
        {period:'尖峰', start:11, end:14, price:1.20},
        {period:'平段', start:14, end:17, price:0.55},
        {period:'峰段', start:17, end:21, price:0.95},
        {period:'谷段', start:21, end:24, price:0.30},
      ],
    },
  };

  function openPricingCurveModal() {
    ensureSimpleDayCatalog().then(() => {
      const pricingMode = el('sel-retail-pricing')?.value || 'M1';
      if (pricingMode === 'M4-contract') {
        openLinkedCurveModal('monthly');
      } else if (pricingMode === 'M4') {
        openLinkedCurveModal('spot');
      } else {
        openRetailCurveModal(pricingMode);
      }
    });
  }

  function openRetailCurveModal(pricingMode) {
    if (pricingMode === 'M1') {
      const html = `<div class="curve-modal-controls">
        <span>省份</span><select id="wb-admin-province"></select>
        <span>月份</span><select id="wb-admin-month"></select>
        <span>用电性质</span><select id="wb-admin-biz"></select>
        <span>电压等级</span><select id="wb-admin-voltage"></select>
      </div>
      <div id="wb-pricing-curve-chart" class="curve-modal-chart"></div>
      <div id="wb-pricing-curve-table"></div>`;
      showHtmlModal('选择曲线 - 行政分时', html, () => {
        setMainPricingCurveValue('admin');
        markChanged();
      }, initAdminCurveChooser);
      return;
    }

    if (pricingMode === 'M5') {
      const html = `<div class="curve-modal-controls">
        <span>固定价格</span><input id="wb-flat-price" type="number" step="0.01" value="0.55">
        <span>元/kWh</span>
      </div>
      <div id="wb-pricing-curve-chart" class="curve-modal-chart"></div>`;
      showHtmlModal('选择曲线 - 固定价格', html, () => {
        setMainPricingCurveValue('flat');
        markChanged();
      }, () => renderPriceBarChart('wb-pricing-curve-chart', Array(24).fill(0.55), '固定价格'));
      el('wb-flat-price')?.addEventListener('input', () => {
        const price = Number(el('wb-flat-price')?.value || 0.55);
        renderPriceBarChart('wb-pricing-curve-chart', Array(24).fill(price), '固定价格');
      });
      return;
    }

    const options = Object.entries(WB_TARIFF_CURVES).map(([key, curve]) => `<option value="${key}">${curve.label}</option>`).join('');
    const html = `<div class="curve-modal-controls"><span>合同分时曲线</span><select id="wb-contract-curve">${options}</select></div>
      <div id="wb-pricing-curve-chart" class="curve-modal-chart"></div>
      <div id="wb-pricing-curve-table"></div>`;
    showHtmlModal('选择曲线 - 合同分时', html, () => {
      setMainPricingCurveValue('contract');
      markChanged();
    }, () => {
      const select = el('wb-contract-curve');
      const update = () => renderTouPreview(select.value);
      select.addEventListener('change', update);
      update();
    });
  }

  function openLinkedCurveModal(category) {
    const v = activeVariant() || {};
    const isSpot = category === 'spot';
    const title = isSpot ? '选择曲线 - 现货联动' : '选择曲线 - 月度联动';
    const options = pricingCurveItemsForMode(isSpot ? 'M4' : 'M4-contract');
    const selected = isSpot
      ? (v.run_curves?.spot_curve_id ? `${v.run_curves.spot_curve_id}::${v.run_curves.spot_price_kind || 'day_ahead'}` : '')
      : (v.run_curves?.monthly_curve_id || '');
    const ratio = isSpot ? Number(v.run_curves?.spot_link_ratio ?? 0.90) : Number(v.run_curves?.monthly_link_ratio ?? 0.70);
    const fixed = isSpot ? Number(v.run_curves?.spot_fixed_price ?? 0.40) : Number(v.run_curves?.monthly_fixed_price ?? 0.40);
    const ratioLabel = isSpot ? '现货联动比例（%）' : '月度联动比例（%）';
    const curveLabel = isSpot ? '现货价格曲线' : '月度综合价曲线（全省统一）';
    const html = `<div class="curve-modal-controls">
        <span>${ratioLabel}</span><input id="wb-link-ratio" type="number" min="0" max="100" step="1" value="${(ratio * 100).toFixed(0)}">
        <span>固定价格（元/kWh）</span><input id="wb-link-fixed" type="number" step="0.01" value="${fixed}">
      </div>
      <div class="curve-modal-controls">
        <span>${curveLabel}</span><select id="wb-link-curve">${optionHtml(options)}</select>
      </div>
      <div class="curve-stack-row">
        <div class="metric-chip"><div class="label">联动分量均值</div><div class="value" id="wb-link-market-avg">--</div></div>
        <div class="metric-chip"><div class="label">固定分量</div><div class="value" id="wb-link-fixed-comp">--</div></div>
      </div>
      <div id="wb-pricing-curve-chart" class="curve-modal-chart"></div>`;
    showHtmlModal(title, html, () => {
      const choice = selectedLinkedCurveChoice();
      if (!choice.value) return;
      setMainPricingCurveValue(choice.rawValue);
      const target = state.variants[state.activeKey];
      if (isSpot) {
        target.run_curves.spot_curve_id = choice.value;
        target.run_curves.spot_price_kind = choice.priceKind || 'day_ahead';
        target.run_curves.spot_link_ratio = boundedPercent(el('wb-link-ratio')?.value, 90);
        target.run_curves.spot_fixed_price = Number(el('wb-link-fixed')?.value || 0.40);
      } else {
        target.run_curves.monthly_curve_id = choice.value;
        target.run_curves.monthly_link_ratio = boundedPercent(el('wb-link-ratio')?.value, 70);
        target.run_curves.monthly_fixed_price = Number(el('wb-link-fixed')?.value || 0.40);
      }
      markChanged();
    }, () => {
      const curveSel = el('wb-link-curve');
      if (selected && [...curveSel.options].some(opt => opt.value === selected)) curveSel.value = selected;
      ['wb-link-curve', 'wb-link-ratio', 'wb-link-fixed'].forEach(id => el(id)?.addEventListener('change', () => updateLinkedCurvePreview(category)));
      el('wb-link-ratio')?.addEventListener('input', () => updateLinkedCurvePreview(category));
      el('wb-link-fixed')?.addEventListener('input', () => updateLinkedCurvePreview(category));
      updateLinkedCurvePreview(category);
    });
  }

  function selectedLinkedCurveChoice() {
    const select = el('wb-link-curve');
    const option = select?.selectedOptions?.[0];
    return {
      rawValue: select?.value || '',
      value: option?.dataset?.curveId || select?.value || '',
      priceKind: option?.dataset?.priceKind || '',
    };
  }

  function boundedPercent(value, fallback) {
    const n = Number(value);
    if (Number.isNaN(n)) return fallback / 100;
    return Math.min(100, Math.max(0, n)) / 100;
  }

  async function updateLinkedCurvePreview(category) {
    const choice = selectedLinkedCurveChoice();
    if (!choice.value) return;
    const ratio = boundedPercent(el('wb-link-ratio')?.value, category === 'spot' ? 90 : 70);
    const fixed = Number(el('wb-link-fixed')?.value || 0.40);
    const query = `/simple-day/curve?category=${category}&curve_id=${encodeURIComponent(choice.value)}&price_kind=${encodeURIComponent(choice.priceKind || '')}`;
    const data = await App.api(query);
    const base = data.values || [];
    const marketPart = base.map(v => +(Number(v) * ratio).toFixed(4));
    const fixedPart = base.map(() => +(fixed * (1 - ratio)).toFixed(4));
    const avg = marketPart.reduce((a, b) => a + b, 0) / (marketPart.length || 1);
    const fixedComp = fixedPart[0] || 0;
    if (el('wb-link-market-avg')) el('wb-link-market-avg').textContent = `${avg.toFixed(4)} 元/kWh`;
    if (el('wb-link-fixed-comp')) el('wb-link-fixed-comp').textContent = `${fixedComp.toFixed(4)} 元/kWh`;
    renderStackedPriceChart('wb-pricing-curve-chart', marketPart, fixedPart, category === 'spot' ? '现货联动分量' : '月度联动分量');
  }

  function setMainPricingCurveValue(value) {
    const select = el('sel-pricing-curve');
    if (!select) return;
    if ([...select.options].some(opt => opt.value === value)) select.value = value;
  }

  async function initAdminCurveChooser() {
    const provinceSel = el('wb-admin-province');
    const monthSel = el('wb-admin-month');
    const bizSel = el('wb-admin-biz');
    const voltageSel = el('wb-admin-voltage');
    const provinces = await App.api('/tariff/administrative/provinces');
    provinceSel.innerHTML = provinces.map(p => `<option value="${p}" ${p === 'Henan' ? 'selected' : ''}>${p}</option>`).join('');
    const update = async () => {
      const province = provinceSel.value;
      const months = await App.api(`/tariff/administrative/months/${province}`);
      const prevMonth = monthSel.value;
      monthSel.innerHTML = months.map(m => `<option value="${m}" ${m === prevMonth ? 'selected' : ''}>${m}</option>`).join('');
      const month = monthSel.value || months[0];
      const bizTypes = await App.api(`/tariff/administrative/business-types/${province}/${month}`);
      const prevBiz = bizSel.value;
      bizSel.innerHTML = bizTypes.map(b => `<option value="${b}" ${b === prevBiz ? 'selected' : ''}>${b}</option>`).join('');
      const data = await App.api(`/tariff/administrative/data/${province}/${month}/${bizSel.value || bizTypes[0]}`);
      const validVoltages = data.voltage_levels.filter(v => data.data.some(row => row[v] != null));
      const prevVolt = voltageSel.value;
      voltageSel.innerHTML = validVoltages.map(v => `<option value="${v}" ${v === prevVolt ? 'selected' : ''}>${v}</option>`).join('');
      renderAdminPreview(data.data, voltageSel.value || validVoltages[0]);
    };
    [provinceSel, monthSel, bizSel, voltageSel].forEach(select => select.addEventListener('change', update));
    await update();
  }

  function renderAdminPreview(rows, voltageCol) {
    const prices = rows.map(row => Number(row[voltageCol] || 0));
    renderPriceBarChart('wb-pricing-curve-chart', prices, '行政分时');
    const html = `<table class="data-table"><tr><th>小时</th><th>时段</th><th>电价 (元/kWh)</th></tr>${
      rows.map(row => `<tr><td>${row.hour}:00</td><td>${row['时段'] || '--'}</td><td>${Number(row[voltageCol] || 0).toFixed(4)}</td></tr>`).join('')
    }</table>`;
    if (el('wb-pricing-curve-table')) el('wb-pricing-curve-table').innerHTML = html;
  }

  function renderTouPreview(curveKey) {
    const curve = WB_TARIFF_CURVES[curveKey] || WB_TARIFF_CURVES.typical;
    const hourly = new Array(24).fill(0);
    curve.periods.forEach(period => {
      for (let h = period.start; h < period.end; h++) hourly[h] = period.price;
    });
    renderPriceBarChart('wb-pricing-curve-chart', hourly, curve.label);
    const rows = curve.periods.map(period => `<tr><td>${period.period}</td><td>${period.start}:00 ~ ${period.end}:00</td><td>${period.price.toFixed(4)}</td></tr>`).join('');
    if (el('wb-pricing-curve-table')) {
      el('wb-pricing-curve-table').innerHTML = `<table class="data-table"><tr><th>时段</th><th>时间范围</th><th>电价 (元/kWh)</th></tr>${rows}</table>`;
    }
  }

  function renderPriceBarChart(containerId, values, name) {
    const target = el(containerId);
    if (!target) return;
    if (pricingCurveChart) pricingCurveChart.dispose();
    pricingCurveChart = echarts.init(target);
    pricingCurveChart.setOption({
      tooltip:{trigger:'axis',backgroundColor:'#1e2330',borderColor:'#2e3446',textStyle:{color:'#f0f2f5',fontSize:11}},
      grid:{left:50,right:24,top:24,bottom:26},
      xAxis:{type:'category',data:Array.from({length:24},(_,i)=>`${i}`),axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:9,interval:0}},
      yAxis:{type:'value',name:'元/kWh',nameTextStyle:{color:'#7a8298',fontSize:9},axisLabel:{color:'#7a8298',fontSize:9},splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}}},
      series:[{name,type:'bar',barWidth:'58%',data:values.map(v => ({value:v,itemStyle:{color:v >= 0.9 ? '#f87171' : (v >= 0.5 ? '#fbbf24' : '#5ea3ff')}}))}],
    });
  }

  function renderStackedPriceChart(containerId, marketPart, fixedPart, marketName) {
    const target = el(containerId);
    if (!target) return;
    if (pricingCurveChart) pricingCurveChart.dispose();
    pricingCurveChart = echarts.init(target);
    pricingCurveChart.setOption({
      tooltip:{trigger:'axis',backgroundColor:'#1e2330',borderColor:'#2e3446',textStyle:{color:'#f0f2f5',fontSize:11}},
      legend:{top:0,textStyle:{color:'#b0b8c8',fontSize:11}},
      grid:{left:50,right:24,top:34,bottom:26},
      xAxis:{type:'category',data:Array.from({length:24},(_,i)=>`${i}`),axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:9,interval:0}},
      yAxis:{type:'value',name:'元/kWh',nameTextStyle:{color:'#7a8298',fontSize:9},axisLabel:{color:'#7a8298',fontSize:9},splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}}},
      series:[
        {name:marketName,type:'bar',stack:'price',barWidth:'58%',data:marketPart,itemStyle:{color:'#7EA8FA'}},
        {name:'固定单价分量',type:'bar',stack:'price',barWidth:'58%',data:fixedPart,itemStyle:{color:'#F2A104'}},
      ],
    });
  }

  async function runCalculation() {
    persistCurrentUIToMemory(false);
    const v = activeVariant();
    const scenarioId = App.state.currentScenario || App.state.scenarios[0]?.id;
    if (!scenarioId) {
      alert('没有可用的方案');
      return;
    }
    App.analysis._setLoading?.(true);
    try {
      const result = await App.api('/calculate', {
        method: 'POST',
        body: JSON.stringify({
          scenario_id: scenarioId,
          variant_key: state.activeKey,
          pricing_mode: v.pricing_mode,
          business_model: v.business_model || 'B1',
          system: v.system,
          ess_params: v.ess_params,
          pv_params: v.pv_params,
          financial_params: v.financial_params,
          run_curves: v.run_curves,
          private_overrides: v.private_overrides,
          wholesale_overrides: v.wholesale_overrides,
        }),
      });
      App.state.result = result;
      publishAlgorithmSnapshot(result, v);
      App.analysis.renderResult(result);
      updateCompositionUI(false);
      const tag = el('tag-calc');
      if (tag) {
        tag.textContent = '计算完成';
        tag.classList.add('done');
      }
    } catch (e) {
      alert('计算失败: ' + e.message);
    } finally {
      App.analysis._setLoading?.(false);
    }
  }

  function publishAlgorithmSnapshot(result, variant) {
    try {
      localStorage.setItem('ess_algorithm_latest_result', JSON.stringify({
        result,
        variant,
        scenarioId: App.state.currentScenario || App.state.scenarios[0]?.id || null,
        variantKey: state.activeKey,
        timestamp: Date.now(),
      }));
    } catch (e) {
      console.warn('Failed to publish algorithm snapshot', e);
    }
  }

  function openCompare() {
    persistCurrentUIToMemory(false);
    if (App.compare?.loadFromSlots) {
      App.compare.loadFromSlots(Object.values(state.variants).map(v => ({
        scenarioId: App.state.currentScenario,
        pricingMode: v.pricing_mode,
        businessModel: v.business_model,
        variantKey: v.key,
        variant: v,
        label: v.key,
      })));
    }
    document.querySelector('.top-nav-item[data-page="compare"]')?.click();
  }

  async function init() {
    await initRunCurveControls();
    const scenarioId = App.state.currentScenario || App.state.scenarios[0]?.id;
    if (scenarioId) await loadParent(scenarioId);
    renderSlots();
  }

  App.workbench = {
    init,
    loadParent,
    switchSlot,
    addSlot,
    stashActiveVariant,
    saveParentScenario,
    markChanged,
    refreshPricingCurveOptions,
    updateCompositionUI,
    openDeviceModal,
    openPricingCurveModal,
    openLoadModal,
    runCalculation,
    openCompare,
    state,
  };
})();
