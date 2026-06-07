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
      const _rteTip = 'RTE为一次完整循环的综合效率，已经考虑到公辅系统的耗电';
      panel.innerHTML = formPanelHTML('储能缺省参数', [
        {label:'额定容量 (MWh)', id:'gp-cap-rated', step:0.1, value:(d.ess.cap_rated/1000).toFixed(2)},
        {label:'额定功率 (MW)', id:'gp-power-rated', step:0.1, value:d.ess.power_rated||0.5},
        {label:`往返效率 RTE (%) <span class="param-tip" data-tip="${_rteTip}">?</span>`, id:'gp-eta', step:1, value:((d.ess.eta_roundtrip||0.87)*100).toFixed(0)},
        {label:'单程充电效率 η (%)', id:'gp-eta-charge', step:1, value:((d.ess.eta_charge||0.92)*100).toFixed(0)},
        {label:'SOC 下限 (%)', id:'gp-soc-min', step:1, value:((d.ess.soc_min||0.1)*100).toFixed(0)},
        {label:'SOC 上限 (%)', id:'gp-soc-max', step:1, value:((d.ess.soc_max||0.9)*100).toFixed(0)},
        {label:'设计寿命 (年)', id:'gp-design-life', step:1, value:d.ess.design_life||10},
        {label:'储能容量年衰减比例 (%)', id:'gp-r-degrade', step:0.5, value:((d.ess.r_degrade||0.025)*100).toFixed(1), checkbox:{id:'gp-degrade-enabled', checked:d.ess.degrade_enabled}},
        {label:'储能循环次数 (100% DoD)', id:'gp-cycle-life', step:100, value:d.ess.cycle_life||5000, checkbox:{id:'gp-cycle-enabled', checked:d.ess.cycle_enabled}},
        {label:'储能收益分成比例 (%)', id:'gp-r-ess-share', step:1, value:((d.ess.r_ess_share||0.20)*100).toFixed(0)},
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
        const regions = pv.curves;  // 现在是 {region: [curve_types]} 格式
        const regionNames = Object.keys(regions);
        const regionLabels = {henan:'河南',jiangsu:'江苏',shandong:'山东',guangdong:'广东'};
        const curveLabels = {annual_avg:'全年日均',cloudy:'阴天',sunny:'晴天'};
        const curRegion = p.region || (regionNames[0] || 'henan');
        const curCurve = p.curve_type || 'annual_avg';
        const regionOpts = regionNames.map(r=>`<option value="${r}" ${r===curRegion?'selected':''}>${regionLabels[r]||r}</option>`).join('');
        const curveList = regions[curRegion] || [];
        const curveOpts = curveList.map(c=>`<option value="${c}" ${c===curCurve?'selected':''}>${curveLabels[c]||c}</option>`).join('');

        const _tipSelfUse = '用户实际用电费用为约定的电价×本地消纳电费折扣，约定的电价通常为用户实际在电网/售电公司购电的电价';
        const _modeOpts = '<option value="admin">行政分时</option><option value="contract">合同分时</option><option value="flat">固定电价</option><option value="spot_da">日前现货联动</option><option value="spot_rt">实时现货联动</option><option value="lt_contract">中长期联动</option>';

        panel.innerHTML = formPanelHTML('光伏缺省参数', [
          {label:'额定装机容量 (kWp)', id:'pv-cap-rated', step:0.1, value:p.cap_rated||1.0},
          {label:'光伏上网电价 (元/kWh)', id:'pv-feed-in-tariff', step:0.01, value:p.feed_in_tariff||0.4},
        ]) + `<div class="params-section"><div class="params-section-hd">光伏经济参数</div>
          <div class="params-grid cols-3">
            <div class="params-field"><label>本地消纳电费折扣（%）<span class="param-tip" data-tip="${_tipSelfUse}">?</span></label><input type="number" id="pv-self-use-discount" step="1" value="${((p.self_use_discount||0.80)*100).toFixed(0)}"></div>
            <div class="params-field"><label>电费模式</label><select id="pv-tariff-mode" onchange="onPvTariffModeChange()">${_modeOpts}</select></div>
            <div class="params-field"><label>电价曲线</label><select id="pv-tariff-curve"></select></div>
          </div>
          <div class="params-grid cols-3" style="margin-top:8px">
            <div class="params-field"><label>单位造价 (元/Wp)</label><input type="number" id="pv-unit-cost" step="0.1" value="${p.unit_cost||3.5}"></div>
            <div class="params-field"><label>年运维费用比例 (%)</label><input type="number" id="pv-r-om" step="0.1" value="${((p.r_om||0.015)*100).toFixed(1)}"></div>
            <div class="params-field"><label>设计寿命 (年)</label><input type="number" id="pv-design-life" step="1" value="${p.design_life||25}"></div>
          </div>
          <div class="params-grid cols-2" style="margin-top:8px">
            <div class="params-field"><label>首年衰减率 (%)</label><input type="number" id="pv-r-degrade-first" step="0.1" value="${((p.r_degrade_first||0.02)*100).toFixed(1)}"></div>
            <div class="params-field"><label>年衰减率 (%)</label><input type="number" id="pv-r-degrade" step="0.1" value="${((p.r_degrade||0.005)*100).toFixed(1)}"></div>
          </div>
        </div>` + `<div class="params-section" style="margin-top:16px"><div class="params-section-hd">出力特性</div><div style="display:flex;align-items:center;gap:16px;margin-bottom:12px"><div class="params-field" style="flex:1"><label>地区</label><select id="pv-region" onchange="onPvCurveChange()">${regionOpts}</select></div><div class="params-field" style="flex:1"><label>曲线类型</label><select id="pv-curve-type" onchange="onPvCurveChange()">${curveOpts}</select></div><div style="flex:1;display:flex;align-items:flex-end;gap:6px;padding-bottom:2px"><span style="font-size:var(--fs-11);color:var(--text-3)">等效利用小时数</span><span id="pv-util-hours" style="font-size:var(--fs-13);color:var(--accent);font-weight:var(--fw-semi)">--</span><span style="font-size:var(--fs-11);color:var(--text-3)">h</span></div></div><div id="pv-curve-chart" style="height:260px"></div></div>
        <div style="font-size:var(--fs-11);color:var(--text-3);margin-top:8px;padding:0 20px">本模型暂未考虑光伏环境权益收益</div>`;
        renderPvCurveChart(pv.curve_data, curRegion, curCurve);
        onPvTariffModeChange();
      } catch(e) {
        panel.innerHTML = placeholderHTML('光伏缺省参数 — 加载失败');
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
            <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
              <span style="font-size:var(--fs-12);color:var(--text-3)">分解曲线</span>
              <select id="contract-curve-type" onchange="onContractCurveChange();onContractCurveTypeChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)">
                <option value="load">按统调负荷分解</option>
                <option value="D1" selected>D1：峰平谷</option>
                <option value="D2">D2：平均</option>
                <option value="D3">D3：高峰（含尖峰）</option>
                <option value="D4">D4：平段</option>
                <option value="D5">D5：谷段（含深谷）</option>
              </select>
              <span style="font-size:var(--fs-12);color:var(--text-3)">标的分时电价</span>
              <select id="contract-target-tariff" onchange="onContractCurveChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)">
                <option value="typical" selected>典型峰谷平</option>
                <option value="midday_valley">午间深谷</option>
                <option value="summer_peak">夏季尖峰</option>
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
      onContractCurveTypeChange();
      break;
    case 'spot-price':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">现货电价</div>
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
          <span style="font-size:var(--fs-12);color:var(--text-3)">现货电价组合</span>
          <select id="spot-price-set" onchange="onSpotPriceSetChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)">
            <option value="henan_mar" selected>河南3月电价</option>
          </select>
        </div>
        <div style="display:flex;gap:16px;margin-bottom:16px">
          <div style="flex:1"><div id="spot-da-chart" style="height:240px"></div></div>
          <div style="flex:1"><div id="spot-rt-chart" style="height:240px"></div></div>
        </div>
        <div id="spot-spread-chart" style="height:240px"></div>
      </div>`;
      renderSpotPriceCharts();
      break;
    case 'pricing-mode':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">模式说明</div><div style="font-size:var(--fs-12);color:var(--text-2);line-height:1.8">
        <b style="color:var(--text-1)">M1 行政分时</b> — 政府核定的峰谷平电价，固定时段划分<br>
        <b style="color:var(--text-1)">M2 江苏模式</b> — 基础电价 × 时段系数（峰/平/谷）<br>
        <b style="color:var(--text-1)">M3 合同分时</b> — 售电公司与用户签订的合同电价<br>
        <b style="color:var(--text-1)">M4 现货联动</b> — 电价与电力市场日前价格联动<br>
        <b style="color:var(--text-1)">M5 一口价</b> — 固定单价，不区分时段
      </div></div>`;
      break;
    case 'tariff-tou':
      panel.innerHTML = `<div class="params-section">
        <div class="params-section-hd">分时电价</div>
        <div style="display:flex;gap:0;margin-bottom:16px;border-bottom:1px solid var(--border)">
          <div class="params-tariff-tab active" data-tariff-tab="admin" onclick="App.params.switchTariffTouTab(this,'admin')">行政分时电价</div>
          <div class="params-tariff-tab" data-tariff-tab="contract" onclick="App.params.switchTariffTouTab(this,'contract')">合同分时电价</div>
          <div class="params-tariff-tab" data-tariff-tab="flat" onclick="App.params.switchTariffTouTab(this,'flat')">固定电价</div>
        </div>
        <div id="tariff-tou-content-admin"></div>
        <div id="tariff-tou-content-contract" style="display:none"></div>
        <div id="tariff-tou-content-flat" style="display:none"></div>
      </div>`;
      renderTariffTouTab('admin');
      break;
    case 'tariff-spot':
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">电力市场联动价格</div><div style="font-size:var(--fs-12);color:var(--text-2);line-height:1.8">M4 模式下，用户侧电价 = 当月日前电价 24h 均值曲线。<br>数据来源：<code>price_henan.csv</code> 中 <code>day_ahead</code> 列按月聚合。</div><div id="spot-price-chart" style="height:300px;margin-top:12px"></div></div>`;
      renderSpotPriceChart();
      break;
    case 'load-curve':
      const _randTip = '选择随机度后，每次仿真都会生成带随机干扰的曲线，目的是增加仿真结果的多样性，建议默认选择不随机。\n\n加性高斯白噪声：给每个数据点增加独立微小随机波动，不改变曲线整体形状，噪声强度推荐 2%~6%\n一阶自相关噪声：生成平滑连续的时序随机波动，相邻点变化自然无跳变，噪声强度推荐 1%~5%、自相关系数 0.7~0.95\n乘性相对噪声：根据曲线数值大小自动调整波动幅度，数值大则波动大，相对扰动系数推荐 0.01~0.05\n低频形状微调：在保留整体趋势与拐点的前提下小幅柔和改变曲线轮廓，频率推荐 2~5、幅度推荐 2%~5%';
      panel.innerHTML = `<div class="params-section"><div class="params-section-hd">用户净生产负荷</div>
        <div id="load-mini-grid" style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:0"></div>
        <div style="border-top:1px solid var(--border);margin:20px 0;padding-top:16px">
          <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px">
            <span style="font-size:var(--fs-12);color:var(--text-3);white-space:nowrap">曲线</span>
            <select id="load-curve-select" onchange="onLoadCurveChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12);min-width:200px"></select>
            <span style="width:16px;flex-shrink:0"></span>
            <label style="display:flex;align-items:center;gap:4px;font-size:var(--fs-12);color:var(--text-2);cursor:pointer;white-space:nowrap"><input type="radio" name="load-scale" value="avg" checked onchange="onLoadScaleModeChange()"> 平均负荷</label>
            <input type="number" id="load-avg-input" step="0.1" value="3.0" oninput="onLoadScaleChange()" style="width:80px;background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)">
            <span style="font-size:var(--fs-11);color:var(--text-3)">MW</span>
            <label style="display:flex;align-items:center;gap:4px;font-size:var(--fs-12);color:var(--text-2);cursor:pointer;white-space:nowrap"><input type="radio" name="load-scale" value="max" onchange="onLoadScaleModeChange()"> 最大负荷</label>
            <input type="number" id="load-max-input" step="0.1" value="" disabled oninput="onLoadScaleChange()" style="width:80px;background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-3);font-size:var(--fs-12)">
            <span style="font-size:var(--fs-11);color:var(--text-3)">MW</span>
            <span style="width:16px;flex-shrink:0"></span>
            <span style="font-size:var(--fs-12);color:var(--text-3);white-space:nowrap">最大需量</span>
            <span id="load-demand-val" style="font-size:var(--fs-12);color:var(--accent);font-weight:var(--fw-semi)">--</span>
            <span style="font-size:var(--fs-11);color:var(--text-3)">MW</span>
            <span style="font-size:var(--fs-12);color:var(--text-3);white-space:nowrap">需量出现时段</span>
            <span id="load-demand-period" style="font-size:var(--fs-12);color:var(--text-2)">--</span>
            <span style="width:16px;flex-shrink:0"></span>
            <span style="font-size:var(--fs-12);color:var(--text-3);white-space:nowrap">随机度</span>
            <select id="load-randomness" onchange="onLoadRandomnessChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)"><option value="none" selected>不随机</option><option value="awgn">加性高斯白噪声</option><option value="corr">一阶自相关噪声</option><option value="mult">乘性相对噪声</option><option value="lowfreq">低频形状微调</option></select>
            <span class="param-tip" data-tip="${_randTip.replace(/"/g,'&quot;')}">?</span>
          </div>
        </div>
        <div id="load-curve-chart" style="height:280px"></div>
      </div>`;
      loadLoadProfiles();
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

// 现货电价图表
async function renderSpotPriceCharts() {
  try {
    const res = await api('/params/spot-prices');
    const da = res.day_ahead;
    const rt = res.real_time;
    const spread = da.map((v, i) => +(rt[i] - v).toFixed(4));

    // 图1：日前电价
    renderSpotLineChart('spot-da-chart', da, '日前电价', '#a78bfa');
    // 图2：实时电价
    renderSpotLineChart('spot-rt-chart', rt, '实时电价', '#f87171');
    // 图3：价差柱状图
    renderSpotSpreadChart('spot-spread-chart', spread);
  } catch(e) {
    console.error('Spot price charts error:', e);
  }
}

function onSpotPriceSetChange() {
  renderSpotPriceCharts();
}

function renderSpotLineChart(containerId, data, name, color) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const chart = echarts.init(el);
  chart.setOption({
    title: { text: name, textStyle: { color: '#b0b8c8', fontSize: 12 }, left: 'center', top: 0 },
    tooltip: { trigger: 'axis', backgroundColor: '#1e2330', borderColor: '#2e3446', textStyle: { color: '#f0f2f5', fontSize: 11 } },
    grid: { left: 46, right: 20, top: 30, bottom: 20 },
    xAxis: { type: 'category', data: Array.from({length:24}, (_,i) => `${i}`), axisLine: { lineStyle: { color: '#2e3446' } }, axisLabel: { color: '#7a8298', fontSize: 8, interval: 0 } },
    yAxis: { type: 'value', name: '元/kWh', nameTextStyle: { color: '#7a8298', fontSize: 8 }, axisLine: { lineStyle: { color: '#2e3446' } }, axisLabel: { color: '#7a8298', fontSize: 8 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series: [{ name: name, type: 'line', data: data, smooth: true, symbol: 'none', lineStyle: { color: color, width: 1.5 }, areaStyle: { color: color.replace(')', ',0.12)').replace('rgb', 'rgba') } }],
  });
  window.addEventListener('resize', () => chart.resize());
}

function renderSpotSpreadChart(containerId, spread) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const chart = echarts.init(el);
  chart.setOption({
    title: { text: '价差曲线（实时 - 日前）', textStyle: { color: '#b0b8c8', fontSize: 12 }, left: 'center', top: 0 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e2330',
      borderColor: '#2e3446',
      textStyle: { color: '#f0f2f5', fontSize: 11 },
      formatter: p => `${p[0].name}:00<br/>价差: ${p[0].value > 0 ? '+' : ''}${p[0].value} 元/kWh`
    },
    grid: { left: 50, right: 30, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: Array.from({length:24}, (_,i) => `${i}`), axisLine: { lineStyle: { color: '#2e3446' } }, axisLabel: { color: '#7a8298', fontSize: 8, interval: 0 } },
    yAxis: { type: 'value', name: '元/kWh', nameTextStyle: { color: '#7a8298', fontSize: 8 }, axisLine: { lineStyle: { color: '#2e3446' } }, axisLabel: { color: '#7a8298', fontSize: 8 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series: [{
      name: '价差',
      type: 'bar',
      data: spread.map(v => ({
        value: v,
        itemStyle: { color: v >= 0 ? '#f87171' : '#5ea3ff' }
      })),
      barWidth: '60%',
    }],
  });
  window.addEventListener('resize', () => chart.resize());
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

// ===== 负荷曲线 =====
let loadProfilesData = [];
let loadDetailChart = null;
let loadMiniCharts = [];

function loadLoadProfiles() {
  App.api('/params/load-profiles').then(d => {
    loadProfilesData = d.profiles || [];
    renderLoadMiniGrid();
    const sel = document.getElementById('load-curve-select');
    if (sel) {
      sel.innerHTML = loadProfilesData.map((p,i) => `<option value="${i}">${i+1}.${p.label}</option>`).join('');
    }
    // 默认选择第 1 个（全天候生产,白天偏高），平均负荷 = 3 MW
    const defaultIdx = 0;
    if (sel) sel.value = defaultIdx;
    if (loadProfilesData.length > 0) {
      renderLoadDetail(defaultIdx);
    }
  }).catch(e => console.error('load profiles failed:', e));
}

function renderLoadMiniGrid() {
  const grid = document.getElementById('load-mini-grid');
  if (!grid) return;
  loadMiniCharts.forEach(c => c.dispose());
  loadMiniCharts = [];

  // 16 个内置曲线 + 1 个"用户自定义"占位
  let html = loadProfilesData.map((p,i) => `
    <div style="text-align:center;cursor:pointer" onclick="selectLoadProfile(${i})">
      <div id="load-mini-${i}" style="height:60px"></div>
      <div style="font-size:10px;color:var(--text-2);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${i+1}.${p.label}</div>
    </div>
  `).join('');
  // 第 17 个：用户自定义占位
  html += `<div style="text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center">
    <div style="height:60px;width:100%;background:var(--bg-strip);border:1px dashed var(--border);border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:var(--fs-11);color:var(--text-3)">用户自定义</div>
    <div style="font-size:10px;color:var(--text-3);margin-top:2px">17.用户自定义</div>
  </div>`;
  grid.innerHTML = html;

  loadProfilesData.forEach((p,i) => {
    const el = document.getElementById(`load-mini-${i}`);
    if (!el) return;
    const c = echarts.init(el);
    c.setOption({
      grid:{left:2,right:2,top:2,bottom:2},
      xAxis:{type:'category',data:p.hour_data.map((_,h)=>h),show:false},
      yAxis:{type:'value',show:false},
      series:[{type:'line',data:p.hour_data,smooth:true,symbol:'none',lineStyle:{color:'#5ea3ff',width:1},areaStyle:{color:'rgba(94,163,255,0.15)'}}],
    });
    loadMiniCharts.push(c);
  });
}

function selectLoadProfile(idx) {
  const sel = document.getElementById('load-curve-select');
  if (sel) sel.value = idx;
  renderLoadDetail(idx);
}

function renderLoadDetail(idx) {
  const p = loadProfilesData[idx];
  if (!p) return;

  // 填充默认值：平均负荷 = 3 MW，最大负荷自动算
  const avgInput = document.getElementById('load-avg-input');
  const maxInput = document.getElementById('load-max-input');
  const defaultAvg = 3.0;
  if (avgInput) avgInput.value = defaultAvg.toFixed(1);
  // 按平均负荷缩放后计算最大负荷
  const ratio = defaultAvg / p.avg_load_mw;
  const scaledMax = p.max_load_mw * ratio;
  if (maxInput) maxInput.value = scaledMax.toFixed(4);

  // 更新最大需量（span 元素用 textContent）
  const scaledDemand = p.max_demand_mw * ratio;
  const demandVal = document.getElementById('load-demand-val');
  const demandPeriod = document.getElementById('load-demand-period');
  if (demandVal) demandVal.textContent = scaledDemand.toFixed(4);
  if (demandPeriod) demandPeriod.textContent = p.max_demand_period;

  // 渲染缩放后的曲线
  const scaledHourData = p.hour_data.map(v => v * ratio);
  renderLoadDetailChart(scaledHourData, idx);
}

function renderLoadDetailChart(hourData, idx) {
  const el = document.getElementById('load-curve-chart');
  if (!el) return;
  if (loadDetailChart) loadDetailChart.dispose();
  loadDetailChart = echarts.init(el);

  const p = loadProfilesData[idx];
  loadDetailChart.setOption({
    tooltip:{trigger:'axis',backgroundColor:'#1e2330',borderColor:'#2e3446',textStyle:{color:'#f0f2f5',fontSize:11}},
    grid:{left:56,right:46,top:20,bottom:24},
    xAxis:{type:'category',data:Array.from({length:24},(_,i)=>`${i}:00`),axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:9,interval:0}},
    yAxis:{type:'value',name:'MW',nameTextStyle:{color:'#7a8298',fontSize:9},axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:9},splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}}},
    series:[{name:p?p.label:'负荷',type:'line',data:hourData,smooth:true,symbol:'none',lineStyle:{color:'#5ea3ff',width:1},areaStyle:{color:'rgba(94,163,255,0.10)'}}],
  });
  window.addEventListener('resize',()=>loadDetailChart&&loadDetailChart.resize());
}

function onLoadCurveChange() {
  const sel = document.getElementById('load-curve-select');
  if (!sel) return;
  renderLoadDetail(parseInt(sel.value)||0);
}

function onLoadScaleModeChange() {
  const mode = document.querySelector('input[name="load-scale"]:checked')?.value;
  const avgInput = document.getElementById('load-avg-input');
  const maxInput = document.getElementById('load-max-input');
  if (mode === 'avg') {
    avgInput.disabled = false;
    maxInput.disabled = true;
    maxInput.value = '';
  } else {
    avgInput.disabled = true;
    avgInput.value = '';
    maxInput.disabled = false;
  }
  onLoadScaleChange();
}

function onLoadScaleChange() {
  const sel = document.getElementById('load-curve-select');
  if (!sel) return;
  const idx = parseInt(sel.value)||0;
  const p = loadProfilesData[idx];
  if (!p) return;

  const mode = document.querySelector('input[name="load-scale"]:checked')?.value;
  let body = { profile_name: p.name };
  if (mode === 'avg') {
    const v = parseFloat(document.getElementById('load-avg-input').value);
    if (!isNaN(v) && v > 0) body.avg_load = v;
    else return;
  } else {
    const v = parseFloat(document.getElementById('load-max-input').value);
    if (!isNaN(v) && v > 0) body.max_load = v;
    else return;
  }

  App.api('/params/load-profile/preview', { method:'POST', body:JSON.stringify(body) }).then(d => {
    // 实时更新另一侧数值
    if (mode === 'avg') {
      document.getElementById('load-max-input').value = d.max_load_mw.toFixed(4);
    } else {
      document.getElementById('load-avg-input').value = d.avg_load_mw.toFixed(4);
    }
    // 应用随机度
    const randomized = _generateRandomizedCurve(d.hour_data);
    // 重新计算需量
    const sel2 = document.getElementById('load-curve-select');
    const idx2 = parseInt(sel2?.value)||0;
    const p2 = loadProfilesData[idx2];
    if (p2) {
      const ratio2 = (mode === 'avg')
        ? (parseFloat(document.getElementById('load-avg-input').value) / p2.avg_load_mw)
        : (parseFloat(document.getElementById('load-max-input').value) / p2.max_load_mw);
      const scaledMinute = p2.minute_data.map(v => v * ratio2);
      const randomizedMinute = _applyRandomnessToMinute(scaledMinute);
      const {maxDemand, period} = _calcMaxDemandFromMinute(randomizedMinute);
      document.getElementById('load-demand-val').textContent = maxDemand.toFixed(4);
      document.getElementById('load-demand-period').textContent = period;
    }
    renderLoadDetailChart(randomized, idx2);
  }).catch(e => console.error('preview failed:', e));
}

// ===== 随机度算法 =====
function _seededRandom(seed) {
  let s = seed;
  return function() { s = (s * 16807 + 0) % 2147483647; return s / 2147483647; };
}

function _gaussianNoise(rng) {
  let u1 = rng(), u2 = rng();
  while (u1 === 0) u1 = rng();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

function _applyAwgn(hourData, intensity, rng) {
  const avgVal = hourData.reduce((a,b) => a+b, 0) / hourData.length;
  const sigma = avgVal * intensity;
  return hourData.map(v => Math.max(0, v + _gaussianNoise(rng) * sigma));
}

function _applyCorrelatedNoise(hourData, intensity, rho, rng) {
  const avgVal = hourData.reduce((a,b) => a+b, 0) / hourData.length;
  const sigma = avgVal * intensity;
  let prev = _gaussianNoise(rng) * sigma;
  return hourData.map(v => {
    const noise = rho * prev + Math.sqrt(1 - rho * rho) * _gaussianNoise(rng) * sigma;
    prev = noise;
    return Math.max(0, v + noise);
  });
}

function _applyMultiplicativeNoise(hourData, coeff, rng) {
  return hourData.map(v => Math.max(0, v * (1 + _gaussianNoise(rng) * coeff)));
}

function _applyLowFreqModulation(hourData, freq, amplitude, rng) {
  const avgVal = hourData.reduce((a,b) => a+b, 0) / hourData.length;
  const amp = avgVal * amplitude;
  const phase = rng() * 2 * Math.PI;
  return hourData.map((v, i) => Math.max(0, v + amp * Math.sin(2 * Math.PI * freq * i / 24 + phase)));
}

function _generateRandomizedCurve(baseHourData) {
  const mode = document.getElementById('load-randomness')?.value || 'none';
  if (mode === 'none') return baseHourData;
  const seed = Date.now() % 2147483647;
  const rng = _seededRandom(seed);
  switch (mode) {
    case 'awgn': return _applyAwgn(baseHourData, 0.04, rng);
    case 'corr': return _applyCorrelatedNoise(baseHourData, 0.03, 0.85, rng);
    case 'mult': return _applyMultiplicativeNoise(baseHourData, 0.03, rng);
    case 'lowfreq': return _applyLowFreqModulation(baseHourData, 3, 0.03, rng);
    default: return baseHourData;
  }
}

function _getBaseScaledHourData() {
  const sel = document.getElementById('load-curve-select');
  if (!sel) return null;
  const idx = parseInt(sel.value) || 0;
  const p = loadProfilesData[idx];
  if (!p) return null;
  const mode = document.querySelector('input[name="load-scale"]:checked')?.value;
  let ratio = 1;
  if (mode === 'avg') {
    const v = parseFloat(document.getElementById('load-avg-input').value);
    if (!isNaN(v) && v > 0) ratio = v / p.avg_load_mw;
  } else {
    const v = parseFloat(document.getElementById('load-max-input').value);
    if (!isNaN(v) && v > 0) ratio = v / p.max_load_mw;
  }
  return p.hour_data.map(v => v * ratio);
}

function _applyRandomnessToMinute(minuteData) {
  const mode = document.getElementById('load-randomness')?.value || 'none';
  if (mode === 'none') return minuteData;
  const seed = Date.now() % 2147483647;
  const rng = _seededRandom(seed);
  switch (mode) {
    case 'awgn': return _applyAwgn(minuteData, 0.04, rng);
    case 'corr': return _applyCorrelatedNoise(minuteData, 0.03, 0.85, rng);
    case 'mult': return _applyMultiplicativeNoise(minuteData, 0.03, rng);
    case 'lowfreq': return _applyLowFreqModulation(minuteData, 3, 0.03, rng);
    default: return minuteData;
  }
}

function _calcMaxDemandFromMinute(minuteData) {
  const padded = [minuteData[0]].concat(minuteData);
  const rolling = [];
  for (let i = 14; i < padded.length; i++) {
    const window = padded.slice(i - 14, i + 1);
    rolling.push(window.reduce((a,b) => a+b, 0) / 15);
  }
  const maxVal = Math.max(...rolling);
  const maxIdx = rolling.indexOf(maxVal);
  const startH = Math.floor(maxIdx / 60);
  const startM = maxIdx % 60;
  const endM = maxIdx + 15;
  const endH = Math.floor(endM / 60);
  const endMM = endM % 60;
  return {
    maxDemand: maxVal,
    period: `${String(startH).padStart(2,'0')}:${String(startM).padStart(2,'0')}-${String(Math.min(endH,23)).padStart(2,'0')}:${String(endMM).padStart(2,'0')}`
  };
}

function _refreshLoadView(hourData) {
  const demandVal = document.getElementById('load-demand-val');
  const demandPeriod = document.getElementById('load-demand-period');
  if (demandVal) demandVal.textContent = '--';
  if (demandPeriod) demandPeriod.textContent = '--';
  renderLoadDetailChart(hourData, parseInt(document.getElementById('load-curve-select')?.value) || 0);
}

function onLoadRandomnessChange() {
  const baseData = _getBaseScaledHourData();
  if (!baseData) return;
  const randomized = _generateRandomizedCurve(baseData);
  // 计算随机化后的需量
  const sel = document.getElementById('load-curve-select');
  const idx = parseInt(sel?.value)||0;
  const p = loadProfilesData[idx];
  if (p) {
    const mode = document.querySelector('input[name="load-scale"]:checked')?.value;
    const ratio = mode === 'avg'
      ? (parseFloat(document.getElementById('load-avg-input').value) / p.avg_load_mw)
      : (parseFloat(document.getElementById('load-max-input').value) / p.max_load_mw);
    const scaledMinute = p.minute_data.map(v => v * ratio);
    const randomizedMinute = _applyRandomnessToMinute(scaledMinute);
    const {maxDemand, period} = _calcMaxDemandFromMinute(randomizedMinute);
    document.getElementById('load-demand-val').textContent = maxDemand.toFixed(4);
    document.getElementById('load-demand-period').textContent = period;
  }
  renderLoadDetailChart(randomized, idx);
}

// 分时电价 tab 切换
function switchTariffTouTab(el, tabName) {
  document.querySelectorAll('.params-tariff-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('[id^="tariff-tou-content-"]').forEach(d => d.style.display = 'none');
  document.getElementById('tariff-tou-content-' + tabName).style.display = '';
  renderTariffTouTab(tabName);
}

// 渲染分时电价子 tab 内容
function renderTariffTouTab(tabName) {
  const d = globalParamsData;
  if (!d) return;
  if (tabName === 'admin') {
    const container = document.getElementById('tariff-tou-content-admin');
    if (!container) return;
    container.innerHTML = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <span style="font-size:var(--fs-12);color:var(--text-3)">时间段</span>
      <select id="tariff-admin-month" onchange="onTariffAdminTouChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)"></select>
      <span style="font-size:var(--fs-12);color:var(--text-3)">省份</span>
      <select id="tariff-admin-province" onchange="onTariffAdminTouChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)"></select>
      <span style="font-size:var(--fs-12);color:var(--text-3)">用电性质</span>
      <select id="tariff-admin-biz-type" onchange="onTariffAdminTouChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)"></select>
      <span style="font-size:var(--fs-12);color:var(--text-3)">电压等级</span>
      <select id="tariff-admin-voltage" onchange="onTariffAdminTouChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)"></select>
    </div>
    <div id="tariff-admin-chart" style="height:280px;margin-bottom:16px"></div>
    <div id="tariff-admin-table"></div>`;
    initTariffAdminTou();
  } else if (tabName === 'contract') {
    const container = document.getElementById('tariff-tou-content-contract');
    if (!container) return;
    container.innerHTML = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <span style="font-size:var(--fs-12);color:var(--text-3)">电价曲线</span>
      <select id="tariff-contract-curve" onchange="onTariffContractCurveChange()" style="background:#1a1f2d;border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text-1);font-size:var(--fs-12)">
        <option value="typical" selected>典型峰谷平</option>
        <option value="midday_valley">午间深谷</option>
        <option value="summer_peak">夏季尖峰</option>
      </select>
    </div>
    <div id="tariff-contract-chart" style="height:280px;margin-bottom:16px"></div>
    <div id="tariff-contract-table"></div>`;
    onTariffContractCurveChange();
  } else if (tabName === 'flat') {
    const container = document.getElementById('tariff-tou-content-flat');
    if (!container) return;
    container.innerHTML = `<div class="params-grid cols-3"><div class="params-field"><label>一口价 (元/kWh)</label><input type="number" id="gp-flat-price" step="0.01" value="${d.flat_price||0.5}"></div></div>`;
  }
}

// ===== 行政分时电价（全国） =====
let tariffAdminData = null;
let tariffAdminChart = null;

const PROVINCE_NAMES = {
  Anhui:'安徽',Beijing:'北京',Chongqing:'重庆',Fujian:'福建',Gansu:'甘肃',
  Guangdong:'广东',Guangxi:'广西',Guizhou:'贵州',Hainan:'海南',Hebei:'河北',
  Heilongjiang:'黑龙江',Henan:'河南',Hubei:'湖北',Hunan:'湖南',
  InnerMongolia:'内蒙古',Jiangsu:'江苏',Jiangxi:'江西',Jilin:'吉林',
  Liaoning:'辽宁',Ningxia:'宁夏',Qinghai:'青海',Shaanxi:'陕西',
  Shandong:'山东',Shanxi:'山西',Shanghai:'上海',Sichuan:'四川',
  Taiwan:'台湾',Tianjin:'天津',Tibet:'西藏',Xinjiang:'新疆',Yunnan:'云南',
};

const BIZ_TYPE_NAMES = {
  commercial:'工商业用电',general_commercial:'一般工商业用电',heavy_industry:'大工业用电',
};

async function initTariffAdminTou() {
  try {
    const provinces = await App.api('/tariff/administrative/provinces');
    const provSel = document.getElementById('tariff-admin-province');
    if (provSel) {
      provSel.innerHTML = provinces.map(p => `<option value="${p}" ${p==='Beijing'?'selected':''}>${PROVINCE_NAMES[p]||p}</option>`).join('');
    }
    await onTariffAdminTouChange();
  } catch(e) { console.error('init tariff admin tou failed:', e); }
}

async function onTariffAdminTouChange() {
  const province = document.getElementById('tariff-admin-province')?.value;
  if (!province) return;

  // 加载月份列表
  try {
    const months = await App.api(`/tariff/administrative/months/${province}`);
    const monthSel = document.getElementById('tariff-admin-month');
    const prevMonth = monthSel?.value;
    if (monthSel) {
      monthSel.innerHTML = months.map(m => `<option value="${m}" ${m===(prevMonth||'202606')?'selected':''}>${m}</option>`).join('');
    }
    const month = monthSel?.value || months[0];

    // 加载用电类别
    const bizTypes = await App.api(`/tariff/administrative/business-types/${province}/${month}`);
    const bizSel = document.getElementById('tariff-admin-biz-type');
    const prevBiz = bizSel?.value;
    if (bizSel) {
      bizSel.innerHTML = bizTypes.map(b => `<option value="${b}" ${b===(prevBiz||bizTypes[0])?'selected':''}>${BIZ_TYPE_NAMES[b]||b}</option>`).join('');
    }
    const bizType = bizSel?.value || bizTypes[0];

    // 加载电价数据
    const result = await App.api(`/tariff/administrative/data/${province}/${month}/${bizType}`);
    tariffAdminData = result;

    // 更新电压等级下拉（过滤掉全空的列）
    const validVoltageLevels = result.voltage_levels.filter(v => {
      return result.data.some(r => r[v] != null);
    });
    const voltSel = document.getElementById('tariff-admin-voltage');
    const prevVolt = voltSel?.value;
    if (voltSel) {
      voltSel.innerHTML = validVoltageLevels.map(v => `<option value="${v}" ${v===(prevVolt||validVoltageLevels[0])?'selected':''}>${v}</option>`).join('');
    }
    const voltage = voltSel?.value || validVoltageLevels[0];

    renderTariffAdminChart(result.data, voltage);
    renderTariffAdminTable(result.data, voltage);
  } catch(e) { console.error('tariff admin tou change failed:', e); }
}

function renderTariffAdminChart(data, voltageCol) {
  const el = document.getElementById('tariff-admin-chart');
  if (!el) return;
  if (tariffAdminChart) tariffAdminChart.dispose();
  tariffAdminChart = echarts.init(el);

  const prices = data.map(r => r[voltageCol] != null ? r[voltageCol] : 0);
  const periods = data.map(r => r['时段'] || '');
  const colors = prices.map((_, i) => {
    const p = periods[i];
    if (p === '峰' || p === '尖峰') return '#EB5757';
    if (p === '谷' || p === '深谷') return '#7EA8FA';
    return '#F2A104';
  });

  tariffAdminChart.setOption({
    tooltip:{trigger:'axis',backgroundColor:'#1e2330',borderColor:'#2e3446',textStyle:{color:'#f0f2f5',fontSize:11}},
    grid:{left:56,right:46,top:20,bottom:24},
    xAxis:{type:'category',data:data.map(r=>`${r.hour}:00`),axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:9,interval:0}},
    yAxis:{type:'value',name:'元/kWh',nameTextStyle:{color:'#7a8298',fontSize:9},axisLine:{lineStyle:{color:'#2e3446'}},axisLabel:{color:'#7a8298',fontSize:9},splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}}},
    series:[{type:'bar',data:prices.map((v,i)=>({value:v,itemStyle:{color:colors[i]}})),barWidth:'60%'}],
  });
  window.addEventListener('resize',()=>tariffAdminChart&&tariffAdminChart.resize());
}

