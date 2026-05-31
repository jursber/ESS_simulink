// ===== flow.js =====

// --- 能量流动图 ---
function updateFlowDiagram(overview) {
  const essActive = (overview.ess_cap_mwh || 0) > 0;
  const pvActive = (overview.pv_cap_kw || 0) > 0;
  const wrap = document.querySelector('.architecture-image-wrap');
  if (!essActive && !pvActive) {
    wrap.classList.add('flow-dim');
  } else {
    wrap.classList.remove('flow-dim');
  }
  const essNode = document.getElementById('flow-ess');
  const pvNode = document.getElementById('flow-pv');
  const pvText = document.getElementById('flow-pv-text');
  const flexNode = document.getElementById('flow-load-flex');
  const flexText = document.getElementById('flow-flex-text');
  if (essNode) essNode.style.opacity = essActive ? '1' : '.25';
  if (pvNode) pvNode.style.opacity = pvActive ? '1' : '.35';
  if (pvText) pvText.setAttribute('fill', pvActive ? '#34d399' : '#6b7280');
  if (flexNode) flexNode.style.opacity = '.35';
  if (flexText) flexText.setAttribute('fill', '#6b7280');
}

// --- App 注册 ---
App.flow = { updateFlowDiagram };

