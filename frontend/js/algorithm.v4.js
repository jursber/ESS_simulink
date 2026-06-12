(function () {
  const STORAGE_KEY = 'ess_algorithm_latest_result';
  const C = {
    grid: '#2563eb',
    load: '#7c3aed',
    ess: '#16a34a',
    soc: '#0f766e',
    user: '#d97706',
    da: '#2563eb',
    rt: '#dc2626',
    axis: '#94a3b8',
    text: '#475569',
    split: '#e5e7eb',
  };

  let dispatchChart = null;
  let priceChart = null;

  function fmt(v, d = 2) {
    if (v == null || Number.isNaN(Number(v))) return '--';
    return Number(v).toLocaleString('zh-CN', {
      minimumFractionDigits: d,
      maximumFractionDigits: d,
    });
  }

  function readSnapshot() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      console.error('Failed to read algorithm snapshot', e);
      return null;
    }
  }

  function hours(ts) {
    return (ts?.hours || Array.from({ length: 24 }, (_, i) => i)).map(h => `${h}:00`);
  }

  function chartBase() {
    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#d8dee9',
        textStyle: { color: '#172033', fontSize: 11 },
        extraCssText: 'box-shadow:0 8px 24px rgba(15,23,42,.12);',
      },
      grid: { left: 52, right: 58, top: 42, bottom: 26, containLabel: true },
      xAxis: {
        type: 'category',
        axisLine: { lineStyle: { color: C.axis } },
        axisLabel: { color: C.text, fontSize: 10, interval: 0 },
      },
    };
  }

  function renderCharts(result) {
    const ts = result?.time_series;
    const dispatchEl = document.getElementById('algo-chart-dispatch');
    const priceEl = document.getElementById('algo-chart-price');
    if (!ts || !dispatchEl || !priceEl) return;

    if (dispatchChart) dispatchChart.dispose();
    if (priceChart) priceChart.dispose();
    dispatchChart = echarts.init(dispatchEl);
    priceChart = echarts.init(priceEl);

    const x = hours(ts);
    dispatchChart.setOption({
      ...chartBase(),
      legend: {
        top: 10,
        textStyle: { color: C.text, fontSize: 11 },
        data: ['关口表功率', '用户负荷', '算法策略-储能功率', 'SOC'],
      },
      xAxis: { ...chartBase().xAxis, data: x },
      yAxis: [
        {
          type: 'value',
          name: 'kW/kWh',
          nameTextStyle: { color: C.text, fontSize: 10 },
          axisLabel: { color: C.text, fontSize: 10 },
          splitLine: { lineStyle: { color: C.split } },
        },
        {
          type: 'value',
          name: 'SOC %',
          min: 0,
          max: 100,
          nameTextStyle: { color: C.text, fontSize: 10 },
          axisLabel: { color: C.text, fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      series: [
        { name: '关口表功率', type: 'line', data: ts.load_grid || [], smooth: false, symbol: 'none', lineStyle: { color: C.grid, width: 1.4 } },
        { name: '用户负荷', type: 'line', data: ts.load_real || [], smooth: false, symbol: 'none', lineStyle: { color: C.load, width: 1.2 } },
        { name: '算法策略-储能功率', type: 'bar', data: ts.load_ess || [], barWidth: '48%', itemStyle: { color: C.ess } },
        { name: 'SOC', type: 'line', yAxisIndex: 1, data: (ts.soc || []).map(v => v * 100), smooth: false, symbol: 'none', lineStyle: { color: C.soc, width: 1.4, type: 'dashed' } },
      ],
    });

    priceChart.setOption({
      ...chartBase(),
      legend: {
        top: 8,
        textStyle: { color: C.text, fontSize: 10 },
        data: ['用户侧电价', '日前价格', '实时价格'],
      },
      grid: { left: 52, right: 30, top: 34, bottom: 22, containLabel: true },
      xAxis: { ...chartBase().xAxis, data: x },
      yAxis: {
        type: 'value',
        name: '元/kWh',
        nameTextStyle: { color: C.text, fontSize: 10 },
        axisLabel: { color: C.text, fontSize: 10 },
        splitLine: { lineStyle: { color: C.split } },
      },
      series: [
        { name: '用户侧电价', type: 'line', data: ts.price_user || [], smooth: false, symbol: 'none', lineStyle: { color: C.user, width: 1.2 } },
        { name: '日前价格', type: 'line', data: ts.price_da || [], smooth: false, symbol: 'none', lineStyle: { color: C.da, width: 1.1 } },
        { name: '实时价格', type: 'line', data: ts.price_rt || [], smooth: false, symbol: 'none', lineStyle: { color: C.rt, width: 1.1, type: 'dashed' } },
      ],
    });
  }

  function boolText(v) {
    return v ? '启用' : '未启用';
  }

  function metricSummary(result) {
    const ts = result?.time_series || {};
    const loadGrid = ts.load_grid || [];
    const soc = ts.soc || [];
    const loadEss = ts.load_ess || [];
    const gridExport = loadGrid.reduce((s, v) => s + Math.max(0, -v), 0);
    const charge = loadEss.reduce((s, v) => s + Math.max(0, -v), 0);
    const discharge = loadEss.reduce((s, v) => s + Math.max(0, v), 0);
    return {
      gridExport,
      charge,
      discharge,
      socMin: soc.length ? Math.min(...soc) : null,
      socMax: soc.length ? Math.max(...soc) : null,
      gridMin: loadGrid.length ? Math.min(...loadGrid) : null,
      gridMax: loadGrid.length ? Math.max(...loadGrid) : null,
    };
  }

  function card(title, rows) {
    return `<div class="algorithm-param-card">
      <h3>${title}</h3>
      ${rows.map(([k, v]) => `<div class="algorithm-kv"><span>${k}</span><span>${v}</span></div>`).join('')}
    </div>`;
  }

  function selectedLabel(id, fallback = '--') {
    const el = document.getElementById(id);
    if (!el) return fallback;
    return el.selectedOptions?.[0]?.textContent || el.value || fallback;
  }

  function renderParams(snapshot) {
    const result = snapshot.result || {};
    const variant = snapshot.variant || {};
    const overview = result.overview || {};
    const investment = result.investment || {};
    const pvInvestment = result.pv_investment || null;
    const m = metricSummary(result);
    const runCurves = variant.run_curves || {};
    const wholesale = variant.wholesale_overrides || {};
    const system = variant.system || {};

    const noPvExportFlag = !system.pv && m.gridExport > 1e-6 ? '异常：存在反送' : '通过';
    const html = [
      card('系统构成', [
        ['用户负荷', boolText(system.net_load !== false)],
        ['表后储能', boolText(system.ess !== false)],
        ['分布式光伏', boolText(!!system.pv)],
        ['售电公司', boolText(!!system.retail)],
      ]),
      card('电价与结算', [
        ['零售电价', overview.pricing_mode_label || variant.pricing_mode || '--'],
        ['批发规则', wholesale.settlement_mode || '--'],
        ['合约曲线', wholesale.contract_curve_profile || '--'],
        ['日前曲线', wholesale.dayahead_curve_profile || '--'],
      ]),
      card('运行曲线', [
        ['负荷曲线', runCurves.load_profile || '--'],
        ['光伏曲线', runCurves.pv_curve_id || '--'],
        ['现货曲线', runCurves.spot_curve_id || '--'],
        ['月度曲线', runCurves.monthly_curve_id || '--'],
      ]),
      card('设备参数', [
        ['储能容量', `${fmt(overview.ess_cap_mwh, 2)} MWh`],
        ['储能功率', `${fmt((overview.ess_power_kw || 0) / 1000, 2)} MW`],
        ['往返效率', `${fmt(overview.eta_pct, 2)}%`],
        ['光伏装机', `${fmt(overview.pv_cap_kw || 0, 0)} kWp`],
      ]),
      card('调度结果', [
        ['总充电量', `${fmt(m.charge, 1)} kWh`],
        ['总放电量', `${fmt(m.discharge, 1)} kWh`],
        ['等效循环', `${fmt(investment.equivalent_cycles, 3)} 次`],
        ['无光伏反送', noPvExportFlag],
      ]),
      card('边界检查', [
        ['SOC 最小', m.socMin == null ? '--' : `${fmt(m.socMin * 100, 2)}%`],
        ['SOC 最大', m.socMax == null ? '--' : `${fmt(m.socMax * 100, 2)}%`],
        ['关口最小', m.gridMin == null ? '--' : `${fmt(m.gridMin, 1)} kWh`],
        ['反送电量', `${fmt(m.gridExport, 1)} kWh`],
      ]),
      card('收益摘要', [
        ['日套利收益', `${fmt(investment.daily_arbitrage_yuan, 2)} 元`],
        ['储能 IRR', investment.irr_pct == null ? '--' : `${fmt(investment.irr_pct, 2)}%`],
        ['光伏自用率', pvInvestment ? `${fmt(pvInvestment.self_rate * 100, 2)}%` : '--'],
        ['更新时间', snapshot.timestamp ? new Date(snapshot.timestamp).toLocaleString('zh-CN') : '--'],
      ]),
      card('页面当前选择', [
        ['零售侧电价', selectedLabel('sel-retail-pricing', variant.pricing_mode || '--')],
        ['调度目标', selectedLabel('sel-dispatch-target', variant.dispatch_target || '--')],
        ['负荷下拉', selectedLabel('sel-load-profile', runCurves.load_profile || '--')],
        ['光伏下拉', selectedLabel('sel-pv-curve-id', runCurves.pv_curve_id || '--')],
      ]),
    ].join('');

    document.getElementById('algo-param-grid').innerHTML = html;
  }

  function renderEmpty() {
    const grid = document.getElementById('algo-param-grid');
    const status = document.getElementById('algo-status');
    const dispatchEl = document.getElementById('algo-chart-dispatch');
    const priceEl = document.getElementById('algo-chart-price');
    if (status) status.textContent = '等待计算结果';
    if (grid) grid.innerHTML = '';
    if (dispatchEl) dispatchEl.innerHTML = '<div class="algorithm-empty">单方案页面点击“开始计算”后，这里会自动显示最新算法结果。</div>';
    if (priceEl) priceEl.innerHTML = '<div class="algorithm-empty">等待电价曲线</div>';
  }

  function render(snapshot) {
    if (!snapshot?.result?.time_series) {
      renderEmpty();
      return;
    }
    const status = document.getElementById('algo-status');
    if (status) {
      const key = snapshot.variantKey || snapshot.variant?.key || 'A';
      status.textContent = `已同步：方案 ${key} · ${new Date(snapshot.timestamp || Date.now()).toLocaleTimeString('zh-CN')}`;
    }
    renderCharts(snapshot.result);
    renderParams(snapshot);
  }

  function refresh() {
    render(readSnapshot());
  }

  window.addEventListener('storage', event => {
    if (event.key === STORAGE_KEY) refresh();
  });
  window.addEventListener('resize', () => {
    dispatchChart && dispatchChart.resize();
    priceChart && priceChart.resize();
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refresh();
  });

  refresh();
})();
