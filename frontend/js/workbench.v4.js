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
      },
      run_curves: {
        ...(current.run_curves || {}),
        load_profile: el('sel-load-profile')?.value || current.run_curves?.load_profile || 'daily_default',
        pv_curve_id: el('sel-pv-curve-id')?.value || current.run_curves?.pv_curve_id || '',
        spot_curve_id: priceChoice.category === 'spot' ? priceChoice.value : '',
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
    return (items || []).map(item => `<option value="${item[valueKey]}" data-category="${item.category || ''}">${item.label || item.id}</option>`).join('');
  }

  function selectedPricingCurve() {
    const select = el('sel-pricing-curve');
    const option = select?.selectedOptions?.[0];
    return {
      value: select?.value || '',
      category: option?.dataset?.category || '',
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
    const useSpot = pricingMode === 'M4' || pricingMode === 'M4-contract';
    const items = useSpot ? (state.simpleDayCatalog.spot || []).slice(0, 200) : (state.simpleDayCatalog.retail || []);
    priceSel.innerHTML = optionHtml(items);
    const selected = useSpot ? v.run_curves?.spot_curve_id : v.run_curves?.retail_curve_id;
    setSelectValue(priceSel, selected || '');
    if (mark) markChanged();
  }

  function openDeviceModal(kind) {
    const hasEss = !!el('chk-ess')?.checked;
    const hasPv = !!el('chk-pv')?.checked;
    if (kind === 'ess' && !hasEss) return;
    if (kind === 'pv' && !hasPv) return;
    ensureGlobalParams().then(params => {
      const v = activeVariant();
      const values = kind === 'ess'
        ? { ...(params.ess || {}), ...(v.ess_params || {}) }
        : { ...(params.pv || {}), ...(v.pv_params || {}) };
      showModal(kind === 'ess' ? '储能参数' : '光伏参数', deviceFields(kind, values), (form) => {
        const parsed = readFormFields(form);
        if (kind === 'ess') {
          if ('cap_rated' in parsed) parsed.cap_rated = parsed.cap_rated * 1000;
          state.variants[state.activeKey].ess_params = parsed;
        } else {
          state.variants[state.activeKey].pv_params = parsed;
        }
        markChanged();
      });
    });
  }

  function deviceFields(kind, v) {
    if (kind === 'ess') {
      return [
        ['cap_rated', '额定容量 (MWh)', ((v.cap_rated || 1000) / 1000).toFixed(2), 'number', '0.1'],
        ['power_rated', '额定功率 (MW)', v.power_rated || 0.5, 'number', '0.1'],
        ['eta_roundtrip', '往返效率 RTE', v.eta_roundtrip || 0.87, 'number', '0.01'],
        ['soc_min', 'SOC 下限', v.soc_min || 0.1, 'number', '0.01'],
        ['soc_max', 'SOC 上限', v.soc_max || 0.9, 'number', '0.01'],
        ['unit_cost', '建设单价 (元/Wh)', v.unit_cost || 0.9, 'number', '0.1'],
      ];
    }
    return [
      ['cap_rated', '额定装机容量 (kWp)', v.cap_rated || 1.0, 'number', '0.1'],
      ['feed_in_tariff', '光伏上网电价 (元/kWh)', v.feed_in_tariff || 0.4, 'number', '0.01'],
      ['self_use_discount', '本地消纳电费折扣', v.self_use_discount || 0.8, 'number', '0.01'],
      ['unit_cost', '建设单价 (元/Wp)', v.unit_cost || 3.5, 'number', '0.1'],
      ['r_om', '年运维比例', v.r_om || 0.015, 'number', '0.001'],
      ['design_life', '设计寿命 (年)', v.design_life || 25, 'number', '1'],
    ];
  }

  async function openLoadModal() {
    const profiles = await ensureLoadProfiles();
    const v = activeVariant();
    const selected = profiles.find(p => p.name === (v.run_curves?.load_profile || el('sel-load-profile')?.value)) || profiles[0];
    showModal('用户净生产负荷曲线', [
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
    overlay.querySelector('.workbench-modal-title').textContent = title;
    body.innerHTML = fields.map(([id, label, value, type, meta, disabled]) => {
      if (type === 'select') {
        return `<label class="wb-field"><span>${label}</span><select name="${id}" ${disabled ? 'disabled' : ''}>${(meta || []).map(([v,l]) => `<option value="${v}" ${v === value ? 'selected' : ''}>${l}</option>`).join('')}</select></label>`;
      }
      return `<label class="wb-field"><span>${label}</span><input name="${id}" type="${type}" step="${meta || ''}" value="${value ?? ''}" ${disabled ? 'disabled' : ''}></label>`;
    }).join('');
    overlay.querySelector('.workbench-save').onclick = () => {
      onSave(body);
      overlay.style.display = 'none';
    };
    overlay.style.display = 'flex';
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
      out[input.name] = input.type === 'number' ? Number(input.value) : input.value;
    });
    return out;
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
          run_curves: v.run_curves,
          private_overrides: v.private_overrides,
          wholesale_overrides: v.wholesale_overrides,
        }),
      });
      App.state.result = result;
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
    openLoadModal,
    runCalculation,
    openCompare,
    state,
  };
})();
