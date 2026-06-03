// ===== charts.js =====

// --- 7. ECharts 图表 ---
let dispatchChart = null;

function renderDispatchChart(ts) {
  if (dispatchChart) dispatchChart.dispose();
  dispatchChart = echarts.init(document.getElementById('chart-dispatch'));

  dispatchChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e2330',
      borderColor: '#2e3446',
      textStyle: { color: '#f0f2f5', fontSize: 12 },
    },
    legend: {
      data: ['负荷', '储能', 'SOC'],
      textStyle: { color: '#b0b8c8', fontSize: 11 },
      top: 0,
    },
    grid: { left: 50, right: 50, top: 36, bottom: 24 },
    xAxis: {
      type: 'category',
      data: ts.hours.map(h => `${h}:00`),
      axisLine: { lineStyle: { color: '#2e3446' } },
      axisLabel: { color: '#7a8298', fontSize: 10, interval: 0 },
    },
    yAxis: [
      {
        type: 'value',
        name: 'kW',
        nameTextStyle: { color: '#7a8298' },
        axisLine: { lineStyle: { color: '#2e3446' } },
        axisLabel: { color: '#7a8298', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
      },
      {
        type: 'value',
        name: 'SOC',
        nameTextStyle: { color: '#7a8298' },
        min: 0,
        max: 1,
        axisLine: { lineStyle: { color: '#2e3446' } },
        axisLabel: { color: '#7a8298', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '负荷',
        type: 'line',
        data: ts.load_real,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#b0b8c8', width: 0.5 },
        areaStyle: { color: 'rgba(176,184,200,0.08)' },
      },
      {
        name: '储能',
        type: 'line',
        data: ts.load_ess,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#5ea3ff', width: 0.5 },
        areaStyle: { color: 'rgba(94,163,255,0.12)' },
      },
      {
        name: 'SOC',
        type: 'line',
        yAxisIndex: 1,
        data: ts.soc,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#34d399', width: 0.5, type: 'dashed' },
      },
    ],
  });

  // 响应式
  window.addEventListener('resize', () => dispatchChart && dispatchChart.resize());
}

// --- 多方收益图表 ---
let chartUserPrice = null, chartEssPower = null, chartPriceCurve = null;

const chartTooltip = { trigger: 'axis', backgroundColor: '#1e2330', borderColor: '#2e3446', textStyle: { color: '#f0f2f5', fontSize: 11 } };
const chartGrid = { left: 46, right: 46, top: 30, bottom: 20 };
const axisStyle = { axisLine: { lineStyle: { color: '#2e3446' } }, axisLabel: { color: '#7a8298', fontSize: 8, interval: 0 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } };

function renderWelfareCharts(ts) {
  const hours = ts.hours.map(h => `${h}`);
  // mock 数据（API 无数据时使用）
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
  if (chartUserPrice) chartUserPrice.dispose();
  chartUserPrice = echarts.init(document.getElementById('chart-user-price'));
  chartUserPrice.setOption({
    tooltip: chartTooltip,
    grid: chartGrid,
    xAxis: { type: 'category', data: hours, ...axisStyle },
    yAxis: { type: 'value', name: '元/kWh', nameTextStyle: { color: '#7a8298', fontSize: 8 }, ...axisStyle },
    series: [{
      name: '用户侧电价', type: 'line', data: (ts.price_user && ts.price_user.length ? ts.price_user : mockPriceUser),
      smooth: true, symbol: 'none',
      lineStyle: { color: '#f0c040', width: 0.5 },
      areaStyle: { color: 'rgba(240,192,64,0.10)' },
    }],
  });

  // 2. 储能功率 + SOC + 光伏功率
  if (chartEssPower) chartEssPower.dispose();
  chartEssPower = echarts.init(document.getElementById('chart-ess-power'));
  chartEssPower.setOption({
    tooltip: chartTooltip,
    legend: { data: ['储能功率', 'SOC', '光伏功率'], textStyle: { color: '#b0b8c8', fontSize: 8 }, top: 0 },
    grid: { left: 46, right: 46, top: 30, bottom: 20 },
    xAxis: { type: 'category', data: hours, ...axisStyle },
    yAxis: [
      { type: 'value', name: 'kW', nameTextStyle: { color: '#7a8298', fontSize: 8 }, ...axisStyle },
      { type: 'value', name: 'SOC %', nameTextStyle: { color: '#7a8298', fontSize: 8 }, min: 0, max: 100, axisLine: { lineStyle: { color: '#2e3446' } }, axisLabel: { color: '#7a8298', fontSize: 8 }, splitLine: { show: false } },
    ],
    series: [
      { name: '储能功率', type: 'line', data: ts.load_ess, smooth: true, symbol: 'none', lineStyle: { color: '#5ea3ff', width: 0.5 }, areaStyle: { color: 'rgba(94,163,255,0.10)' } },
      { name: 'SOC', type: 'line', yAxisIndex: 1, data: (ts.soc || []).map(v => v * 100), smooth: true, symbol: 'none', lineStyle: { color: '#34d399', width: 0.5, type: 'dashed' } },
      { name: '光伏功率', type: 'line', data: ts.pv_power || [], smooth: true, symbol: 'none', lineStyle: { color: '#fbbf24', width: 0.5 }, areaStyle: { color: 'rgba(251,191,36,0.10)' } },
    ],
  });

  // 3. 日前电价 + 实时电价
  if (chartPriceCurve) chartPriceCurve.dispose();
  chartPriceCurve = echarts.init(document.getElementById('chart-price-curve'));
  chartPriceCurve.setOption({
    tooltip: chartTooltip,
    legend: { data: ['日前电价', '实时电价'], textStyle: { color: '#b0b8c8', fontSize: 8 }, top: 0 },
    grid: chartGrid,
    xAxis: { type: 'category', data: hours, ...axisStyle },
    yAxis: { type: 'value', name: '元/kWh', nameTextStyle: { color: '#7a8298', fontSize: 8 }, ...axisStyle },
    series: [
      { name: '日前电价', type: 'line', data: (ts.price_da && ts.price_da.length ? ts.price_da : mockPriceDa), smooth: true, symbol: 'none', lineStyle: { color: '#a78bfa', width: 0.5 } },
      { name: '实时电价', type: 'line', data: (ts.price_rt && ts.price_rt.length ? ts.price_rt : mockPriceRt), smooth: true, symbol: 'none', lineStyle: { color: '#f87171', width: 0.5, type: 'dashed' } },
    ],
  });

  window.addEventListener('resize', () => {
    chartUserPrice && chartUserPrice.resize();
    chartEssPower && chartEssPower.resize();
    chartPriceCurve && chartPriceCurve.resize();
  });
}