function renderTariffAdminTable(data, voltageCol) {
  const el = document.getElementById('tariff-admin-table');
  if (!el) return;

  // 按时段聚合
  const segments = [];
  let curPeriod = null, curStart = 0, curPrices = [];
  data.forEach((r, i) => {
    const period = r['时段'] || '';
    const price = r[voltageCol];
    if (period !== curPeriod) {
      if (curPeriod !== null) {
        const avg = curPrices.length > 0 ? curPrices.reduce((a,b) => a+b, 0) / curPrices.length : 0;
        segments.push({ period: curPeriod, start: curStart, end: i, avgPrice: avg });
      }
      curPeriod = period;
      curStart = i;
      curPrices = price != null ? [price] : [];
    } else {
      if (price != null) curPrices.push(price);
    }
  });
  // 最后一段
  if (curPeriod !== null) {
    const avg = curPrices.length > 0 ? curPrices.reduce((a,b) => a+b, 0) / curPrices.length : 0;
    segments.push({ period: curPeriod, start: curStart, end: 24, avgPrice: avg });
  }

  const periodColors = { '峰': '#EB5757', '尖峰': '#EB5757', '谷': '#7EA8FA', '深谷': '#7EA8FA', '平': '#F2A104' };
  let html = '<table class="data-table"><tr><th>时段</th><th>时间范围</th><th>平均电价 (元/kWh)</th></tr>';
  segments.forEach(s => {
    const color = periodColors[s.period] || 'var(--text-1)';
    html += `<tr><td style="color:${color};font-weight:var(--fw-semi)">${s.period}</td><td>${s.start}:00 ~ ${s.end}:00</td><td>${s.avgPrice.toFixed(4)}</td></tr>`;
  });
  html += '</table>';
  el.innerHTML = html;
}
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

  // 等效利用小时数 = 日归一化出力之和 × 365
  const dailySum = data.reduce((a,b) => a+b, 0);
  const utilHours = (dailySum * 365).toFixed(0);
  const utilEl = document.getElementById('pv-util-hours');
  if (utilEl) utilEl.textContent = utilHours;
}

