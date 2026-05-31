// ===== params.js =====

// --- 缺省参数页面 ---
let globalParamsData = null;
let currentPanel = null;

// 占位面板模板
function placeholderHTML(title) {
  return `<div class="params-placeholder"><div style="text-align:center;color:var(--text-3)"><div style="font-size:16px;margin-bottom:8px">${title}</div><div style="font-size:var(--fs-12)">待实现</div></div></div>`;
}

// 表格面板模板
function tablePanelHTML(title, headers, rows) {
  return `<div class="params-section"><div class="params-section-hd">${title}</div><div style="overflow-x:auto"><table class="data-table"><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</table></div></div>`;
}

// 参数表单面板模板
function formPanelHTML(title, fields) {
  return `<div class="params-section"><div class="params-section-hd">${title}</div><div class="params-grid cols-3">${fields.map(f=>{
    const cb = f.checkbox ? `<span style="display:inline-flex;align-items:center;gap:4px;margin-left:6px;font-size:var(--fs-11);color:var(--text-2);cursor:pointer;white-space:nowrap"><input type="checkbox" id="${f.checkbox.id}" ${f.checkbox.checked?'checked':''} style="margin:0"> 启用</span>` : '';
    return `<div class="params-field"><div style="display:flex;align-items:center;margin-bottom:4px"><span style="font-size:var(--fs-11);color:var(--text-3);font-weight:var(--fw-medium)">${f.label}</span>${cb}</div><input type="number" id="${f.id}" step="${f.step||1}" value="${f.value||''}"></div>`;
  }).join('')}</div></div>`;
}

