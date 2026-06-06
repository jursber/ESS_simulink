// ===== charts.js =====

// 实体色彩常量
const C = { src: '#F2A104', grid: '#7EA8FA', load: '#D4ADFC', ess: '#4E9F3D', soc: '#34d399', accent: '#7EA8FA' };

// --- 千分位格式化 ---
function fmtNum(v, decimals) {
  if (v == null || isNaN(v)) return '--';
  const d = decimals != null ? decimals : (Math.abs(v) >= 100 ? 0 : 1);
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d });
}

// --- ECharts 通用配置 ---
const chartTooltip = { trigger: 'axis', backgroundColor: '#1E1E1E', borderColor: '#333', textStyle: { color: 'rgba(250,250,250,0.87)', fontSize: 11 } };
const chartGrid = { left: 46, right: 46, top: 30, bottom: 20, containLabel: true };
const axisStyle = { axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: 'rgba(176,176,176,0.60)', fontSize: 9, interval: 0 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } };

// --- 调度曲线 ---
let dispatchChart = null;

function renderDispatchChart(ts) {
  const el = document.getElementById('chart-dispatch');
  if (!el) return;
  if (dispatchChart) dispatchChart.dispose();
  dispatchChart = echarts.init(el);

  dispatchChart.setOption({
    tooltip: chartTooltip,
    legend: {
      data: ['负荷', '储能', 'SOC', '光伏'],
      textStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 11 },
      top: 0,
    },
    grid: { left: 50, right: 50, top: 36, bottom: 24, containLabel: true },
    xAxis: {
      type: 'category',
      data: ts.hours.map(h => `${h}:00`),
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: 'rgba(176,176,176,0.60)', fontSize: 10, interval: 0 },
    },
    yAxis: [
      {
        type: 'value', name: 'kW',
        nameTextStyle: { color: 'rgba(176,176,176,0.60)' },
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { color: 'rgba(176,176,176,0.60)', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
      },
      {
        type: 'value', name: 'SOC %',
        nameTextStyle: { color: 'rgba(176,176,176,0.60)' },
        min: 0, max: 100,
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { color: 'rgba(176,176,176,0.60)', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      { name: '负荷', type: 'line', data: ts.load_real, smooth: true, symbol: 'none', lineStyle: { color: C.load, width: 0.5 }, areaStyle: { color: 'rgba(212,173,252,0.08)' } },
      { name: '储能', type: 'line', data: ts.load_ess, smooth: true, symbol: 'none', lineStyle: { color: C.ess, width: 0.5 }, areaStyle: { color: 'rgba(78,159,61,0.10)' } },
      { name: 'SOC', type: 'line', yAxisIndex: 1, data: (ts.soc || []).map(v => v * 100), smooth: true, symbol: 'none', lineStyle: { color: C.soc, width: 0.5, type: 'dashed' } },
      { name: '光伏', type: 'line', data: ts.pv_power || [], smooth: true, symbol: 'none', lineStyle: { color: C.src, width: 0.5 }, areaStyle: { color: 'rgba(242,161,4,0.08)' } },
    ],
  });
  window.addEventListener('resize', () => dispatchChart && dispatchChart.resize());
}

// --- 多方收益图表 ---
let chartUserPrice = null, chartEssPower = null, chartPriceCurve = null;

function renderWelfareCharts(ts) {
  const hours = ts.hours.map(h => `${h}`);
  const mockPriceUser = Array.from({length:24},(_,i)=>{
    const base=0.45;const peak=Math.sin((i-6)*Math.PI/12)*0.35;
    return +(base+(i>=8&&i<=21?peak:(i>=0&&i<=6?-0.15:0))).toFixed(4);
  });
  const mockPriceDa = Array.from({length:24},(_,i)=>{
    const base=0.35;const wave=Math.sin((i-5)*Math.PI/13)*0.25;
    return +(base+(i>=7&&i<=20?wave:(i<=5?-0.1:0))).toFixed(4);
  });
  const mockPriceRt = mockPriceDa.map((v,i)=>+(v+(Math.sin(i*1.5)*0.05-0.02)).toFixed(4));

  // 1. 用户侧购电电价曲线
  const elUserPrice = document.getElementById('chart-user-price');
  if (elUserPrice) {
    if (chartUserPrice) chartUserPrice.dispose();
    chartUserPrice = echarts.init(elUserPrice);
    chartUserPrice.setOption({
      tooltip: chartTooltip,
      grid: { left: 8, right: 8, top: 10, bottom: 18, containLabel: true },
      xAxis: { type: 'category', data: hours, ...axisStyle },
      yAxis: { type: 'value', name: '元/kWh', nameTextStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 9 }, ...axisStyle },
      series: [{
        name: '用户侧电价', type: 'line', data: (ts.price_user && ts.price_user.length ? ts.price_user : mockPriceUser),
        smooth: true, symbol: 'none',
        lineStyle: { color: C.src, width: 0.5 },
        areaStyle: { color: 'rgba(242,161,4,0.08)' },
      }],
    });
  }

  // 2. 储能功率 + SOC + 光伏功率
  const elEssPower = document.getElementById('chart-ess-power');
  if (elEssPower) {
    if (chartEssPower) chartEssPower.dispose();
    chartEssPower = echarts.init(elEssPower);
    chartEssPower.setOption({
      tooltip: chartTooltip,
      legend: { data: ['储能功率', 'SOC', '光伏功率'], textStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 9 }, top: 0 },
      grid: { left: 8, right: 8, top: 10, bottom: 18, containLabel: true },
      xAxis: { type: 'category', data: hours, ...axisStyle },
      yAxis: [
        { type: 'value', name: 'kW', nameTextStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 9 }, ...axisStyle },
        { type: 'value', name: 'SOC %', nameTextStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 9 }, min: 0, max: 100, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: 'rgba(176,176,176,0.60)', fontSize: 9 }, splitLine: { show: false } },
      ],
      series: [
        { name: '储能功率', type: 'line', data: ts.load_ess, smooth: true, symbol: 'none', lineStyle: { color: C.ess, width: 0.5 }, areaStyle: { color: 'rgba(78,159,61,0.10)' } },
        { name: 'SOC', type: 'line', yAxisIndex: 1, data: (ts.soc || []).map(v => v * 100), smooth: true, symbol: 'none', lineStyle: { color: C.soc, width: 0.5, type: 'dashed' } },
        { name: '光伏功率', type: 'line', data: ts.pv_power || [], smooth: true, symbol: 'none', lineStyle: { color: C.src, width: 0.5 }, areaStyle: { color: 'rgba(242,161,4,0.08)' } },
      ],
    });
  }

  // 3. 日前电价 + 实时电价
  const elPriceCurve = document.getElementById('chart-price-curve');
  if (elPriceCurve) {
    if (chartPriceCurve) chartPriceCurve.dispose();
    chartPriceCurve = echarts.init(elPriceCurve);
    chartPriceCurve.setOption({
      tooltip: chartTooltip,
      legend: { data: ['日前电价', '实时电价'], textStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 9 }, top: 0 },
      grid: { left: 8, right: 8, top: 10, bottom: 18, containLabel: true },
      xAxis: { type: 'category', data: hours, ...axisStyle },
      yAxis: { type: 'value', name: '元/kWh', nameTextStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 9 }, ...axisStyle },
      series: [
        { name: '日前电价', type: 'line', data: (ts.price_da && ts.price_da.length ? ts.price_da : mockPriceDa), smooth: true, symbol: 'none', lineStyle: { color: C.grid, width: 0.5 } },
        { name: '实时电价', type: 'line', data: (ts.price_rt && ts.price_rt.length ? ts.price_rt : mockPriceRt), smooth: true, symbol: 'none', lineStyle: { color: '#EB5757', width: 0.5, type: 'dashed' } },
      ],
    });
  }

  window.addEventListener('resize', () => {
    chartUserPrice && chartUserPrice.resize();
    chartEssPower && chartEssPower.resize();
    chartPriceCurve && chartPriceCurve.resize();
  });
}