async function onPvCurveChange() {
  const region = document.getElementById('pv-region').value;
  const curveType = document.getElementById('pv-curve-type').value;
  const curveLabels = {annual_avg:'全年日均',cloudy:'阴天',sunny:'晴天'};
  const sel = document.getElementById('pv-curve-type');
  try {
    const pv = await api('/params/pv');
    const opts = (pv.curves[region]||[]).map(c=>`<option value="${c}" ${c===curveType?'selected':''}>${curveLabels[c]||c}</option>`).join('');
    sel.innerHTML = opts;
    const res = await api(`/params/pv-curve/${region}/${sel.value}`);
    renderPvCurveChart(res.data, region, sel.value);
  } catch(e) { console.error('PV curve load failed:', e); }
}

// 光伏消纳折扣 — 电费模式联动
const PV_TARIFF_CURVES = {
  admin: [{v:'admin_henan',l:'河南行政分时'}],
  contract: [{v:'standard',l:'标准合同分时'}],
  flat: [{v:'flat_0.5',l:'固定 0.5 元/kWh'},{v:'flat_0.6',l:'固定 0.6 元/kWh'}],
  spot_da: [{v:'henan_mar',l:'河南3月日前现货'}],
  spot_rt: [{v:'henan_mar',l:'河南3月实时现货'}],
  lt_contract: [{v:'henan_202603',l:'河南2026年3月中长期'}],
};