// 渲染各面板内容
async function renderPanelContent(panelId) {
  console.log('[params] renderPanelContent called for:', panelId, 'globalParamsData:', globalParamsData);
  const d = globalParamsData;
  const panel = document.getElementById('panel-' + panelId);
  if (!d) {
    panel.innerHTML = '<div class="params-placeholder"><div style="color:var(--danger);font-size:var(--fs-14)">参数数据未加载，请刷新页面重试</div></div>';
    return;
  }

  switch(panelId) {
    case 'ess':
      panel.innerHTML = formPanelHTML('储能系统参数', [
        {label:'额定容量 (MWh)', id:'gp-cap-rated', step:0.1, value:(d.ess.cap_rated/1000).toFixed(2)},
        {label:'额定功率 (MW)', id:'gp-power-rated', step:0.1, value:d.ess.power_rated||0.5},
        {label:'往返效率 RTE (%)', id:'gp-eta', step:1, value:((d.ess.eta_roundtrip||0.87)*100).toFixed(0)},
        {label:'单程充电效率 η (%)', id:'gp-eta-charge', step:1, value:((d.ess.eta_charge||0.92)*100).toFixed(0)},
        {label:'SOC 下限 (%)', id:'gp-soc-min', step:1, value:((d.ess.soc_min||0.1)*100).toFixed(0)},
        {label:'SOC 上限 (%)', id:'gp-soc-max', step:1, value:((d.ess.soc_max||0.9)*100).toFixed(0)},
        {label:'设计寿命 (年)', id:'gp-design-life', step:1, value:d.ess.design_life||10},
        {label:'储能容量年衰减比例 (%)', id:'gp-r-degrade', step:0.5, value:((d.ess.r_degrade||0.025)*100).toFixed(1), checkbox:{id:'gp-degrade-enabled', checked:d.ess.degrade_enabled}},
        {label:'储能循环次数 (100% DoD)', id:'gp-cycle-life', step:100, value:d.ess.cycle_life||5000, checkbox:{id:'gp-cycle-enabled', checked:d.ess.cycle_enabled}},
      ]) + formPanelHTML('财务参数', [
        {label:'建设单价 (元/Wh)', id:'gp-unit-cost', step:0.1, value:d.ess.unit_cost||0.9},
        {label:'年运维支出比例 (%)', id:'gp-r-om', step:0.1, value:((d.ess.r_om||0.01)*100).toFixed(1)},
        {label:'折现率 (%)', id:'gp-r-discount', step:0.5, value:((d.financial.r_discount||0.06)*100).toFixed(1)},
        {label:'用户侧峰谷套利收益分享比例 (%)', id:'gp-r-user-b1', step:1, value:((d.financial.r_user_b1||0.3)*100).toFixed(0)},
        {label:'售电公司额外收益分享比例 (%)', id:'gp-r-user-b2', step:1, value:((d.financial.r_user_b2||0.5)*100).toFixed(0)},
      ]);
      appendEssNotes(panel);
      break;
    case 'pv':
      try {
        const pv = await api('/params/pv');
        const p = pv.params;
        const regions = Object.keys(pv.curves);
        const regionLabels = {jiangsu:'江苏',shandong:'山东',guangdong:'广东'};
        const curveLabels = {annual_avg:'年均',cloudy:'典型阴雨天',sunny:'典型晴天'};
        const curRegion = p.region || 'jiangsu';
        const curCurve = p.curve_type || 'annual_avg';
        const regionOpts = regions.map(r=>`<option value="${r}" ${r===curRegion?'selected':''}>${regionLabels[r]||r}</option>`).join('');
        const curveOpts = (pv.curves[curRegion]||[]).map(c=>`<option value="${c}" ${c===curCurve?'selected':''}>${curveLabels[c]||c}</option>`).join('');
        panel.innerHTML = formPanelHTML('光伏基本参数', [
          {label:'额定装机容量 (kWp)', id:'pv-cap-rated', step:0.1, value:p.cap_rated||1.0},
        ]) + formPanelHTML('光伏经济参数', [
          {label:'单位造价 (元/Wp)', id:'pv-unit-cost', step:0.1, value:p.unit_cost||3.5},
          {label:'年运维费用比例 (%)', id:'pv-r-om', step:0.1, value:((p.r_om||0.015)*100).toFixed(1)},
          {label:'设计寿命 (年)', id:'pv-design-life', step:1, value:p.design_life||25},
          {label:'年衰减率 (%)', id:'pv-r-degrade', step:0.1, value:((p.r_degrade||0.005)*100).toFixed(1)},
        ]) + `<div class="params-section" style="margin-top:16px"><div class="params-section-hd">出力特性</div><div class="params-grid cols-2" style="margin-bottom:12px"><div class="params-field"><label>地区</label><select id="pv-region" onchange="onPvCurveChange()">${regionOpts}</select></div><div class="params-field"><label>曲线类型</label><select id="pv-curve-type" onchange="onPvCurveChange()">${curveOpts}</select></div></div><div id="pv-curve-chart" style="height:260px"></div></div>`;
        renderPvCurveChart(pv.curve_data, curRegion, curCurve);
      } catch(e) {
        panel.innerHTML = placeholderHTML('光伏参数 — 加载失败');
      }
      break;
    case 'contract':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">中长期量价曲线</div>
        <div style="display:flex;gap:24px;margin-bottom:16px">
          <div style="flex:1">
            <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px">
              <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:var(--fs-12);color:var(--text-2)">
                <input type="radio" name="contract-mode" value="absolute" checked onchange="onContractModeChange()"> 合约电量 (MWh)
              </label>
              <input type="number" id="contract-mwh" value="80" step="1" style="width:100px;background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)">
              <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:var(--fs-12);color:var(--text-2)">
                <input type="radio" name="contract-mode" value="ratio" onchange="onContractModeChange()"> 覆盖比例 (%)
              </label>
              <input type="number" id="contract-ratio" value="50" step="1" disabled style="width:100px;background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-3);font-size:var(--fs-12)">
            </div>
            <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">
              <span style="font-size:var(--fs-12);color:var(--text-3)">合约单价 (元/MWh)</span>
              <input type="number" id="contract-price" value="372" step="1" style="width:100px;background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)">
            </div>
            <div style="display:flex;align-items:center;gap:16px">
              <span style="font-size:var(--fs-12);color:var(--text-3)">分解曲线</span>
              <select id="contract-curve-type" onchange="onContractCurveChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)">
                <option value="load">按统调负荷分解</option>
                <option value="D1" selected>D1：峰平谷</option>
                <option value="D2">D2：平均</option>
                <option value="D3">D3：高峰（含尖峰）</option>
                <option value="D4">D4：平段</option>
                <option value="D5">D5：谷段（含深谷）</option>
              </select>
            </div>
          </div>
        </div>
        <div id="contract-chart" style="height:280px;margin-bottom:16px"></div>
        <div style="font-size:var(--fs-11);color:var(--text-3);line-height:1.8;white-space:pre-line">说明：
国内各省中长期规则差异较大，D1~D5 曲线为综合国内多省情况设置，不特定指代某个省的实际情况。
统调负荷分解曲线由后台数据提供，反映系统实际负荷分布。</div>
      </div>`;
      onContractCurveChange();
      break;
    case 'dayahead':
      try {
        const da = await api('/params/dayahead-position');
        panel.innerHTML = tablePanelHTML('日前节点电价',
          ['时段','申报电量 (kWh)','出清电量 (kWh)'],
          da.map(r=>[r.hour+':00', r.q_dayahead_kwh, r.q_dayahead_cleared_kwh])
        );
      } catch(e) { panel.innerHTML = placeholderHTML('日前节点电价 — 加载失败'); }
      break;
    case 'realtime':
      panel.innerHTML = '<div class="params-section"><div class="params-section-hd">实时节点电价</div><div id="rt-price-chart" style="height:300px"></div></div>';
      renderRealtimeChart();
      break;
    case 'pricing-mode':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">电价模式选择</div><div style="font-size:var(--fs-12);color:var(--text-2);line-height:1.8">
        <b style="color:var(--text-1)">M1 行政分时</b> — 政府核定的峰谷平电价，固定时段划分<br>
        <b style="color:var(--text-1)">M2 江苏模式</b> — 基础电价 × 时段系数（峰/平/谷）<br>
        <b style="color:var(--text-1)">M3 合同分时</b> — 售电公司与用户签订的合同电价<br>
        <b style="color:var(--text-1)">M4 现货联动</b> — 电价与电力市场日前价格联动<br>
        <b style="color:var(--text-1)">M5 一口价</b> — 固定单价，不区分时段
      </div></div>`;
      break;
    case 'tariff-admin':
      panel.innerHTML = tablePanelHTML('行政分时电价',
        ['时段','起始','结束','电价 (元/kWh)'],
        d.tariff_admin.map(r=>[r.period, r.start+':00', r.end+':00', r.price])
      );
      break;
    case 'tariff-contract':
      panel.innerHTML = tablePanelHTML('合同分时电价',
        ['时段','起始','结束','电价 (元/kWh)'],
        d.tariff_contract.map(r=>[r.period, r.start+':00', r.end+':00', r.price])
      );
      break;
    case 'tariff-flat':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">固定价格</div><div class="params-grid cols-3"><div class="params-field"><label>一口价 (元/kWh)</label><input type="number" id="gp-flat-price" step="0.01" value="${d.flat_price||0.55}"></div></div></div>`;
      break;
    case 'tariff-spot':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">电力市场联动价格</div><div style="font-size:var(--fs-12);color:var(--text-2);line-height:1.8">M4 模式下，用户侧电价 = 当月日前电价 24h 均值曲线。<br>数据来源：<code>price_henan.csv</code> 中 <code>day_ahead</code> 列按月聚合。</div><div id="spot-price-chart" style="height:300px;margin-top:12px"></div></div>`;
      renderSpotPriceChart();
      break;
    case 'load-curve':
      panel.innerHTML = '<div class="params-section"><div class="params-section-hd">用户净负荷曲线</div><div id="load-curve-chart" style="height:300px"></div></div>';
      renderLoadCurveChart();
      break;
    case 'pv-curve':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">光伏发电功率曲线</div><div style="font-size:var(--fs-12);color:var(--text-2);line-height:1.8">
        光伏发电功率曲线用于计算光伏出力随时间的变化，典型形状为倒抛物线（白天高、夜间为零）。<br><br>
        <b style="color:var(--text-1)">数据需求</b><br>
        · 逐时辐照度数据（kW/m²）<br>
        · 组件效率曲线<br>
        · 温度修正系数<br><br>
        <b style="color:var(--text-1)">典型日发电曲线特征</b><br>
        · 0:00~6:00 — 出力为零（夜间）<br>
        · 6:00~10:00 — 逐渐上升（日出）<br>
        · 10:00~14:00 — 峰值区间（正午）<br>
        · 14:00~18:00 — 逐渐下降（日落）<br>
        · 18:00~24:00 — 出力为零（夜间）<br><br>
        <div style="color:var(--text-3);font-size:var(--fs-11);margin-top:8px">状态：待实现 — 需要辐照度数据源</div>
      </div></div>`;
      break;
    case 'wholesale':
      panel.innerHTML = formPanelHTML('批发侧结算配置', [
        {label:'月度外生费用 (元)', id:'gp-pm-const', step:100, value:d.wholesale.purchase_monthly_constant_yuan||0},
        {label:'广西月度调平 (元)', id:'gp-gx-smooth', step:50, value:d.wholesale.guangxi_month_smooth_yuan||0},
        {label:'山西批发附加 (元)', id:'gp-sx-addon', step:50, value:d.wholesale.shanxi_wholesale_addon_yuan||0},
      ]) + `<div class="params-section" style="margin-top:16px"><div class="params-section-hd">结算模式配置</div><div class="params-grid cols-2"><div class="params-field"><label>市场区域</label><input type="text" value="${d.wholesale.market_region_code}" disabled></div><div class="params-field"><label>结算模式</label><input type="text" value="${d.wholesale.settlement_mode}" disabled></div><div class="params-field"><label>时间粒度</label><input type="text" value="${d.wholesale.time_granularity}" disabled></div><div class="params-field"><label>合约曲线</label><input type="text" value="${d.wholesale.contract_curve_profile}" disabled></div></div></div>`;
      break;
    case 'pv-biz':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">光伏商业模式</div><div style="font-size:var(--fs-12);color:var(--text-2);line-height:1.8">
        光伏商业模式定义光伏资产的归属、收益分配和并网方式。<br><br>
        <b style="color:var(--text-1)">资产归属模式</b><br>
        · <b>自建自用</b> — 用户投资建设，自发自用余电上网<br>
        · <b>EMC 合同能源管理</b> — 第三方投资，用户按折扣电价购电<br>
        · <b>屋顶租赁</b> — 租用用户屋顶，光伏运营商独立运营<br><br>
        <b style="color:var(--text-1)">收益分配</b><br>
        · 自用节省电费（按用户侧电价计算）<br>
        · 余电上网收益（按上网电价计算）<br>
        · 需量电费节约（降低最大需量）<br><br>
        <b style="color:var(--text-1)">与储能的协同</b><br>
        · 光储联合调度：光伏余量优先充储<br>
        · 储能削峰填谷配合光伏出力波动<br><br>
        <div style="color:var(--text-3);font-size:var(--fs-11);margin-top:8px">状态：待实现 — 需要光伏模块和电价模型完善</div>
      </div></div>`;
      break;
    case 'ess-biz':
      panel.innerHTML = formPanelHTML('储能商业模式', [
        {label:'折现率 (%)', id:'gp-r-discount', step:0.5, value:((d.financial.r_discount||0.06)*100).toFixed(1)},
        {label:'用户侧峰谷套利收益分享比例 (%)', id:'gp-r-user-b1', step:1, value:((d.financial.r_user_b1||0.3)*100).toFixed(0)},
        {label:'售电公司额外收益分享比例 (%)', id:'gp-r-user-b2', step:1, value:((d.financial.r_user_b2||0.5)*100).toFixed(0)},
        {label:'建设单价 (元/Wh)', id:'gp-unit-cost', step:0.1, value:d.ess.unit_cost||0.9},
        {label:'年运维支出比例 (%)', id:'gp-r-om', step:0.1, value:((d.ess.r_om||0.01)*100).toFixed(1)},
      ]);
      break;
    case 'biz-note':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">其他模式说明</div><div style="font-size:var(--fs-12);color:var(--text-2);line-height:1.8">
        <b style="color:var(--text-1)">B1 用户+储能</b> — 用户拥有储能，直接获取套利收益<br>
        <b style="color:var(--text-1)">B2a 售电公司最优</b> — 售电公司控制储能调度，最大化自身利润<br>
        <b style="color:var(--text-1)">B2b 储能运营商最优</b> — 储能运营商独立运营，最大化储能收益<br>
        <b style="color:var(--text-1)">B2c 用户最优</b> — 以用户侧成本最小化为目标<br>
        <b style="color:var(--text-1)">B3a 储售一体最优</b> — 售电公司同时运营储能，联合优化<br>
        <b style="color:var(--text-1)">B3b 用户最优(储售一体)</b> — 储售一体模式下以用户利益为主<br>
        <b style="color:var(--text-1)">B4 总社会福利最高</b> — 最大化用户+售电+储能三方总收益
      </div></div>`;
      break;
  }
  bindDirtyTracking();
}

// 实时电价图表
function renderRealtimeChart() {
  const el = document.getElementById('rt-price-chart');
  if (!el) return;
  const chart = echarts.init(el);
  chart.setOption({
    tooltip:{trigger:'axis',backgroundColor:'#1e2330',borderColor:'#2e3446',textStyle:{color:'#f0f2f5',fontSize:11}},
    legend:{data:['日前电价','实时电价'],textStyle:{color:'#b0b8c8',fontSize:8},top:0},
    grid:{left:46,right:46,top:30,bottom:20},
    xAxis:{type:'category',data:Array.from({length:24},(_,i)=>`${i}`),axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:8,interval:0}},
    yAxis:{type:'value',name:'元/kWh',nameTextStyle:{color:'#7a8298',fontSize:8},axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:8},splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}}},
    series:[
      {name:'日前电价',type:'line',data:Array.from({length:24},(_,i)=>+(0.35+Math.sin((i-5)*Math.PI/13)*0.25).toFixed(4)),smooth:true,symbol:'none',lineStyle:{color:'#a78bfa',width:0.5}},
      {name:'实时电价',type:'line',data:Array.from({length:24},(_,i)=>+(0.33+Math.sin((i-5)*Math.PI/13)*0.25+Math.sin(i*1.5)*0.05).toFixed(4)),smooth:true,symbol:'none',lineStyle:{color:'#f87171',width:0.5,type:'dashed'}},
    ],
  });
  window.addEventListener('resize',()=>chart.resize());
}

// 现货价格图表
function renderSpotPriceChart() {
  const el = document.getElementById('spot-price-chart');
  if (!el) return;
  const chart = echarts.init(el);
  const mockDa = Array.from({length:24},(_,i)=>+(0.35+Math.sin((i-5)*Math.PI/13)*0.25).toFixed(4));
  chart.setOption({
    tooltip:{trigger:'axis',backgroundColor:'#1e2330',borderColor:'#2e3446',textStyle:{color:'#f0f2f5',fontSize:11}},
    grid:{left:46,right:46,top:20,bottom:20},
    xAxis:{type:'category',data:Array.from({length:24},(_,i)=>`${i}`),axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:8,interval:0}},
    yAxis:{type:'value',name:'元/kWh',nameTextStyle:{color:'#7a8298',fontSize:8},axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:8},splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}}},
    series:[{name:'日前均价',type:'line',data:mockDa,smooth:true,symbol:'none',lineStyle:{color:'#a78bfa',width:0.5},areaStyle:{color:'rgba(167,139,250,0.10)'}}],
  });
  window.addEventListener('resize',()=>chart.resize());
}

// 负荷曲线图表
function renderLoadCurveChart() {
  const el = document.getElementById('load-curve-chart');
  if (!el) return;
  const chart = echarts.init(el);
  const mockLoad = [120,110,105,100,105,130,200,350,420,450,460,440,420,400,380,360,380,420,480,500,460,380,280,180];
  chart.setOption({
    tooltip:{trigger:'axis',backgroundColor:'#1e2330',borderColor:'#2e3446',textStyle:{color:'#f0f2f5',fontSize:11}},
    grid:{left:46,right:46,top:20,bottom:20},
    xAxis:{type:'category',data:Array.from({length:24},(_,i)=>`${i}`),axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:8,interval:0}},
    yAxis:{type:'value',name:'kW',nameTextStyle:{color:'#7a8298',fontSize:8},axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:8},splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}}},
    series:[{name:'净负荷',type:'line',data:mockLoad,smooth:true,symbol:'none',lineStyle:{color:'#5ea3ff',width:0.5},areaStyle:{color:'rgba(94,163,255,0.10)'}}],
  });
  window.addEventListener('resize',()=>chart.resize());
}

// 光伏出力曲线图表
let pvCurveChart = null;
function renderPvCurveChart(data, region, curveType) {
  const el = document.getElementById('pv-curve-chart');
  if (!el) return;
  if (pvCurveChart) pvCurveChart.dispose();
  pvCurveChart = echarts.init(el);
  const regionLabels = {jiangsu:'江苏',shandong:'山东',guangdong:'广东'};
  const curveLabels = {annual_avg:'年均',cloudy:'典型阴雨天',sunny:'典型晴天'};
  pvCurveChart.setOption({
    tooltip:{trigger:'axis',backgroundColor:'#1e2330',borderColor:'#2e3446',textStyle:{color:'#f0f2f5',fontSize:11}},
    grid:{left:46,right:46,top:30,bottom:20},
    xAxis:{type:'category',data:Array.from({length:24},(_,i)=>`${i}`),axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:8,interval:0}},
    yAxis:{type:'value',name:'归一化出力',nameTextStyle:{color:'#7a8298',fontSize:8},min:0,max:1,axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:8},splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}}},
    series:[{name:(regionLabels[region]||region)+' '+(curveLabels[curveType]||curveType),type:'line',data:data,smooth:true,symbol:'none',lineStyle:{color:'#fbbf24',width:1},areaStyle:{color:'rgba(251,191,36,0.12)'}}],
  });
  window.addEventListener('resize',()=>pvCurveChart&&pvCurveChart.resize());
}

async function onPvCurveChange() {
  const region = document.getElementById('pv-region').value;
  const curveType = document.getElementById('pv-curve-type').value;
  // 更新二级下拉选项
  const curves = await api('/params/pv');
  const curveLabels = {annual_avg:'年均',cloudy:'典型阴雨天',sunny:'典型晴天'};
  const sel = document.getElementById('pv-curve-type');
  const opts = (curves.curves[region]||[]).map(c=>`<option value="${c}" ${c===curveType?'selected':''}>${curveLabels[c]||c}</option>`).join('');
  sel.innerHTML = opts;
  // 加载曲线数据
  const res = await api(`/params/pv-curve/${region}/${sel.value}`);
  renderPvCurveChart(res.data, region, sel.value);
}

// 中长期合约曲线
let contractChart = null;

function onContractModeChange() {
  const mode = document.querySelector('input[name="contract-mode"]:checked').value;
  document.getElementById('contract-mwh').disabled = (mode === 'ratio');
  document.getElementById('contract-mwh').style.color = (mode === 'ratio') ? 'var(--text-3)' : 'var(--text-1)';
  document.getElementById('contract-ratio').disabled = (mode === 'absolute');
  document.getElementById('contract-ratio').style.color = (mode === 'absolute') ? 'var(--text-3)' : 'var(--text-1)';
  onContractCurveChange();
}

async function onContractCurveChange() {
  const mode = document.querySelector('input[name="contract-mode"]:checked').value;
  const curveType = document.getElementById('contract-curve-type').value;
  let totalMwh;
  if (mode === 'absolute') {
    totalMwh = parseFloat(document.getElementById('contract-mwh').value) || 80;
  } else {
    const ratio = parseFloat(document.getElementById('contract-ratio').value) || 50;
    // 从 state.result 获取用户总用电量
    const loadMwh = state.result?.overview?.prod_load_mwh || 160;
    totalMwh = loadMwh * ratio / 100;
  }

  try {
    const res = await api(`/params/contract-curve?total_mwh=${totalMwh}&curve_type=${curveType}`);
    renderContractChart(res);
  } catch(e) {
    console.error('Contract curve error:', e);
  }
}

function renderContractChart(res) {
  const el = document.getElementById('contract-chart');
  if (!el) return;
  if (contractChart) contractChart.dispose();
  contractChart = echarts.init(el);
  const hours = Array.from({length:24}, (_,i) => `${i}`);
  const curveLabels = {load:'按统调负荷分解',D1:'D1 峰平谷',D2:'D2 平均',D3:'D3 高峰',D4:'D4 平段',D5:'D5 谷段'};

  // 颜色：按电价分色
  const colors = res.tou_prices.map(p => {
    if (p >= 0.9) return '#f87171'; // 峰-红
    if (p >= 0.5) return '#fbbf24'; // 平-黄
    return '#5ea3ff';               // 谷-蓝
  });

  contractChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e2330',
      borderColor: '#2e3446',
      textStyle: { color: '#f0f2f5', fontSize: 11 },
      formatter: function(params) {
        const p = params[0];
        const price = res.tou_prices[p.dataIndex];
        return `${p.name}<br/>合约电量: ${p.value.toFixed(2)} MWh<br/>分时电价: ${price} 元/kWh`;
      }
    },
    grid: { left: 50, right: 30, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: hours,
      axisLine: { lineStyle: { color: '#2e3446' } },
      axisLabel: { color: '#7a8298', fontSize: 8, interval: 0 },
    },
    yAxis: {
      type: 'value',
      name: 'MWh',
      nameTextStyle: { color: '#7a8298', fontSize: 8 },
      axisLine: { lineStyle: { color: '#2e3446' } },
      axisLabel: { color: '#7a8298', fontSize: 8 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
    },
    series: [{
      name: curveLabels[res.curve_type] || res.curve_type,
      type: 'bar',
      data: res.hourly_mwh.map((v, i) => ({
        value: v,
        itemStyle: { color: colors[i], opacity: v > 0 ? 0.85 : 0.15 }
      })),
      barWidth: '60%',
    }],
  });
  window.addEventListener('resize', () => contractChart && contractChart.resize());
}

// 储能指标说明
function appendEssNotes(panel) {
  const note = document.createElement('div');
  note.className = 'params-section';
  note.style.marginTop = '16px';
  note.innerHTML = `<div style="font-size:var(--fs-11);color:var(--text-3);line-height:1.8;white-space:pre-line">指标说明：
1、RTE = η_charge × η_discharge，因此不再单独列出单程放电效率，该指标为考虑公辅的工程实测指标，与厂商宣称的只考虑线损的单程指标有所区别，η指标仅在虚拟电厂等需要计算单边收益的场景中生效
2、启用储能循环（默认不启用）次数约束后，储能计算将按照实际充放电次数折算实际寿命，部分工况激进的场景储能无法支撑10年的稳定运行。
3、为简化计算，建设单价按照大EPC均价计算，无额外其他建设成本
4、本仿真系统暂不考虑融资相关的财务指标</div>`;
  panel.appendChild(note);
}

// 折叠/展开 section
function toggleSection(hd) {
  hd.classList.toggle('collapsed');
  const body = hd.nextElementSibling;
  body.style.display = body.style.display === 'none' ? '' : 'none';
}

// 电价表 tab 切换
function switchTariffTab(mode) {
  document.querySelectorAll('.params-tariff-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('[id^="tariff-content-"]').forEach(d => d.style.display = 'none');
  event.target.classList.add('active');
  document.getElementById('tariff-content-' + mode).style.display = '';
}

// 菜单切换（由 HTML onclick 调用）
async function selectPanel(panelId) {
  console.log('[params] selectPanel:', panelId);
  if (!globalParamsData) { await loadGlobalParams(); }
  document.querySelectorAll('.params-menu-item').forEach(i => i.classList.remove('active'));
  const item = document.querySelector(`.params-menu-item[data-panel="${panelId}"]`);
  if (item) item.classList.add('active');
  document.querySelectorAll('.params-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('params-default-hint').style.display = 'none';
  const panel = document.getElementById('panel-' + panelId);
  panel.classList.add('active');
  currentPanel = panelId;
  await renderPanelContent(panelId);
}

function initParamsMenu() {
  // 兼容旧调用，不再需要
}

// 加载数据
async function loadGlobalParams() {
  console.log('[params] loadGlobalParams called');
  try {
    const data = await api('/global-params');
    console.log('[params] API response:', data);
    globalParamsData = data;
    paramsDirty = false;
    console.log('[params] globalParamsData set, keys:', Object.keys(data));
  } catch (e) {
    console.error('[params] Failed to load global params:', e);
    alert('加载全局参数失败: ' + e.message);
  }
}

// --- App 注册 ---
App.params = {
  loadGlobalParams, initParamsMenu, renderPanelContent, selectPanel,
  toggleSection, switchTariffTab, onPvCurveChange,
  renderPvCurveChart, appendEssNotes, markParamsDirty, bindDirtyTracking,
  onContractModeChange, onContractCurveChange, renderContractChart,
  get currentPanel() { return currentPanel; },
  set currentPanel(v) { currentPanel = v; }
};