// --- 典型日能量分析图表 ---
let chartCostComposition = null, chartEnergyComposition = null;

function renderEnergyAnalysisCharts(ts) {
  const hours = ts.hours.map(h => `${h}:00`);

  // 1. 全时段成本构成 - 堆积柱状图
  const elCost = document.getElementById('chart-cost-composition');
  if (elCost) {
    if (chartCostComposition) chartCostComposition.dispose();
    chartCostComposition = echarts.init(elCost);
    chartCostComposition.setOption({
      tooltip: { ...chartTooltip, trigger: 'axis', formatter: function(params) {
        let s = params[0].axisValue + '<br/>';
        let total = 0;
        params.forEach(p => { s += p.marker + p.seriesName + ': ' + fmtNum(p.value) + ' 元<br/>'; total += p.value; });
        s += '<b>合计: ' + fmtNum(total) + ' 元</b>';
        return s;
      }},
      legend: { data: ['网购电', '储能返还'], textStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 10 }, top: 0 },
      grid: { left: 8, right: 20, top: 36, bottom: 24, containLabel: true },
      xAxis: { type: 'category', data: hours, ...axisStyle },
      yAxis: { type: 'value', name: '元', nameTextStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 11 }, ...axisStyle },
      series: [
        { name: '网购电', type: 'bar', stack: 'cost', data: ts.cost_grid || [], itemStyle: { color: C.grid } },
        { name: '储能返还', type: 'bar', stack: 'cost', data: ts.cost_ess || [], itemStyle: { color: C.ess } },
      ],
    });
  }

  // 2. 全时段能量构成 - 正负堆叠双向柱状图
  const elEnergy = document.getElementById('chart-energy-composition');
  if (elEnergy) {
    if (chartEnergyComposition) chartEnergyComposition.dispose();
    chartEnergyComposition = echarts.init(elEnergy);

    // 供给侧为正（光伏、电网购电、储能放电），消耗侧为负（用户负荷、储能充电）
    const pvPower = ts.pv_power || [];
    const gridSupply = (ts.energy_grid || []).map(v => Math.abs(v));
    const essDischarge = (ts.energy_ess || []).map(v => Math.max(0, v));
    const essCharge = (ts.energy_ess || []).map(v => Math.min(0, v));
    const loadDemand = (ts.energy_load || []).map(v => -Math.abs(v));

    chartEnergyComposition.setOption({
      tooltip: { ...chartTooltip, trigger: 'axis', formatter: function(params) {
        let s = params[0].axisValue + '<br/>';
        params.forEach(p => { if (Math.abs(p.value) > 0.01) s += p.marker + p.seriesName + ': ' + fmtNum(Math.abs(p.value)) + ' kW<br/>'; });
        return s;
      }},
      legend: { data: ['光伏发电', '电网供电', '储能放电', '储能充电', '用户负荷'], textStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 10 }, top: 0 },
      grid: { left: 8, right: 20, top: 36, bottom: 24, containLabel: true },
      xAxis: { type: 'category', data: hours, ...axisStyle },
      yAxis: { type: 'value', name: 'kW', nameTextStyle: { color: 'rgba(176,176,176,0.60)', fontSize: 11 }, ...axisStyle },
      series: [
        { name: '光伏发电', type: 'bar', stack: 'supply', data: pvPower, itemStyle: { color: C.src }, barMaxWidth: 12 },
        { name: '电网供电', type: 'bar', stack: 'supply', data: gridSupply, itemStyle: { color: C.grid }, barMaxWidth: 12 },
        { name: '储能放电', type: 'bar', stack: 'supply', data: essDischarge, itemStyle: { color: C.ess }, barMaxWidth: 12 },
        { name: '储能充电', type: 'bar', stack: 'demand', data: essCharge, itemStyle: { color: 'rgba(78,159,61,0.5)' }, barMaxWidth: 12 },
        { name: '用户负荷', type: 'bar', stack: 'demand', data: loadDemand, itemStyle: { color: C.load }, barMaxWidth: 12 },
      ],
    });
  }

  // 3. 分时电量汇总
  const elTou = document.getElementById('tou-summary');
  if (elTou) {
    const tou = ts.tou_summary || {};
    const total = tou._total || 1;
    elTou.querySelectorAll('.tou-block').forEach(block => {
      const period = block.dataset.period;
      const val = tou[period] || 0;
      const kWh = Math.round(val);
      const pct = total > 0 ? +(val / total * 100).toFixed(1) : 0;
      const barFill = block.querySelector('.tou-bar-fill');
      const valueEl = block.querySelector('.tou-value');
      if (barFill) barFill.style.width = pct + '%';
      if (valueEl) valueEl.textContent = kWh.toLocaleString() + ' kWh (' + pct + '%)';
    });
  }

  window.addEventListener('resize', () => {
    chartCostComposition && chartCostComposition.resize();
    chartEnergyComposition && chartEnergyComposition.resize();
  });
}

// --- App 注册 ---
App.charts = { renderDispatchChart, renderWelfareCharts, renderEnergyAnalysisCharts, fmtNum };