function onPvTariffModeChange() {
  const mode = document.getElementById('pv-tariff-mode')?.value;
  const curveSel = document.getElementById('pv-tariff-curve');
  if (!mode || !curveSel) return;
  const curves = PV_TARIFF_CURVES[mode] || [];
  curveSel.innerHTML = curves.map(c=>`<option value="${c.v}">${c.l}</option>`).join('');
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
  const targetTariff = document.getElementById('contract-target-tariff')?.value || 'typical';
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
    const res = await api(`/params/contract-curve?total_mwh=${totalMwh}&curve_type=${curveType}&tariff_curve=${targetTariff}`);
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

// --- 电价曲线预设数据 ---
const TARIFF_CURVES = {
  typical: {
    label: '典型峰谷平',
    periods: [
      {period:'valley', start:0, end:8, price:0.28, label:'谷段'},
      {period:'peak',   start:8, end:12, price:0.95, label:'峰段'},
      {period:'flat',   start:12, end:17, price:0.58, label:'平段'},
      {period:'peak',   start:17, end:21, price:0.95, label:'峰段'},
      {period:'flat',   start:21, end:24, price:0.58, label:'平段'},
    ]
  },
  midday_valley: {
    label: '午间深谷',
    periods: [
      {period:'valley', start:0, end:6, price:0.25, label:'谷段'},
      {period:'flat',   start:6, end:9, price:0.50, label:'平段'},
      {period:'peak',   start:9, end:12, price:0.90, label:'峰段'},
      {period:'deep_valley', start:12, end:15, price:0.15, label:'深谷'},
      {period:'flat',   start:15, end:18, price:0.50, label:'平段'},
      {period:'peak',   start:18, end:22, price:0.90, label:'峰段'},
      {period:'valley', start:22, end:24, price:0.25, label:'谷段'},
    ]
  },
  summer_peak: {
    label: '夏季尖峰',
    periods: [
      {period:'valley', start:0, end:6, price:0.30, label:'谷段'},
      {period:'flat',   start:6, end:8, price:0.55, label:'平段'},
      {period:'peak',   start:8, end:11, price:0.95, label:'峰段'},
      {period:'super_peak', start:11, end:14, price:1.20, label:'尖峰'},
      {period:'flat',   start:14, end:17, price:0.55, label:'平段'},
      {period:'peak',   start:17, end:21, price:0.95, label:'峰段'},
      {period:'valley', start:21, end:24, price:0.30, label:'谷段'},
    ]
  }
};

// 将时段数据展开为 24 小时电价数组
function tariffCurveToHourly(curveKey) {
  const curve = TARIFF_CURVES[curveKey] || TARIFF_CURVES.typical;
  const hourly = new Array(24).fill(0);
  for (const p of curve.periods) {
    for (let h = p.start; h < p.end; h++) hourly[h] = p.price;
  }
  return hourly;
}

// 行政分时电价柱状图
function onTariffAdminCurveChange() {
  const curveKey = document.getElementById('tariff-admin-curve').value;
  const hourly = tariffCurveToHourly(curveKey);
  renderTariffBarChart('tariff-admin-chart', hourly, '行政分时电价');
  const curve = TARIFF_CURVES[curveKey];
  const tbl = document.getElementById('tariff-admin-table');
  if (tbl) {
    tbl.innerHTML = tablePanelHTML('时段明细',
      ['时段','起始','结束','电价 (元/kWh)'],
      curve.periods.map(r=>[r.label, r.start+':00', r.end+':00', r.price])
    );
  }
}

// 合同分时电价柱状图
function onTariffContractCurveChange() {
  const curveKey = document.getElementById('tariff-contract-curve').value;
  const hourly = tariffCurveToHourly(curveKey);
  renderTariffBarChart('tariff-contract-chart', hourly, '合同分时电价');
  const curve = TARIFF_CURVES[curveKey];
  const tbl = document.getElementById('tariff-contract-table');
  if (tbl) {
    tbl.innerHTML = tablePanelHTML('时段明细',
      ['时段','起始','结束','电价 (元/kWh)'],
      curve.periods.map(r=>[r.label, r.start+':00', r.end+':00', r.price])
    );
  }
}

// 中长期分解曲线类型变化 → 控制标的分时电价下拉
function onContractCurveTypeChange() {
  const curveType = document.getElementById('contract-curve-type').value;
  const targetSel = document.getElementById('contract-target-tariff');
  if (!targetSel) return;
  targetSel.disabled = (curveType === 'load');
  targetSel.style.color = (curveType === 'load') ? 'var(--text-3)' : 'var(--text-1)';
  targetSel.style.opacity = (curveType === 'load') ? '0.5' : '1';
}

// 通用电价柱状图渲染
function renderTariffBarChart(containerId, hourly, seriesName) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const chart = echarts.init(el);
  const colors = hourly.map(p => {
    if (p >= 0.9) return '#f87171'; // 峰-红
    if (p >= 0.5) return '#fbbf24'; // 平-黄
    return '#5ea3ff';               // 谷-蓝
  });
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e2330',
      borderColor: '#2e3446',
      textStyle: { color: '#f0f2f5', fontSize: 11 },
      formatter: p => `${p[0].name}:00<br/>电价: ${p[0].value} 元/kWh`
    },
    grid: { left: 50, right: 30, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: Array.from({length:24}, (_,i) => `${i}`),
      axisLine: { lineStyle: { color: '#2e3446' } },
      axisLabel: { color: '#7a8298', fontSize: 8, interval: 0 },
    },
    yAxis: {
      type: 'value',
      name: '元/kWh',
      nameTextStyle: { color: '#7a8298', fontSize: 8 },
      axisLine: { lineStyle: { color: '#2e3446' } },
      axisLabel: { color: '#7a8298', fontSize: 8 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
    },
    series: [{
      name: seriesName,
      type: 'bar',
      data: hourly.map((v, i) => ({
        value: v,
        itemStyle: { color: colors[i] }
      })),
      barWidth: '60%',
    }],
  });
  window.addEventListener('resize', () => chart.resize());
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
    // 提供更友好的错误信息
    let errorMsg = e.message;
    if (e.message === 'Failed to fetch') {
      errorMsg = '无法连接到服务器，请确认后端服务已启动 (python run.py)';
    }
    alert('加载全局参数失败: ' + errorMsg);
  }
}

// --- App 注册 ---
App.params = {
  loadGlobalParams, initParamsMenu, renderPanelContent, selectPanel,
  toggleSection, switchTariffTab, onPvCurveChange,
  renderPvCurveChart, appendEssNotes, markParamsDirty, bindDirtyTracking,
  onContractModeChange, onContractCurveChange, renderContractChart,
  onTariffAdminCurveChange, onTariffContractCurveChange,
  onTariffAdminTouChange, initTariffAdminTou,
  onContractCurveTypeChange, renderTariffBarChart,
  renderSpotPriceCharts, onSpotPriceSetChange,
  switchTariffTouTab, renderTariffTouTab,
  onLoadCurveChange, onLoadScaleModeChange, onLoadScaleChange, onLoadRandomnessChange,
  onPvTariffModeChange,
  get currentPanel() { return currentPanel; },
  set currentPanel(v) { currentPanel = v; }
};