// --- 典型日能量分析图表 ---
let chartCostComposition = null, chartEnergyComposition = null, chartPriceComposition = null;

function renderEnergyAnalysisCharts(ts) {
  const hours = ts.hours.map(h => `${h}:00`);

  // 1. 全时段成本构成（终端用户视角）- 堆积柱状图
  if (chartCostComposition) chartCostComposition.dispose();
  chartCostComposition = echarts.init(document.getElementById('chart-cost-composition'));
  chartCostComposition.setOption({
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: { data: ['网购电', '储能返还', '光伏消纳', '光伏上网'], textStyle: { color: '#b0b8c8', fontSize: 10 }, top: 0 },
    grid: { left: 60, right: 20, top: 36, bottom: 24 },
    xAxis: { type: 'category', data: hours, ...axisStyle },
    yAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#7a8298', fontSize: 10 }, ...axisStyle },
    series: [
      { name: '网购电', type: 'bar', stack: 'cost', data: ts.cost_grid || [], itemStyle: { color: '#5ea3ff' } },
      { name: '储能返还', type: 'bar', stack: 'cost', data: ts.cost_ess || [], itemStyle: { color: '#34d399' } },
      { name: '光伏消纳', type: 'bar', stack: 'cost', data: ts.cost_pv_self || [], itemStyle: { color: '#fbbf24' } },
      { name: '光伏上网', type: 'bar', stack: 'cost', data: ts.cost_pv_out || [], itemStyle: { color: '#a78bfa' }, show: false },
    ],
  });

  // 2. 全时段能量构成 - 堆积柱状图
  if (chartEnergyComposition) chartEnergyComposition.dispose();
  chartEnergyComposition = echarts.init(document.getElementById('chart-energy-composition'));
  chartEnergyComposition.setOption({
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: { data: ['电网供电', '储能充放电', '光伏发电', '用户负荷'], textStyle: { color: '#b0b8c8', fontSize: 10 }, top: 0 },
    grid: { left: 60, right: 20, top: 36, bottom: 24 },
    xAxis: { type: 'category', data: hours, ...axisStyle },
    yAxis: { type: 'value', name: 'kW', nameTextStyle: { color: '#7a8298', fontSize: 10 }, ...axisStyle },
    series: [
      { name: '电网供电', type: 'bar', stack: 'energy', data: (ts.energy_grid || []).map(v => -v), itemStyle: { color: '#5ea3ff' } },
      { name: '储能充放电', type: 'bar', stack: 'energy', data: ts.energy_ess || [], itemStyle: { color: '#34d399' } },
      { name: '光伏发电', type: 'bar', stack: 'energy', data: (ts.energy_pv || []).map(v => -v), itemStyle: { color: '#fbbf24' } },
      { name: '用户负荷', type: 'bar', stack: 'energy', data: ts.energy_load || [], itemStyle: { color: '#f87171' } },
    ],
  });

  // 3. 分时电价构成 - 条形图
  if (chartPriceComposition) chartPriceComposition.dispose();
  chartPriceComposition = echarts.init(document.getElementById('chart-price-composition'));
  chartPriceComposition.setOption({
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: { data: ['净负荷'], textStyle: { color: '#b0b8c8', fontSize: 10 }, top: 0 },
    grid: { left: 60, right: 20, top: 36, bottom: 24 },
    xAxis: { type: 'category', data: hours, ...axisStyle },
    yAxis: { type: 'value', name: 'kW', nameTextStyle: { color: '#7a8298', fontSize: 10 }, ...axisStyle },
    series: [
      { name: '净负荷', type: 'bar', data: ts.net_load || [], itemStyle: { color: '#5ea3ff' } },
    ],
  });

  window.addEventListener('resize', () => {
    chartCostComposition && chartCostComposition.resize();
    chartEnergyComposition && chartEnergyComposition.resize();
    chartPriceComposition && chartPriceComposition.resize();
  });
}

// --- App 注册 ---
App.charts = { renderDispatchChart, renderWelfareCharts, renderEnergyAnalysisCharts };

