/* Moola 原型 —— 交互逻辑（复刻简约记账） */
'use strict';

/* ============ 数据 ============ */
// 类型（复刻简约记账默认分类）
const TYPES = {
  expense: [
    { name: '餐饮', icon: '🍜' }, { name: '交通', icon: '🚌' },
    { name: '购物', icon: '🛒' }, { name: '居住', icon: '🏠' },
    { name: '娱乐', icon: '🎮' }, { name: '医疗', icon: '💊' },
    { name: '教育', icon: '📚' }, { name: '转账', icon: '💸' },
    { name: '水果', icon: '🍎' }, { name: '零食', icon: '🍿' },
    { name: '服饰', icon: '👕' }, { name: '日用', icon: '🧴' },
    { name: '通讯', icon: '📱' }, { name: '其他', icon: '📦' },
  ],
  income: [
    { name: '工资', icon: '💰' }, { name: '奖金', icon: '🎁' },
    { name: '红包', icon: '🧧' }, { name: '退款', icon: '↩️' },
    { name: '报销', icon: '📄' }, { name: '理财', icon: '📈' },
    { name: '兼职', icon: '💼' }, { name: '其他收入', icon: '💵' },
  ],
};

// 示例账单（与 sample_wechat.csv 一致）
const TX_ICONS = { 餐饮:'🍜', 交通:'🚌', 购物:'🛒', 居住:'🏠', 娱乐:'🎮', 其他支出:'📦', 转账:'💸', 收入:'💰' };
const INITIAL_TX = [
  { date: '2026-08-02', items: [
    { type: '餐饮', remark: '瑞幸咖啡 · 拿铁', money: -19.90 },
    { type: '交通', remark: '滴滴出行 · 快车', money: -18.00 },
  ]},
  { date: '2026-08-01', items: [
    { type: '餐饮', remark: '美团外卖 · 午餐', money: -32.50 },
  ]},
  { date: '2026-07-31', items: [
    { type: '购物', remark: '便利店 · 饮料零食', money: -23.50 },
    { type: '其他支出', remark: '顺丰速运 · 寄件', money: -12.00 },
  ]},
  { date: '2026-07-28', items: [
    { type: '餐饮', remark: '星巴克 · 美式', money: -33.00 },
  ]},
  { date: '2026-07-25', items: [
    { type: '餐饮', remark: '美团外卖 · 晚餐', money: -28.80 },
  ]},
  { date: '2026-07-20', items: [
    { type: '收入', remark: '工资 · 7月实习', money: 3000.00 },
  ]},
  { date: '2026-07-18', items: [
    { type: '购物', remark: '淘宝 · 夏季衣物', money: -258.00 },
  ]},
  { date: '2026-07-15', items: [
    { type: '居住', remark: '国家电网 · 电费', money: -156.30 },
  ]},
  { date: '2026-07-12', items: [
    { type: '娱乐', remark: '万达影城 · 电影票', money: -78.00 },
  ]},
  { date: '2026-07-10', items: [
    { type: '餐饮', remark: '麦当劳 · 汉堡', money: -45.50 },
  ]},
  { date: '2026-07-08', items: [
    { type: '购物', remark: '京东商城 · 数码', money: -129.00 },
  ]},
  { date: '2026-07-05', items: [
    { type: '转账', remark: '张三 · 还钱', money: 500.00 },
  ]},
];

// 状态
let state = {
  currentTab: 'page-account',
  naKind: 'expense',        // 记账页收支类型
  selectedType: null,
  moneyStr: '0',
  sign: -1,                  // -1 支出 / +1 收入
  againMode: false,
};

