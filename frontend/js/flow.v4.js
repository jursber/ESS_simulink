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

  // 储能节点
  const essNode = document.getElementById('flow-ess');
  if (essNode) {
    essNode.style.opacity = essActive ? '1' : '.2';
    essNode.setAttribute('stroke', essActive ? '#4E9F3D' : '#333');
    essNode.setAttribute('fill', essActive ? 'rgba(78,159,61,0.10)' : 'rgba(78,159,61,0.03)');
  }

  // 光伏节点
  const pvNode = document.getElementById('flow-pv');
  const pvText = document.getElementById('flow-pv-text');
  if (pvNode) {
    pvNode.style.opacity = pvActive ? '1' : '.2';
    pvNode.setAttribute('stroke', pvActive ? '#F2A104' : '#333');
    pvNode.setAttribute('fill', pvActive ? 'rgba(242,161,4,0.10)' : 'rgba(242,161,4,0.03)');
  }
  if (pvText) pvText.setAttribute('fill', pvActive ? '#F2A104' : 'rgba(176,176,176,0.25)');

  // 可调负荷节点
  const flexNode = document.getElementById('flow-load-flex');
  const flexText = document.getElementById('flow-flex-text');
  if (flexNode) flexNode.style.opacity = '.2';
  if (flexText) flexText.setAttribute('fill', 'rgba(176,176,176,0.25)');
}

// --- App 注册 ---
App.flow = { updateFlowDiagram };