/* ============ 工具 ============ */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const fmt = (n) => {
  const neg = n < 0; const v = Math.abs(n).toFixed(2);
  return (neg ? '-' : '') + v.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

/* ============ 底部 Tab 切换 ============ */
function switchTab(pageId) {
  state.currentTab = pageId;
  $$('.page').forEach(p => p.classList.remove('active'));
  $('#' + pageId).classList.add('active');
  $$('.tabbar .tab').forEach(t => t.classList.toggle('active', t.dataset.page === pageId));
}
$$('.tabbar .tab').forEach(t => t.addEventListener('click', () => switchTab(t.dataset.page)));

/* ============ 明细列表渲染 ============ */
function renderTxList() {
  const wrap = $('#tx-list');
  wrap.innerHTML = '';
  INITIAL_TX.forEach(group => {
    const g = document.createElement('div');
    g.className = 'tx-group';
    const daySum = group.items.reduce((s, it) => s + it.money, 0);
    const head = document.createElement('div');
    head.className = 'tx-group-head';
    const [y, m, d] = group.date.split('-');
    head.innerHTML = `<span>${m}月${d}日 星期${'日一二三四五六'[new Date(group.date).getDay()]}</span>`;
    const sumEl = document.createElement('span');
    sumEl.textContent = '支出 ¥' + fmt(Math.min(0, daySum)) + '  收入 ¥' + fmt(Math.max(0, daySum));
    head.appendChild(sumEl);
    g.appendChild(head);
    group.items.forEach(it => {
      const item = document.createElement('div');
      item.className = 'tx-item';
      item.innerHTML = `
        <div class="tx-icon">${TX_ICONS[it.type] || '📦'}</div>
        <div class="tx-mid">
          <div class="tx-type">${it.type}</div>
          <div class="tx-remark">${it.remark}</div>
        </div>
        <div class="tx-money ${it.money > 0 ? 'income' : ''}">${it.money > 0 ? '+' : ''}${fmt(it.money)}</div>`;
      g.appendChild(item);
    });
    wrap.appendChild(g);
  });
}

/* ============ 记账页 ============ */
function renderTypeGrid() {
  const grid = $('#type-grid');
  grid.innerHTML = '';
  TYPES[state.naKind].forEach(t => {
    const d = document.createElement('div');
    d.className = 'type-item' + (state.selectedType === t.name ? ' selected' : '');
    d.innerHTML = `<div class="type-icon">${t.icon}</div><div class="type-name">${t.name}</div>`;
    d.addEventListener('click', () => {
      state.selectedType = t.name;
      renderTypeGrid();
      $('#calc-panel').style.display = '';
    });
    grid.appendChild(d);
  });
}

function updateMoneyDisplay() {
  const v = parseFloat(state.moneyStr || '0');
  $('#money-display').textContent = fmt(v * state.sign);
  $('#money-display').style.color = state.sign > 0 ? 'var(--primary)' : 'var(--expense)';
}

function handleKey(k) {
  if (k === 'del') {
    state.moneyStr = state.moneyStr.slice(0, -1) || '0';
  } else if (k === 'plus') {
    state.sign = 1;          // 切换为收入
  } else if (k === 'minus') {
    state.sign = -1;         // 切换为支出
  } else if (k === '.') {
    if (!state.moneyStr.includes('.')) state.moneyStr += '.';
  } else if (k === 'done' || k === 'again') {
    commitTransaction(k === 'again');
    return;
  } else {
    // 数字
    if (state.moneyStr === '0') state.moneyStr = k;
    else if (state.moneyStr.replace('.', '').length < 9) state.moneyStr += k;
  }
  updateMoneyDisplay();
}

function commitTransaction(again) {
  const val = parseFloat(state.moneyStr || '0');
  if (val === 0 || !state.selectedType) { alert('请输入金额并选择类型'); return; }
  const amount = val * state.sign;
  const type = state.selectedType;
  const remark = $('#note-input').value.trim() || type;
  const date = state.dateLabel || '今天';
  const dateStr = date === '今天' ? '2026-08-03' : date;

  // 插入到列表顶部（同日分组）
  let group = INITIAL_TX.find(g => g.date === dateStr);
  if (!group) { group = { date: dateStr, items: [] }; INITIAL_TX.unshift(group); }
  group.items.unshift({ type, remark, money: amount });
  renderTxList();

  if (again) {
    // 再记：保留类型，清空金额和备注
    state.moneyStr = '0';
    state.againMode = true;
    $('#note-input').value = '';
    updateMoneyDisplay();
  } else {
    closeNewAccount();
  }
}

function openNewAccount() {
  state.naKind = 'expense';
  state.selectedType = null;
  state.moneyStr = '0';
  state.sign = -1;
  $('#note-input').value = '';
  $('#calc-panel').style.display = 'none';
  $$('#na-kind-tabs .na-tab').forEach(t => t.classList.toggle('active', t.dataset.kind === 'expense'));
  renderTypeGrid();
  updateMoneyDisplay();
  $('#page-newaccount').classList.add('active');
}
function closeNewAccount() {
  $('#page-newaccount').classList.remove('active');
  state.selectedType = null;
}

// 事件绑定
$('#fab-add').addEventListener('click', openNewAccount);
$('#na-back').addEventListener('click', closeNewAccount);
$$('#na-kind-tabs .na-tab').forEach(t => t.addEventListener('click', () => {
  state.naKind = t.dataset.kind;
  state.selectedType = null;
  $$('#na-kind-tabs .na-tab').forEach(x => x.classList.toggle('active', x === t));
  renderTypeGrid();
}));
$$('.np-key').forEach(k => k.addEventListener('click', () => handleKey(k.dataset.k)));

/* ============ 统计页 ============ */
const STAT_DATA = [
  { name: '购物',   amt: 410.50, color: '#303f9f' },
  { name: '居住',   amt: 156.30, color: '#3f51b5' },
  { name: '餐饮',   amt: 159.70, color: '#5c6bc0' },
  { name: '娱乐',   amt: 78.00,  color: '#7986cb' },
  { name: '交通',   amt: 18.00,  color: '#9fa8da' },
  { name: '其他',   amt: 12.00,  color: '#c5cae9' },
];

function renderTrend() {
  const days = [28, 55, 33, 90, 45, 62, 40, 78, 52, 30, 68, 45, 22, 58];
  const max = Math.max(...days);
  const chart = $('#trend-chart');
  chart.innerHTML = '';
  days.forEach(d => {
    const bar = document.createElement('div');
    bar.className = 'trend-bar';
    bar.style.height = (d / max * 140) + 'px';
    chart.appendChild(bar);
  });
}

function renderPie() {
  const total = STAT_DATA.reduce((s, d) => s + d.amt, 0);
  const svg = $('#pie-chart');
  svg.innerHTML = '';
  let angle = -90;
  const cx = 100, cy = 100, r = 78;
  STAT_DATA.forEach(d => {
    const pct = d.amt / total;
    const a0 = angle, a1 = angle + pct * 360;
    const x0 = cx + r * Math.cos(a0 * Math.PI / 180), y0 = cy + r * Math.sin(a0 * Math.PI / 180);
    const x1 = cx + r * Math.cos(a1 * Math.PI / 180), y1 = cy + r * Math.sin(a1 * Math.PI / 180);
    const large = pct > 0.5 ? 1 : 0;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M${cx},${cy} L${x0},${y0} A${r},${r} 0 ${large} 1 ${x1},${y1} Z`);
    path.setAttribute('fill', d.color);
    svg.appendChild(path);
    angle = a1;
  });
  // 中心挖空成环形
  const hole = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  hole.setAttribute('cx', cx); hole.setAttribute('cy', cy); hole.setAttribute('r', r * 0.45);
  hole.setAttribute('fill', '#fff');
  svg.appendChild(hole);
  const centerText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  centerText.setAttribute('x', cx); centerText.setAttribute('y', cy - 6);
  centerText.setAttribute('text-anchor', 'middle'); centerText.setAttribute('font-size', '14');
  centerText.setAttribute('fill', '#444'); centerText.textContent = '总支出';
  const centerAmt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  centerAmt.setAttribute('x', cx); centerAmt.setAttribute('y', cy + 16);
  centerAmt.setAttribute('text-anchor', 'middle'); centerAmt.setAttribute('font-size', '16');
  centerAmt.setAttribute('font-weight', 'bold'); centerAmt.setAttribute('fill', '#444');
  centerAmt.textContent = '¥' + fmt(total);
  svg.appendChild(centerText); svg.appendChild(centerAmt);

  // 明细列表
  const list = $('#stat-list');
  list.innerHTML = '';
  STAT_DATA.forEach(d => {
    const pct = (d.amt / total * 100).toFixed(1);
    const item = document.createElement('div');
    item.className = 'stat-item';
    item.innerHTML = `
      <span class="stat-dot" style="background:${d.color}"></span>
      <span class="stat-name">${d.name}</span>
      <span class="stat-pct">${pct}%</span>
      <span class="stat-amt">¥${fmt(d.amt)}</span>`;
    list.appendChild(item);
  });
}

// 周/月/年切换
$$('.period').forEach(p => p.addEventListener('click', () => {
  $$('.period').forEach(x => x.classList.toggle('active', x === p));
}));

/* ============ 初始化 ============ */
renderTxList();
renderTypeGrid();
renderTrend();
renderPie();
updateMoneyDisplay();

// 更新顶部概览数字（与示例数据一致）
$('#ov-expense-amt').textContent = fmt(1000);
$('#ov-income').textContent = '¥' + fmt(3500.00);
$('#ov-balance').textContent = '¥' + fmt(2665.50);
