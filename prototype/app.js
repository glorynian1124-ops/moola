/* ================================================================
   简约记账 · 复刻交互逻辑
   页面结构与交互流均参照 APK（com.yhqx.account）各 Activity
   ================================================================ */
'use strict';

/* ================= 工具 ================= */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function fmt(n) {
  // 千分位两位小数
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(n).toFixed(2);
  const [i, d] = abs.split('.');
  return sign + i.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '.' + d;
}

/* ================= 数据（与 sample_wechat.csv 一致） ================= */
const TYPES = {
  expense: [
    { name: '餐饮', icon: 'cate_restaurant.png' }, { name: '交通', icon: 'cate_bus.png' },
    { name: '购物', icon: 'cate_shopping.png' }, { name: '居住', icon: 'cate_home.png' },
    { name: '娱乐', icon: 'cate_game.png' }, { name: '医疗', icon: 'cate_medical.png' },
    { name: '教育', icon: 'cate_study.png' }, { name: '转账', icon: 'cate_redirect.png' },
    { name: '水果', icon: 'cate_fruit.png' }, { name: '零食', icon: 'cate_snack.png' },
    { name: '服饰', icon: 'cate_cloth.png' }, { name: '日用', icon: 'cate_daily.png' },
    { name: '通讯', icon: 'cate_phone.png' }, { name: '其他', icon: 'cate_more.png' },
  ],
  income: [
    { name: '工资', icon: 'cate_salary.png' }, { name: '奖金', icon: 'cate_reward.png' },
    { name: '红包', icon: 'cate_redbag.png' }, { name: '退款', icon: 'cate_refund.png' },
    { name: '报销', icon: 'cate_reimburse.png' }, { name: '理财', icon: 'cate_invest.png' },
    { name: '兼职', icon: 'cate_partjob.png' }, { name: '其他收入', icon: 'cate_moneybag.png' },
  ],
};

/* 图标 mask 渲染辅助（APK 白色扁平图标上色） */
function icIcon(file, cls = 'ic24') {
  return `<i class="ic ${cls}" style="--mask:url(assets/icons/${file})"></i>`;
}

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
    { type: '其他', remark: '顺丰速运 · 寄件', money: -12.00 },
  ]},
  { date: '2026-07-28', items: [
    { type: '餐饮', remark: '星巴克 · 美式', money: -33.00 },
  ]},
  { date: '2026-07-25', items: [
    { type: '餐饮', remark: '美团外卖 · 晚餐', money: -28.80 },
  ]},
  { date: '2026-07-20', items: [
    { type: '工资', remark: '工资 · 7月实习', money: 3000.00 },
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
    { type: '通讯', remark: '中国移动 · 话费', money: -100.00 },
  ]},
  { date: '2026-07-02', items: [
    { type: '娱乐', remark: 'KTV · 聚会', money: -168.00 },
  ]},
  { date: '2026-07-01', items: [
    { type: '零食', remark: '全家便利店 · 零食', money: -38.50 },
  ]},
];

// 账本集合：每个账本拥有独立的账单数据（tx）
let books = [
  { name: '默认账本', icon: 'ic_accounts.png', type: '标准账本', tx: JSON.parse(JSON.stringify(INITIAL_TX)) },
  { name: '旅行账本', icon: 'ic_plane.png', type: '旅行', tx: [] },
  { name: '家庭账本', icon: 'cate_home.png', type: '家庭', tx: [] },
];
let tx = books[0].tx; // 全局 tx 指向当前账本数据
const BOOK_ICONS = ['ic_accounts.png', 'ic_plane.png', 'cate_home.png', 'cate_salary.png', 'cate_shopping.png', 'cate_moneybag.png'];
const BOOK_TYPES = ['标准账本', '旅行', '家庭', '生意', '人情', '其他'];

// 状态
const state = {
  tab: 'page-account',
  naKind: 'expense',       // 记账页收支类型
  naType: null,            // 选中的类别
  moneyStr: '0',           // 计算器数字串
  dateLabel: '今天',
  calYear: 2026, calMonth: 8, calSelected: null,
  statCat: 'expense', statPeriod: 'week',
  searchMode: 'bill', searchSort: 'time', searchText: '',
  selectedBook: 0,
};
let acctYM = '2026-08';      // 明细页当前显示的年月
let wheelYear = 2026, wheelMonth = 8; // 年/月滚轮当前选择值

/* ================= 设置项（全局生效） ================= */
const settings = {
  bigDisplay: 'expense',      // expense | income | balance 首页大字
  moneyColor: 'redGreen',     // redGreen 支出红收入绿 | greenRed 对调
  sort: 'desc',               // desc 逆序 | asc 正序
  loadNeighbor: true,
  vibrate: true,
  startDay: 1,
  totalBalance: false,
};

function applyMoneyColors() {
  const root = document.documentElement;
  if (settings.moneyColor === 'redGreen') {
    root.style.setProperty('--exp-color', '#cc0000');
    root.style.setProperty('--inc-color', '#067d17');
  } else {
    root.style.setProperty('--exp-color', '#067d17');
    root.style.setProperty('--inc-color', '#cc0000');
  }
}

function moneyClass(money) { return money > 0 ? 'inc' : 'exp'; }

function sortedTx() {
  const arr = [...tx];
  if (settings.sort === 'asc') arr.reverse();
  return arr;
}

/* ================= 页面切换 ================= */
function showPage(id) {
  $$('.page').forEach(p => p.classList.remove('active'));
  const target = $('#' + id);
  target.classList.add('active');
  // 覆盖页全屏时隐藏底部导航，避免遮挡内容（如记账键盘的 0/发送键）
  $$('nav.tabbar').forEach(t => { t.style.display = target.classList.contains('overlay') ? 'none' : 'flex'; });
  if (id === 'page-stat') renderStat();
  if (id === 'page-calendar') renderCalendar();
}

$$('.tabbar .tab').forEach(tab => {
  tab.addEventListener('click', () => {
    $$('.tabbar .tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    showPage(tab.dataset.page);
  });
});

function openOverlay(id) { showPage(id); }
function closeOverlay() {
  // 记账日期选择模式：返回记账页而非底部 Tab
  if (calPickMode) { calPickMode = false; showPage('page-newaccount'); return; }
  showPage(state.tab);
}
let calPickMode = false; // 从记账页进入日历选日期的模式标志

$$('[data-back]').forEach(btn => btn.addEventListener('click', closeOverlay));

/* ================= 明细页 ================= */
function txIconFile(name) {
  const all = [...TYPES.expense, ...TYPES.income];
  const hit = all.find(t => t.name === name);
  return hit ? hit.icon : 'cate_more.png';
}

function weekDayCN(dateStr) {
  const d = new Date(dateStr.replace(/-/g, '/'));
  return ['日', '一', '二', '三', '四', '五', '六'][d.getDay()];
}

function renderTxList() {
  const list = $('#tx-list');
  const groups = sortedTx().filter(g => g.date.startsWith(acctYM)).map(g => {
    const spend = -g.items.filter(i => i.money < 0).reduce((s, i) => s + i.money, 0);
    const income = g.items.filter(i => i.money > 0).reduce((s, i) => s + i.money, 0);
    const [y, m, d] = g.date.split('-');
    return `
      <div class="tx-group">
        <div class="tx-group-head">
          <span>${y}年${+m}月${+d}日 星期${weekDayCN(g.date)}</span>
          <span>支出:${fmt(spend)} 收入:${fmt(income)}</span>
        </div>
        ${g.items.map(it => `
          <div class="tx-item">
            <div class="tx-icon">${icIcon(txIconFile(it.type), 'ic20')}</div>
            <div class="tx-mid">
              <div class="tx-type">${it.type}</div>
              <div class="tx-remark">${it.remark}</div>
            </div>
            ${it.pic ? `<div class="tx-thumb"><i class="ic ic14" style="--mask:url(assets/icons/ic_photo.png)"></i></div>` : ''}
            <div class="tx-money ${moneyClass(it.money)}">${it.money > 0 ? '+' : '-'}${fmt(Math.abs(it.money))}</div>
          </div>`).join('')}
      </div>`;
  }).join('');
  list.innerHTML = groups || emptyHtml();
  list.classList.toggle('has-empty', !groups); // 空状态时去掉底部内边距，让"暂无数据"真正居中
  updateOverview();
}

function emptyHtml() {
  return `<div class="empty-state">
    <i class="ic ic50" style="--mask:url(assets/icons/ic_empty.png)"></i>
    <div class="empty-text">暂无数据</div>
  </div>`;
}

function updateOverview() {
  const nowMonth = acctYM;
  const monthTx = tx.filter(g => g.date.startsWith(nowMonth)).flatMap(g => g.items);
  const expense = -monthTx.filter(i => i.money < 0).reduce((s, i) => s + i.money, 0);
  const income = monthTx.filter(i => i.money > 0).reduce((s, i) => s + i.money, 0);
  const balance = income - expense;

  // 首页大字显示切换（支出/收入/结余）
  const big = settings.bigDisplay;
  const bigVal = big === 'expense' ? expense : big === 'income' ? income : balance;
  const bigLabel = big === 'expense' ? '本月支出' : big === 'income' ? '本月收入' : '本月结余';
  $('#ov-label').textContent = bigLabel;
  $('#ov-expense-amt').textContent = fmt(bigVal);

  // 底部两行显示其余两项
  const bottom = big === 'expense'
    ? [['收入', income], ['结余', balance]]
    : big === 'income'
      ? [['支出', expense], ['结余', balance]]
      : [['支出', expense], ['收入', income]];
  $('#ov-bottom').innerHTML = bottom.map(([label, val]) => `
    <div class="ov-col"><span class="ov-label-sm">${label}</span><span class="ov-val">¥${fmt(val)}</span></div>`).join('');
}

/* ================= 统计页 ================= */
const PIE_COLORS = ['#303f9f', '#ee6c8c', '#d2691e', '#a52a2a', '#8b008b', '#008000', '#303030', '#753c2c', '#4c9aff', '#6c9f3f', '#e0673c', '#8e6cd8'];

function statData() {
  const sign = state.statCat === 'expense' ? -1 : 1;
  const items = tx.flatMap(g => g.items.map(it => ({ ...it, date: g.date })))
    .filter(i => Math.sign(i.money) === sign);
  return items;
}

function renderBarChart() {
  const data = statData();
  const box = $('#trend-chart');
  if (!data.length) { box.innerHTML = '<div class="stat-no-data">暂无数据</div>'; return; }

  const period = state.statPeriod; // week / month / year
  const dates = [...new Set(data.map(i => i.date))].sort();
  const last = new Date(dates[dates.length - 1].replace(/-/g, '/'));
  const lastY = last.getFullYear(), lastM = last.getMonth() + 1;

  const sumOf = (y, m, d) => {
    const key = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    return data.filter(i => i.date === key).reduce((s, i) => s + Math.abs(i.money), 0);
  };
  const daysIn = (y, m) => new Date(y, m, 0).getDate();

  // 周：每天一柱（周一~周日）；月：每5天一段（6段，刻度 5/10/15/20/25/30）；年：每月一柱
  let buckets = [], ticks = [];
  if (period === 'week') {
    const monday = new Date(last);
    monday.setDate(monday.getDate() - ((last.getDay() + 6) % 7));
    for (let i = 0; i < 7; i++) {
      const dd = new Date(monday); dd.setDate(monday.getDate() + i);
      buckets.push(sumOf(dd.getFullYear(), dd.getMonth() + 1, dd.getDate()));
      ticks.push(`${String(dd.getMonth() + 1).padStart(2, '0')}-${String(dd.getDate()).padStart(2, '0')}`);
    }
  } else if (period === 'month') {
    // 每天一柱（本月所有日期），刻度每 5 天标一次直到月末
    const dim = daysIn(lastY, lastM);
    for (let d = 1; d <= dim; d++) {
      buckets.push(sumOf(lastY, lastM, d));
      ticks.push(String(d));
    }
  } else {
    for (let m = 1; m <= 12; m++) {
      let s = 0;
      const dim = daysIn(lastY, m);
      for (let d = 1; d <= dim; d++) s += sumOf(lastY, m, d);
      buckets.push(s);
      ticks.push(m + '月');
    }
  }

  const max = Math.max(...buckets, 1);
  const n = buckets.length;
  const W = 370, H = 150, padL = 6, padR = 6, padT = 22, padB = 24;
  const bw = (W - padL - padR) / n;
  const barW = Math.min(26, bw * 0.6);
  const fontS = n > 12 ? 8 : 9;

  const bars = buckets.map((v, i) => {
    const h = Math.max(2, (v / max) * (H - padB - padT));
    const cx = padL + i * bw + bw / 2;
    const x = cx - barW / 2;
    const y = H - padB - h;
    const active = i === n - 1;
    const label = v ? v.toFixed(1) : '';
    const showTick = period !== 'month' || (i + 1) % 5 === 0 || i === n - 1;
    return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" rx="${barW < 12 ? 1 : 2}" fill="${active ? '#303f9f' : '#9aa0d6'}"/>` +
      (label ? `<text x="${cx.toFixed(1)}" y="${(y - 3).toFixed(1)}" text-anchor="middle" font-size="${fontS}" fill="#666666">${label}</text>` : '') +
      (showTick ? `<text x="${cx.toFixed(1)}" y="${(H - padB + 12).toFixed(1)}" text-anchor="middle" font-size="9" fill="#999999">${ticks[i]}</text>` : '');
  }).join('');

  box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${bars}</svg>`;
}

/* ============ 饼图手指旋转（原版 PieStatisticView） ============ */
function pieAngleOf(container, clientX, clientY) {
  const rect = container.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  return Math.atan2(clientY - cy, clientX - cx);
}

function bindPieRotation(container, renderFn) {
  let startAngle = 0, rotStart = 0, dragging = false;
  container.addEventListener('pointerdown', (e) => {
    dragging = true;
    startAngle = pieAngleOf(container, e.clientX, e.clientY);
    rotStart = container.__pieRot || 0;
    if (container.setPointerCapture) { try { container.setPointerCapture(e.pointerId); } catch (_) {} }
  });
  container.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const a = pieAngleOf(container, e.clientX, e.clientY);
    container.__pieRot = rotStart + (a - startAngle);
    renderFn();
  });
  const stop = () => { dragging = false; };
  container.addEventListener('pointerup', stop);
  container.addEventListener('pointercancel', stop);
}

function pieRotation(container) {
  return ((container.__pieRot || 0) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
}

function renderPie() {
  const data = statData();
  const pie = $('#pie-chart');
  if (!data.length) {
    pie.innerHTML = '<div class="stat-no-data">暂无数据</div>';
    $('#stat-list').innerHTML = '<div class="stat-no-data">暂无数据</div>';
    return;
  }

  // 按类别聚合
  const map = {};
  data.forEach(i => { map[i.type] = (map[i.type] || 0) + Math.abs(i.money); });
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, e) => s + e[1], 0);

  // 整块 .pie-canvas（390×210）都是轮盘显示区，viewBox 与容器 1:1
  const cx = 195, cy = 105, r = 70;
  const rot = pieRotation(pie);
  const deg = rot * 180 / Math.PI;

  // 弧段基准角（不含旋转；旋转由扇区组 transform 完成，避免重建导致的晃动）
  let angle = -Math.PI / 2;
  const arcs = entries.map((e, i) => {
    const frac = e[1] / total;
    const a0 = angle;
    const a1 = angle + frac * Math.PI * 2;
    angle = a1;
    return { name: e[0], val: e[1], idx: i, frac, a0, a1, fill: PIE_COLORS[i % PIE_COLORS.length] };
  });
  const shown = arcs.filter(a => a.frac >= 0.02);

  // —— 首次构建 SVG 骨架（之后仅更新属性/局部组，不再重建整个 svg）——
  if (!pie.__psec) {
    pie.innerHTML = `<svg viewBox="0 0 390 210">
      <g class="psec"></g>
      <g class="plbl"></g>
      <circle class="phole" fill="#f0f1f6"/>
      <text class="pamt" text-anchor="middle" font-size="14" fill="#666666"></text>
      <text class="pcat" text-anchor="middle" font-size="11" fill="#999999"></text>
    </svg>`;
    pie.__psec = pie.querySelector('.psec');
    pie.__plbl = pie.querySelector('.plbl');
    const hole = pie.querySelector('.phole');
    hole.setAttribute('cx', cx); hole.setAttribute('cy', cy); hole.setAttribute('r', 34);
    pie.__pamt = pie.querySelector('.pamt');
    pie.__pcat = pie.querySelector('.pcat');
    pie.__pamt.setAttribute('x', cx); pie.__pamt.setAttribute('y', cy - 4);
    pie.__pcat.setAttribute('x', cx); pie.__pcat.setAttribute('y', cy + 14);
  }

  // —— 扇区：仅在类别集合变化时重建 path，旋转只更新 transform ——
  const key = shown.map(a => a.name).join('|');
  if (pie.__psecKey !== key) {
    const GAP = 0.022; // 色块之间小留白
    pie.__psec.innerHTML = shown.map(a => {
      const large = a.frac > 0.5 ? 1 : 0;
      const a0 = a.a0 + GAP / 2, a1 = a.a1 - GAP / 2;
      const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
      const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
      return `<path d="M${cx},${cy} L${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 ${large} 1 ${x1.toFixed(1)},${y1.toFixed(1)} Z" fill="${a.fill}"/>`;
    }).join('');
    pie.__psecKey = key;
  }
  pie.__psec.setAttribute('transform', `rotate(${deg.toFixed(3)} ${cx} ${cy})`);

  // —— 标注（<2% 不显示）：位置跟随 rot，文字保持水平 ——
  pie.__plbl.innerHTML = shown.map(a => {
    const mid = (a.a0 + a.a1) / 2 + rot;
    const c = Math.cos(mid), s = Math.sin(mid);
    const right = c >= 0;
    const bx = cx + c * (r + 4), by = cy + s * (r + 4);     // 圆点（扇区外沿）
    const ox = cx + c * (r + 15), oy = cy + s * (r + 15);   // 折点
    const pct = (a.frac * 100).toFixed(1) + '%';
    const txt = a.name + ' ' + pct;
    const w = a.name.length * 9.5 + pct.length * 4.8 + 2;   // 估算文字宽
    const hlen = w * 2 / 3;                                  // 横向延长线（减少 1/3）
    const cgap = 10;                                         // 与数字留一个字符空隙
    const hx = right ? ox + hlen : ox - hlen;                // 水平横线终点
    const tx = right ? hx + cgap : hx - cgap;                // 文字起点
    return `<circle cx="${bx.toFixed(1)}" cy="${by.toFixed(1)}" r="2.5" fill="${a.fill}"/>` +
      `<line x1="${bx.toFixed(1)}" y1="${by.toFixed(1)}" x2="${ox.toFixed(1)}" y2="${oy.toFixed(1)}" stroke="${a.fill}" stroke-width="1.2"/>` +
      `<line x1="${ox.toFixed(1)}" y1="${oy.toFixed(1)}" x2="${hx.toFixed(1)}" y2="${oy.toFixed(1)}" stroke="${a.fill}" stroke-width="1.2"/>` +
      `<text x="${tx.toFixed(1)}" y="${oy.toFixed(1)}" text-anchor="${right ? 'start' : 'end'}" dominant-baseline="middle" font-size="9.5" fill="${a.fill}" font-weight="500">${txt}</text>`;
  }).join('');

  // 中心文字
  pie.__pamt.textContent = fmt(total);
  pie.__pcat.textContent = state.statCat === 'expense' ? '支出' : '收入';

  // 明细列表
  const list = $('#stat-list');
  list.innerHTML = arcs.map(a => {
    const pct = a.frac * 100;
    return `<div class="stat-item">
      <span class="stat-ic" style="color:${a.fill}"><i class="ic ic16" style="--mask:url(assets/icons/${txIconFile(a.name)})"></i></span>
      <span class="stat-name">${a.name}</span>
      <span class="stat-amt">${fmt(a.val)}</span>
      <span class="stat-pct">${pct >= 2 ? pct.toFixed(1) + '%' : ''}</span>
    </div>`;
  }).join('');
}

function renderStat() {
  renderBarChart();
  renderPie();
  // 空数据时保持三栏结构（统计/消费结构/明细），各栏内显示「暂无数据」
  $('#stat-empty').style.display = 'none';
}

$('#stat-cat-tabs').addEventListener('click', (e) => {
  const tab = e.target.closest('.stat-tab');
  if (!tab) return;
  $$('#stat-cat-tabs .stat-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  state.statCat = tab.dataset.cat;
  renderStat();
});

$('#period-group').addEventListener('click', (e) => {
  const p = e.target.closest('.period');
  if (!p) return;
  $$('#period-group .period').forEach(t => t.classList.remove('active'));
  p.classList.add('active');
  state.statPeriod = p.dataset.p;
  renderStat();
});

$('#btn-charttype').addEventListener('click', () => openBillStat());
$('#btn-region').addEventListener('click', () => openChartPage());

/* ================= 记账页 ================= */
let calcAcc = 0;        // 连加累计值
let calcOp = null;      // 运算符
let txDate = '2026-08-18'; // 记账日期
let hasPic = false;

function renderTypeGrid() {
  const grid = $('#type-grid');
  grid.innerHTML = TYPES[state.naKind].map(t => `
    <div class="type-cell" data-type="${t.name}">
      <div class="t-icon">${icIcon(t.icon, 'ic24')}</div>
      <div class="t-name">${t.name}</div>
      ${t.custom ? `<span class="t-badge">自</span>` : ''}
    </div>`).join('');
}

function updateMoneyDisplay() {
  $('#money-display').textContent = state.moneyStr;
  $('#money-display').style.color = state.moneyStr === '0' ? '#999999' : '#cc0000';
}

function resetCalc() { state.moneyStr = '0'; updateMoneyDisplay(); }

function pressKey(k) {
  if (k === 'done') { addTx(); return; }
  if (k === 'again') { addTx(true); return; }
  if (k === 'del') {
    state.moneyStr = state.moneyStr.length > 1 ? state.moneyStr.slice(0, -1) : '0';
  } else if (k === 'plus' || k === 'minus') {
    // 连加连减：当前输入并入累计，重置输入
    const cur = parseFloat(state.moneyStr) || 0;
    if (calcOp === 'minus') calcAcc -= cur; else calcAcc += cur;
    calcOp = k === 'minus' ? 'minus' : null;
    state.moneyStr = '0';
    // 显示累计反馈
    const el = $('#money-display');
    el.textContent = fmt(calcAcc);
    el.style.color = calcAcc ? '#cc0000' : '#999999';
    return;
  } else if (k === '.') {
    if (!state.moneyStr.includes('.')) state.moneyStr += '.';
  } else {
    if (state.moneyStr === '0') state.moneyStr = k;
    else if (state.moneyStr.replace('.', '').replace('-', '').length < 9) state.moneyStr += k;
  }
  updateMoneyDisplay();
}

function addTx(again = false) {
  // 连加：累计值 + 当前输入
  const input = parseFloat(state.moneyStr) || 0;
  const money = calcAcc + input;
  const sign = state.naKind === 'expense' ? -1 : 1;
  if (!money || !state.naType) {
    if (!money) resetCalc();
    return;
  }
  const remark = $('#note-input').value.trim() || state.naType;
  let group = tx.find(g => g.date === txDate);
  if (!group) { group = { date: txDate, items: [] }; tx.unshift(group); }
  group.items.push({ type: state.naType, remark, money: money * sign, pic: hasPic });
  $('#note-input').value = '';
  calcAcc = 0; calcOp = null; hasPic = false;
  $('#pic-added').hidden = true;
  txDate = '2026-08-18';
  $('#date-label').textContent = '今天';
  resetCalc();
  $('#calc-panel').classList.remove('show');
  if (!again) { state.naType = null; $$('#type-grid .type-cell').forEach(c => c.classList.remove('selected')); }
  renderTxList();
  if (!again) closeOverlay();
}

$('#type-grid').addEventListener('click', (e) => {
  const cell = e.target.closest('.type-cell');
  if (!cell) return;
  $$('#type-grid .type-cell').forEach(c => c.classList.remove('selected'));
  cell.classList.add('selected');
  state.naType = cell.dataset.type;
  // 原版：点击类型后才展开键盘
  $('#calc-panel').classList.add('show');
});

$$('#na-kind-tabs .na-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    $$('#na-kind-tabs .na-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    state.naKind = tab.dataset.kind;
    state.naType = null;
    $('#calc-panel').classList.remove('show');
    renderTypeGrid();
  });
});

$$('.numpad .np-key').forEach(key => {
  key.addEventListener('click', () => pressKey(key.dataset.k));
});

$('#btn-date').addEventListener('click', () => {
  // 点「今天」→ 进入日历，自由选择记账日期
  calPickMode = true;
  state.calYear = 2026; state.calMonth = 8;
  openOverlay('page-calendar');
});

// 图片选择后标记
$$('#pic-sheet .mode-opt').forEach(opt => {
  opt.addEventListener('click', () => {
    hasPic = true;
    $('#pic-added').hidden = false;
    $('#pic-label').textContent = '图片';
  });
});

/* ================= 日历页（周/月/年三视图） ================= */
let calView = 'month'; // month | week | year

function renderCalendar() {
  const y = state.calYear, m = state.calMonth;
  $('#cal-month-label').textContent = calView === 'year' ? `${y}年` : `${y}年${m}月`;
  $$('#cal-view-tabs .cal-view-tab').forEach(t => t.classList.toggle('active', t.dataset.v === calView));
  const grid = $('#cal-grid');
  const weekBar = $('#cal-week');
  const hasTx = {};
  tx.forEach(g => {
    if (g.date.startsWith(`${y}-${String(m).padStart(2, '0')}`)) {
      const d = Number(g.date.split('-')[2]);
      hasTx[d] = (hasTx[d] || 0) + g.items.filter(i => i.money < 0).reduce((s, i) => s - i.money, 0);
    }
  });

  if (calView === 'year') {
    weekBar.style.display = 'none';
    grid.classList.add('year-mode');
    grid.innerHTML = Array.from({ length: 12 }, (_, i) => `
      <div class="year-month-card ${i + 1 === m ? 'active' : ''}" data-m="${i + 1}">${i + 1}月</div>`).join('');
    renderCalList(18);
    return;
  }

  weekBar.style.display = '';
  grid.classList.remove('year-mode');
  const first = new Date(y, m - 1, 1).getDay();
  const days = new Date(y, m, 0).getDate();
  const prevDays = new Date(y, m - 1, 0).getDate();
  const cells = [];

  if (calView === 'week') {
    // 当前周（今天 2026-08-18 所在周）
    const monday = 17; // 2026-08-17 周一
    for (let i = 0; i < 7; i++) {
      const d = monday + i;
      const isToday = d === 18;
      cells.push(`<div class="cal-day ${isToday ? 'today' : ''}" data-d="${d}">
        <span class="d-num">${d}</span>
        ${hasTx[d] ? `<span class="d-dot"></span><span class="d-amt">${hasTx[d]}</span>` : ''}
      </div>`);
    }
  } else {
    for (let i = first - 1; i >= 0; i--) {
      cells.push(`<div class="cal-day other"><span class="d-num">${prevDays - i}</span></div>`);
    }
    for (let d = 1; d <= days; d++) {
      const isToday = d === 18 && m === 8 && y === 2026;
      const cls = ['cal-day'];
      if (isToday) cls.push('today');
      cells.push(`<div class="${cls.join(' ')}" data-d="${d}">
        <span class="d-num">${d}</span>
        ${hasTx[d] ? `<span class="d-dot"></span><span class="d-amt">${hasTx[d]}</span>` : ''}
      </div>`);
    }
    const rest = (7 - (first + days) % 7) % 7;
    for (let i = 1; i <= rest; i++) {
      cells.push(`<div class="cal-day other"><span class="d-num">${i}</span></div>`);
    }
  }
  grid.innerHTML = cells.join('');

  // 账单列表（默认今天）
  renderCalList(18);
}

$('#cal-view-tabs').addEventListener('click', (e) => {
  const tab = e.target.closest('.cal-view-tab');
  if (!tab) return;
  calView = tab.dataset.v;
  renderCalendar();
});

$('#cal-grid').addEventListener('click', (e) => {
  const card = e.target.closest('.year-month-card');
  if (card) {
    state.calMonth = Number(card.dataset.m);
    calView = 'month';
    renderCalendar();
    return;
  }
});

function renderCalList(day) {
  const dateStr = `${state.calYear}-${String(state.calMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  const group = tx.find(g => g.date === dateStr);
  const list = $('#cal-list');
  if (!group) { list.innerHTML = emptyHtml(); return; }
  list.innerHTML = group.items.map(it => `
    <div class="tx-item" style="background:#fff">
      <div class="tx-icon">${icIcon(txIconFile(it.type), 'ic20')}</div>
      <div class="tx-mid">
        <div class="tx-type">${it.type}</div>
        <div class="tx-remark">${it.remark}</div>
      </div>
      <div class="tx-money ${moneyClass(it.money)}">${it.money > 0 ? '+' : '-'}${fmt(Math.abs(it.money))}</div>
    </div>`).join('');
}

$('#cal-grid').addEventListener('click', (e) => {
  const day = e.target.closest('.cal-day');
  if (!day || day.dataset.d === undefined || day.classList.contains('other')) return;
  const d = Number(day.dataset.d);
  // 记账日期选择模式：把选中日期带回记账页
  if (calPickMode) {
    const y = state.calYear, m = state.calMonth;
    txDate = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    $('#date-label').textContent = `${m}月${d}日`;
    calPickMode = false;
    showPage('page-newaccount');
    return;
  }
  $$('#cal-grid .cal-day').forEach(c => c.classList.remove('selected'));
  day.classList.add('selected');
  renderCalList(d);
});

$('#cal-month-btn').addEventListener('click', () => {
  $('#ym-sheet').classList.add('show');
  wYear.select(wheelYears.indexOf(state.calYear));
  wMonth.select(wheelMonths.indexOf(state.calMonth));
  // 日历：确定后切换到所选年月并刷新
  ymOnOk = () => {
    state.calYear = wheelYear;
    state.calMonth = wheelMonth;
    renderCalendar();
  };
});

$('#cal-today').addEventListener('click', () => {
  $$('#cal-grid .cal-day').forEach(c => c.classList.remove('selected'));
  const todayCell = $$('#cal-grid .cal-day').find(c => c.dataset.d === '18');
  if (todayCell) todayCell.classList.add('selected');
  renderCalList(18);
});

$('#cal-add').addEventListener('click', () => openOverlay('page-newaccount'));

/* ================= 搜索页 ================= */
$('#search-tabs').addEventListener('click', (e) => {
  const tab = e.target.closest('.stat-tab');
  if (!tab) return;
  $$('#search-tabs .stat-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  state.searchMode = tab.dataset.st;
});

$('#sort-group').addEventListener('click', (e) => {
  const s = e.target.closest('.period');
  if (!s) return;
  $$('#sort-group .period').forEach(t => t.classList.remove('active'));
  s.classList.add('active');
  state.searchSort = s.dataset.s;
  runSearch();
});

function runSearch() {
  const q = ($('#search-input').value || '').trim().toLowerCase();
  const list = $('#result-list');
  if (!q) { list.innerHTML = ''; return; }
  let items = tx.flatMap(g => g.items.map(it => ({ ...it, date: g.date })));
  items = items.filter(i => i.type.includes(q) || i.remark.toLowerCase().includes(q));
  if (state.searchSort === 'money') items.sort((a, b) => Math.abs(b.money) - Math.abs(a.money));
  else items.sort((a, b) => b.date.localeCompare(a.date));
  list.innerHTML = items.length ? items.map(i => `
    <div class="tx-item" style="background:#fff">
      <div class="tx-icon">${icIcon(txIconFile(i.type), 'ic20')}</div>
      <div class="tx-mid">
        <div class="tx-type">${i.type}</div>
        <div class="tx-remark">${i.remark}</div>
      </div>
      <div class="tx-money ${moneyClass(i.money)}">${i.money > 0 ? '+' : '-'}${fmt(Math.abs(i.money))}</div>
    </div>`).join('') : '<div class="empty-text" style="text-align:center;padding:30px;color:#999">无搜索结果</div>';
}

$('#search-go').addEventListener('click', runSearch);
$('#search-input').addEventListener('input', runSearch);

/* ================= 年度统计 ================= */
function renderYearStat() {
  const items = tx.flatMap(g => g.items);
  const income = items.filter(i => i.money > 0).reduce((s, i) => s + i.money, 0);
  const expense = -items.filter(i => i.money < 0).reduce((s, i) => s + i.money, 0);
  $('#ys-balance').textContent = '¥' + fmt(income - expense);
  $('#ys-income').textContent = '¥' + fmt(income);
  $('#ys-expense').textContent = '¥' + fmt(expense);

  // 按月聚合
  const months = {};
  tx.forEach(g => {
    const key = g.date.slice(0, 7);
    months[key] = months[key] || { income: 0, expense: 0 };
    g.items.forEach(i => {
      if (i.money > 0) months[key].income += i.money;
      else months[key].expense -= i.money;
    });
  });
  $('#year-list').innerHTML = Object.entries(months).sort((a, b) => b[0].localeCompare(a[0])).map(([m, v]) => `
    <div class="ym-row">
      <span class="ym-name">${m.replace('-', '年')}月</span>
      <span class="ym-cell in">${fmt(v.income)}</span>
      <span class="ym-cell">${fmt(v.expense)}</span>
      <span class="ym-cell">${fmt(v.income - v.expense)}</span>
    </div>`).join('');
}

/* ================= 管理账本 ================= */
function renderBooks() {
  $('#book-list').innerHTML = books.map((b, i) => `
    <div class="book-item ${i === state.selectedBook ? 'checked' : ''}" data-i="${i}">
      <div class="book-icon">${icIcon(b.icon, 'ic22')}</div>
      <div class="book-info"><div class="book-name">${b.name}</div><div class="book-desc">${b.type} · 2026年创建</div></div>
      <div class="book-check"></div>
    </div>`).join('');
}

$('#book-list').addEventListener('click', (e) => {
  const item = e.target.closest('.book-item');
  if (!item) return;
  switchBook(Number(item.dataset.i));
});

/* ================= 类别管理 ================= */
function renderTypeMgr() {
  $('#type-mgr-list').innerHTML = TYPES[state.naKind].map(t => `
    <div class="type-mgr-item">
      <div class="t-icon">${icIcon(t.icon, 'ic20')}</div>
      <span class="type-mgr-name">${t.name}</span>
      <span class="cell-arrow">›</span>
    </div>`).join('');
}

$('#type-mgr-tabs').addEventListener('click', (e) => {
  const tab = e.target.closest('.na-tab');
  if (!tab) return;
  $$('#type-mgr-tabs .na-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  state.naKind = tab.dataset.kind;
  renderTypeMgr();
});

/* ================= 我的页 ================= */
$('#btn-login').addEventListener('click', () => {
  const nickname = $('#nickname');
  nickname.textContent = nickname.textContent === '点击登录' ? '简约用户' : '点击登录';
  $('#pi-nickname').textContent = $('#nickname').textContent;
});

$$('#page-profile .cell[data-nav]').forEach(cell => {
  cell.addEventListener('click', () => {
    const nav = cell.dataset.nav;
    const map = {
      vip: 'page-vip', types: 'page-types', sync: 'page-backup',
      settings: 'page-setting', export: 'page-vip',
      gesture: 'page-gesture', theme: 'page-theme',
      about: 'page-about',
    };
    if (nav === 'export') { toast('Excel 导出功能（演示）'); return; }
    if (nav === 'widget') { $('#widget-sheet').classList.add('show'); return; }
    if (nav === 'gesture') { openOverlay('page-gesture'); return; }
    if (map[nav]) openOverlay(map[nav]);
  });
});

/* ================= 小部件设置弹窗 ================= */
$$('#widget-sheet .wr-choice').forEach(c => {
  c.addEventListener('click', () => {
    $$(`#widget-sheet .wr-choice[data-k="${c.dataset.k}"]`).forEach(x => x.classList.remove('active'));
    c.classList.add('active');
  });
});
$('#widget-trans').addEventListener('click', function () { this.classList.toggle('on'); });
$('#widget-cancel').addEventListener('click', () => $('#widget-sheet').classList.remove('show'));

/* ================= 选择主账本弹窗 ================= */
function renderMainbook() {
  $('#mainbook-list').innerHTML = books.map((b, i) => `
    <div class="sheet-book-item ${i === 0 ? 'checked' : ''}" data-i="${i}">
      <span class="cell-icon">${icIcon(b.icon, 'ic20')}</span>
      <span>${b.name}</span>
    </div>`).join('');
}
$('#btn-merge').addEventListener('click', () => {
  renderMainbook();
  $('#mainbook-sheet').classList.add('show');
});
$('#mainbook-list').addEventListener('click', (e) => {
  const item = e.target.closest('.sheet-book-item');
  if (!item) return;
  $$('#mainbook-list .sheet-book-item').forEach(x => x.classList.remove('checked'));
  item.classList.add('checked');
  toast('主账本已设置');
  setTimeout(() => $('#mainbook-sheet').classList.remove('show'), 500);
});
$('#mainbook-cancel').addEventListener('click', () => $('#mainbook-sheet').classList.remove('show'));

/* ================= 下载进度弹窗（检查更新） ================= */
let downloadTimer = null;
function startDownload() {
  $('#download-sheet').classList.add('show');
  let pct = 0;
  $('#download-fill').style.width = '0%';
  $('#download-pct').textContent = '0%';
  clearInterval(downloadTimer);
  downloadTimer = setInterval(() => {
    pct += Math.random() * 18 + 4;
    if (pct >= 100) {
      pct = 100;
      clearInterval(downloadTimer);
      $('#download-pct').textContent = '100%';
      toast('下载完成，请点击安装');
      setTimeout(() => $('#download-sheet').classList.remove('show'), 800);
    }
    $('#download-fill').style.width = pct + '%';
    $('#download-pct').textContent = Math.floor(pct) + '%';
  }, 300);
}
$('#download-cancel').addEventListener('click', () => {
  clearInterval(downloadTimer);
  $('#download-sheet').classList.remove('show');
  toast('已取消下载');
});

/* ================= 通用消息确认弹窗 ================= */
let msgOkHandler = null;
function confirmMsg(title, body, onOk) {
  $('#msg-title').textContent = title;
  $('#msg-body').textContent = body;
  msgOkHandler = onOk;
  $('#msg-sheet').classList.add('show');
}
$('#msg-ok').addEventListener('click', () => {
  $('#msg-sheet').classList.remove('show');
  if (msgOkHandler) msgOkHandler();
});
$('#msg-cancel').addEventListener('click', () => $('#msg-sheet').classList.remove('show'));

/* 账单列表项点击 → 详情 */
$('#tx-list').addEventListener('click', (e) => {
  const item = e.target.closest('.tx-item');
  if (!item) return;
  const groupEl = item.closest('.tx-group');
  const groups = $$('#tx-list .tx-group');
  const gi = groups.indexOf(groupEl);
  const items = $$('#tx-list .tx-group')[gi] ? $$('#tx-list .tx-group')[gi].querySelectorAll('.tx-item') : [];
  const ii = Array.from(items).indexOf(item);
  const date = tx[gi] && tx[gi].date;
  if (date !== undefined) openDetail(date, ii);
});

/* ================= 主页按钮 ================= */
$('#fab-add').addEventListener('click', () => {
  state.naKind = 'expense'; state.naType = null; resetCalc();
  calcAcc = 0; calcOp = null; txDate = '2026-08-18'; hasPic = false;
  $('#date-label').textContent = '今天';
  $('#pic-added').hidden = true;
  $('#calc-panel').classList.remove('show');
  $$('#na-kind-tabs .na-tab').forEach(t => t.classList.toggle('active', t.dataset.kind === 'expense'));
  renderTypeGrid();
  openOverlay('page-newaccount');
});
$('#btn-book').addEventListener('click', () => openBookSheet());
$('#btn-search').addEventListener('click', () => openOverlay('page-search'));
$('#btn-calendar').addEventListener('click', () => openOverlay('page-calendar'));
$('#btn-report').addEventListener('click', () => { renderYearStat(); openOverlay('page-yearstat'); });
$('#na-back').addEventListener('click', closeOverlay);
$('#na-manage').addEventListener('click', () => openOverlay('page-types'));
$('#btn-books-cancel').addEventListener('click', closeOverlay);
$('#btn-merge').addEventListener('click', () => {});
$('#btn-new-type').addEventListener('click', () => openOverlay('page-newtype'));
$('#btn-import-type').addEventListener('click', () => {});
$('#btn-newtype-save').addEventListener('click', () => {
  const name = $('#newtype-name').value.trim();
  if (!name) return;
  TYPES[state.naKind].push({ name, icon: 'cate_more.png', custom: true });
  $('#newtype-name').value = '';
  renderTypeMgr();
  renderTypeGrid();
  closeOverlay();
});
$('#btn-book-save').addEventListener('click', saveEditBook);

/* ================= 账单详情（res_xv） ================= */
let detailTx = null;

function openDetail(date, idx) {
  const group = tx.find(g => g.date === date);
  const item = group && group.items[idx];
  if (!item) return;
  detailTx = { date, idx };
  const sign = item.money < 0;
  $('#detail-money').textContent = (sign ? '-' : '+') + fmt(Math.abs(item.money));
  $('#detail-money').className = 'detail-money' + (sign ? '' : ' income');
  $('#detail-type-name').textContent = item.type;
  $('#detail-type-ic').setAttribute('style', '--mask:url(assets/icons/' + txIconFile(item.type) + ')');
  const [y, m, d] = date.split('-');
  $('#detail-date').textContent = `${y}年${m}月${d}日`;
  $('#detail-remark').textContent = item.remark;
  $('#detail-pic-row').hidden = true;
  openOverlay('page-detail');
}

$('#detail-del').addEventListener('click', () => {
  if (!detailTx) return;
  const g = tx.find(x => x.date === detailTx.date);
  g.items.splice(detailTx.idx, 1);
  if (!g.items.length) tx = tx.filter(x => x !== g);
  toast('已删除');
  renderTxList();
  closeOverlay();
});

$('#detail-edit').addEventListener('click', () => {
  const g = tx.find(x => x.date === detailTx.date);
  const item = g.items[detailTx.idx];
  state.naKind = item.money < 0 ? 'expense' : 'income';
  state.naType = item.type;
  state.moneyStr = String(Math.abs(item.money));
  $('#note-input').value = item.remark;
  $$('#na-kind-tabs .na-tab').forEach(t => t.classList.toggle('active', t.dataset.kind === state.naKind));
  renderTypeGrid();
  $$('#type-grid .type-cell').forEach(c => c.classList.toggle('selected', c.dataset.type === item.type));
  updateMoneyDisplay();
  // 删除旧账再记账
  g.items.splice(detailTx.idx, 1);
  if (!g.items.length) tx = tx.filter(x => x !== g);
  renderTxList();
  $('#calc-panel').classList.add('show');
  openOverlay('page-newaccount');
});

/* ================= 账单统计（res_z9） ================= */
const billStatPeriod = { p: 'week', tab: 0 };

function renderBillStat() {
  const bar = $('#billstat-periods-bar');
  const labels = billStatPeriod.p === 'week'
    ? ['08-12', '08-13', '08-14', '08-15', '08-16', '08-17', '08-18']
    : billStatPeriod.p === 'month' ? ['8月', '9月', '10月', '11月', '12月', '1月'] : ['2026', '2025', '2024'];
  bar.innerHTML = labels.map((l, i) => `<span class="pb-item ${i === 0 ? 'active' : ''}" data-i="${i}">${l}</span>`).join('');

  const items = tx.flatMap(g => g.items.map(it => ({ ...it, date: g.date })));
  // 柱状图：按周期聚合
  const n = labels.length;
  const buckets = Array(n).fill(0);
  items.forEach(i => {
    if (i.money > 0) return; // 账单统计显示支出
    const d = new Date(i.date.replace(/-/g, '/'));
    let idx;
    if (billStatPeriod.p === 'week') idx = (d.getDay() + 6) % 7;
    else if (billStatPeriod.p === 'month') idx = 0;
    else idx = 2;
    if (idx < n) buckets[idx] += Math.abs(i.money);
  });
  const max = Math.max(...buckets, 1);
  const W = 340, H = 130, padB = 18, padT = 8, bw = W / n;
  const bars = buckets.map((v, i) => {
    const h = Math.max(2, (v / max) * (H - padB - padT));
    const x = i * bw + bw / 2 - 10;
    const y = H - padB - h;
    return `<rect x="${x}" y="${y}" width="20" height="${h}" rx="3" fill="${i === n - 1 ? '#303f9f' : '#9aa0d6'}"/>`;
  }).join('');
  $('#billstat-chart').innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${bars}</svg>`;

  // 账单列表（支出明细，按日期倒序）
  const list = items.filter(i => i.money < 0).sort((a, b) => b.date.localeCompare(a.date));
  $('#billstat-list').innerHTML = list.map(i => `
    <div class="tx-item" style="background:#fff">
      <div class="tx-icon">${icIcon(txIconFile(i.type), 'ic20')}</div>
      <div class="tx-mid">
        <div class="tx-type">${i.type}</div>
        <div class="tx-remark">${i.remark}</div>
      </div>
      <div class="tx-money">-${fmt(Math.abs(i.money))}</div>
    </div>`).join('') || emptyHtml();
  const total = list.reduce((s, i) => s + Math.abs(i.money), 0);
  $('#billstat-tot').textContent = '合计: ¥' + fmt(total);
}

$('#billstat-period-group').addEventListener('click', (e) => {
  const p = e.target.closest('.period');
  if (!p) return;
  $$('#billstat-period-group .period').forEach(t => t.classList.remove('active'));
  p.classList.add('active');
  billStatPeriod.p = p.dataset.p;
  renderBillStat();
});

/* ================= 图表页（res_lC 横向柱状+饼图） ================= */
const chartState = { cat: 'expense' };

function renderHBar(container, items) {
  // 横向收支对比：收入 vs 支出 两个条
  const income = items.filter(i => i.money > 0).reduce((s, i) => s + i.money, 0);
  const expense = -items.filter(i => i.money < 0).reduce((s, i) => s + i.money, 0);
  const max = Math.max(income, expense, 1);
  const W = 340, H = 50;
  const bw = (w) => Math.max(6, (w / max) * (W - 70));
  container.innerHTML = `<svg viewBox="0 0 ${W} ${H}">
    <rect x="45" y="6" width="${bw(income)}" height="15" rx="3" fill="#303f9f"/>
    <text x="40" y="19" text-anchor="end" font-size="11" fill="#666">收入</text>
    <text x="${50 + bw(income)}" y="19" font-size="11" fill="#303f9f">${fmt(income)}</text>
    <rect x="45" y="28" width="${bw(expense)}" height="15" rx="3" fill="#ee6c8c"/>
    <text x="40" y="41" text-anchor="end" font-size="11" fill="#666">支出</text>
    <text x="${50 + bw(expense)}" y="41" font-size="11" fill="#ee6c8c">${fmt(expense)}</text>
  </svg>`;
}

function renderPieTo(container, listContainer, items, title) {
  const map = {};
  items.forEach(i => { map[i.type] = (map[i.type] || 0) + Math.abs(i.money); });
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, e) => s + e[1], 0);
  if (!total) {
    if (container.__psec) { container.__psec = null; container.innerHTML = ''; }
    listContainer.innerHTML = emptyHtml();
    return;
  }
  const cx = 195, cy = 105, r = 70; // 整块 .pie-canvas（390×210）都是轮盘显示区，viewBox 与容器 1:1
  const rot = pieRotation(container);
  const deg = rot * 180 / Math.PI;
  let angle = -Math.PI / 2;
  const arcs = entries.map((e, i) => {
    const frac = e[1] / total;
    const a0 = angle;
    angle += frac * Math.PI * 2;
    return { name: e[0], val: e[1], idx: i, frac, a0, a1: angle, fill: PIE_COLORS[i % PIE_COLORS.length] };
  });
  const shown = arcs.filter(a => a.frac >= 0.02);

  // —— 首次构建 SVG 骨架（之后仅更新属性/局部组，避免重建晃动）——
  if (!container.__psec) {
    container.innerHTML = `<svg viewBox="0 0 390 210">
      <g class="psec"></g>
      <g class="plbl"></g>
      <circle class="phole" fill="#f0f1f6"/>
      <text class="pamt" text-anchor="middle" font-size="14" fill="#666"></text>
      <text class="pcat" text-anchor="middle" font-size="11" fill="#999"></text>
    </svg>`;
    container.__psec = container.querySelector('.psec');
    container.__plbl = container.querySelector('.plbl');
    const hole = container.querySelector('.phole');
    hole.setAttribute('cx', cx); hole.setAttribute('cy', cy); hole.setAttribute('r', 34);
    container.__pamt = container.querySelector('.pamt');
    container.__pcat = container.querySelector('.pcat');
    container.__pamt.setAttribute('x', cx); container.__pamt.setAttribute('y', cy - 4);
    container.__pcat.setAttribute('x', cx); container.__pcat.setAttribute('y', cy + 14);
  }

  // —— 扇区：仅在类别集合变化时重建 path，旋转只更新 transform ——
  const key = shown.map(a => a.name).join('|');
  if (container.__psecKey !== key) {
    const GAP = 0.022; // 色块之间小留白
    container.__psec.innerHTML = shown.map(a => {
      const a0 = a.a0 + GAP / 2, a1 = a.a1 - GAP / 2;
      const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
      const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
      return `<path d="M${cx},${cy} L${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 ${a.frac > 0.5 ? 1 : 0} 1 ${x1.toFixed(1)},${y1.toFixed(1)} Z" fill="${a.fill}"/>`;
    }).join('');
    container.__psecKey = key;
  }
  container.__psec.setAttribute('transform', `rotate(${deg.toFixed(3)} ${cx} ${cy})`);

  // —— 标注（<2% 不显示）：位置跟随 rot，文字保持水平 ——
  container.__plbl.innerHTML = shown.map(a => {
    const mid = (a.a0 + a.a1) / 2 + rot;
    const c = Math.cos(mid), s = Math.sin(mid);
    const right = c >= 0;
    const bx = cx + c * (r + 4), by = cy + s * (r + 4);     // 圆点（扇区外沿）
    const ox = cx + c * (r + 15), oy = cy + s * (r + 15);   // 折点
    const pct = (a.frac * 100).toFixed(1) + '%';
    const txt = a.name + ' ' + pct;
    const w = a.name.length * 9.5 + pct.length * 4.8 + 2;   // 估算文字宽
    const hlen = w * 2 / 3;                                  // 横向延长线（减少 1/3）
    const cgap = 10;                                         // 与数字留一个字符空隙
    const hx = right ? ox + hlen : ox - hlen;                // 水平横线终点
    const tx = right ? hx + cgap : hx - cgap;                // 文字起点
    return `<circle cx="${bx.toFixed(1)}" cy="${by.toFixed(1)}" r="2.5" fill="${a.fill}"/>` +
      `<line x1="${bx.toFixed(1)}" y1="${by.toFixed(1)}" x2="${ox.toFixed(1)}" y2="${oy.toFixed(1)}" stroke="${a.fill}" stroke-width="1.2"/>` +
      `<line x1="${ox.toFixed(1)}" y1="${oy.toFixed(1)}" x2="${hx.toFixed(1)}" y2="${oy.toFixed(1)}" stroke="${a.fill}" stroke-width="1.2"/>` +
      `<text x="${tx.toFixed(1)}" y="${oy.toFixed(1)}" text-anchor="${right ? 'start' : 'end'}" dominant-baseline="middle" font-size="9.5" fill="${a.fill}" font-weight="500">${txt}</text>`;
  }).join('');

  // 中心文字
  container.__pamt.textContent = fmt(total);
  container.__pcat.textContent = title;
  listContainer.innerHTML = arcs.map(a => {
    const pct = a.frac * 100;
    return `<div class="stat-item">
      <span class="stat-ic" style="color:${a.fill}"><i class="ic ic16" style="--mask:url(assets/icons/${txIconFile(a.name)})"></i></span>
      <span class="stat-name">${a.name}</span>
      <span class="stat-amt">${fmt(a.val)}</span>
      <span class="stat-pct">${pct >= 2 ? pct.toFixed(1) + '%' : ''}</span>
    </div>`;
  }).join('');
}

function chartItems() {
  const sign = chartState.cat === 'expense' ? -1 : 1;
  return tx.flatMap(g => g.items.map(it => ({ ...it, date: g.date }))).filter(i => Math.sign(i.money) === sign);
}

function renderChartPage() {
  renderHBar($('#chart-hbar'), tx.flatMap(g => g.items));
  renderPieTo($('#chart-pie'), $('#chart-list'), chartItems(), chartState.cat === 'expense' ? '支出' : '收入');
}

// 饼图旋转绑定（三个饼图各自独立旋转）
bindPieRotation($('#pie-chart'), renderPie);
bindPieRotation($('#chart-pie'), () => renderPieTo($('#chart-pie'), $('#chart-list'), chartItems(), chartState.cat === 'expense' ? '支出' : '收入'));
bindPieRotation($('#customstat-pie'), () => {
  const all = tx.flatMap(g => g.items.map(it => ({ ...it, date: g.date })));
  const items = customState.cat === 'expense' ? all.filter(i => i.money < 0) : all.filter(i => i.money > 0);
  renderPieTo($('#customstat-pie'), $('#customstat-list'), items, customState.cat === 'expense' ? '支出' : '收入');
});

$('#chart-tabs').addEventListener('click', (e) => {
  const tab = e.target.closest('.stat-tab');
  if (!tab) return;
  $$('#chart-tabs .stat-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  chartState.cat = tab.dataset.cat;
  renderChartPage();
});

/* ================= 自定义统计（res_sC） ================= */
const customState = { cat: 'expense' };

function renderCustomStat() {
  renderHBar($('#customstat-hbar'), tx.flatMap(g => g.items));
  const all = tx.flatMap(g => g.items.map(it => ({ ...it, date: g.date })));
  const items = customState.cat === 'expense' ? all.filter(i => i.money < 0) : all.filter(i => i.money > 0);
  // 纵向柱状图：按月聚合
  const months = {};
  items.forEach(i => {
    const key = i.date.slice(5, 7) + '月';
    months[key] = (months[key] || 0) + Math.abs(i.money);
  });
  const keys = Object.keys(months).slice(0, 6);
  const vals = keys.map(k => months[k]);
  const max = Math.max(...vals, 1);
  const W = 340, H = 130, padB = 18, bw = W / Math.max(keys.length, 1);
  const bars = vals.map((v, i) => {
    const h = Math.max(2, (v / max) * (H - padB - 8));
    const x = i * bw + bw / 2 - 10;
    return `<rect x="${x}" y="${H - padB - h}" width="20" height="${h}" rx="3" fill="#9aa0d6"/>`;
  }).join('');
  $('#customstat-vbar').innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${bars}</svg>`;
  renderPieTo($('#customstat-pie'), $('#customstat-list'), items, customState.cat === 'expense' ? '支出' : '收入');
}

$('#customstat-tabs').addEventListener('click', (e) => {
  const tab = e.target.closest('.stat-tab');
  if (!tab) return;
  $$('#customstat-tabs .stat-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  customState.cat = tab.dataset.cat;
  renderCustomStat();
});

/* ================= 导入类别（res_f7） ================= */
const IMPORT_PRESETS = [
  { name: '旅行', icon: 'ic_plane.png' }, { name: '宠物', icon: 'cate_dog.png' },
  { name: '宝贝', icon: 'cate_baby.png' }, { name: '保险', icon: 'cate_insurance.png' },
  { name: '公园', icon: 'cate_park.png' }, { name: '酒水', icon: 'cate_wine.png' },
  { name: '主食', icon: 'cate_rice.png' }, { name: '烟酒', icon: 'cate_smoking.png' },
  { name: '加油', icon: 'cate_refuel.png' }, { name: '外卖', icon: 'cate_delivery.png' },
  { name: '家具', icon: 'cate_furniture.png' }, { name: '水电', icon: 'cate_electricity.png' },
  { name: '电器', icon: 'cate_fridge.png' }, { name: '办公', icon: 'cate_paper.png' },
  { name: '健身', icon: 'cate_dumbell.png' }, { name: '礼物', icon: 'cate_gift.png' },
  { name: '长辈', icon: 'cate_oldman.png' }, { name: '借出', icon: 'cate_borrow.png' },
];
let importSelected = new Set();

function renderImport() {
  $('#import-list').innerHTML = IMPORT_PRESETS.map((t, i) => `
    <div class="import-item ${importSelected.has(i) ? 'checked' : ''}" data-i="${i}">
      <div class="book-icon">${icIcon(t.icon, 'ic20')}</div>
      <span class="type-mgr-name">${t.name}</span>
      <div class="import-check"></div>
    </div>`).join('');
}

$('#import-list').addEventListener('click', (e) => {
  const item = e.target.closest('.import-item');
  if (!item) return;
  const i = Number(item.dataset.i);
  if (importSelected.has(i)) importSelected.delete(i); else importSelected.add(i);
  item.classList.toggle('checked');
});

$('#import-all').addEventListener('click', () => {
  importSelected = new Set(IMPORT_PRESETS.map((_, i) => i));
  renderImport();
});
$('#import-reset').addEventListener('click', () => {
  importSelected = new Set();
  renderImport();
});
$('#import-go').addEventListener('click', () => {
  let count = 0;
  importSelected.forEach(i => {
    if (!TYPES.expense.some(t => t.name === IMPORT_PRESETS[i].name)) {
      TYPES.expense.push({ ...IMPORT_PRESETS[i] });
      count++;
    }
  });
  toast(`已导入 ${count} 个类别`);
  renderTypeMgr();
  closeOverlay();
});

/* ================= 登录 / 用户中心 ================= */
let loggedIn = false;

function updateLoginUI() {
  $('#nickname').textContent = loggedIn ? '简约用户' : '点击登录';
  $('#vip-status').textContent = loggedIn ? '普通会员' : '未开通会员';
  $('#vipflag').hidden = !loggedIn;
  $('#pi-nickname').textContent = $('#nickname').textContent;
  $('#pi-vip').textContent = $('#vip-status').textContent;
  $('#uc-nickname').textContent = $('#nickname').textContent;
  $('#uc-vip').textContent = $('#vip-status').textContent;
}

$('#login-go').addEventListener('click', () => {
  const mobile = $('#login-mobile').value.trim();
  const pwd = $('#login-pwd').value;
  if (!/^1\d{10}$/.test(mobile)) { toast('手机号格式不正确'); return; }
  if (pwd.length < 6) { toast('密码格式不正确'); return; }
  loggedIn = true;
  updateLoginUI();
  toast('登录成功');
  closeOverlay();
});
$('#login-wechat').addEventListener('click', () => {
  loggedIn = true;
  updateLoginUI();
  toast('微信登录成功');
  closeOverlay();
});
$('#login-register').addEventListener('click', () => toast('请通过注册页面完成注册'));
$('#login-forgot').addEventListener('click', () => toast('请通过手机验证码找回密码'));

$('#btn-login').addEventListener('click', () => {
  if (loggedIn) openOverlay('page-usercenter');
  else openOverlay('page-login');
});
$('#profile-head').addEventListener('click', (e) => {
  if (e.target.closest('#btn-login')) return;
  if (loggedIn) openOverlay('page-usercenter');
  else openOverlay('page-login');
});
$('#uc-logout').addEventListener('click', () => {
  confirmMsg('提示', '是否确定退出登录？', () => {
    loggedIn = false;
    updateLoginUI();
    toast('已退出登录');
    closeOverlay();
  });
});
$('#uc-unregister').addEventListener('click', () => {
  confirmMsg('确定注销', '注销后账号的所有信息将从服务端删除，包括个人资料、云备份数据，且无法恢复，请谨慎操作', () => {
    loggedIn = false;
    updateLoginUI();
    toast('账号已成功注销');
    closeOverlay();
  });
});

/* ================= 修改手机号/密码（复用表单） ================= */
$$('#page-usercenter .uc-row[data-form]').forEach(row => {
  row.addEventListener('click', () => {
    const kind = row.dataset.form;
    const isPwd = kind === 'pwd';
    $('#authform-title').textContent = isPwd ? '修改密码' : '修改手机号';
    $('#authform-card').innerHTML = isPwd ? `
      <div class="form-row"><span class="form-label">旧密码</span><input class="form-input" id="af-old" type="password" placeholder="输入旧密码"></div>
      <div class="form-row"><span class="form-label">新密码</span><input class="form-input" id="af-new" type="password" placeholder="输入新密码"></div>
    ` : `
      <div class="form-row"><span class="form-label">新手机号</span><input class="form-input" id="af-new" type="tel" placeholder="输入新手机号"></div>
      <div class="form-row"><span class="form-label">验证码</span><input class="form-input" id="af-old" placeholder="输入验证码"></div>
    `;
    openOverlay('page-authform');
  });
});
$('#authform-save').addEventListener('click', () => {
  const val = $('#af-new') && $('#af-new').value.trim();
  if (!val) { toast('输入不能为空'); return; }
  toast('修改成功');
  closeOverlay();
});

/* ================= 云备份 ================= */
$('#backup-now').addEventListener('click', () => {
  const log = $('#backup-log');
  log.style.display = 'block';
  log.textContent = '正在备份…';
  setTimeout(() => {
    log.textContent = `备份成功 ${new Date().toLocaleString()} · 共 ${tx.flatMap(g => g.items).length} 笔账单`;
    toast('备份成功');
  }, 800);
});
$('#backup-restore').addEventListener('click', () => {
  const log = $('#backup-log');
  log.style.display = 'block';
  log.textContent = '正在恢复…';
  setTimeout(() => {
    log.textContent = '恢复成功，数据已还原';
    toast('恢复成功');
  }, 800);
});
$('#backup-auto-sw').addEventListener('click', function () { this.classList.toggle('on'); });

/* ================= 主题设置（8 主题） ================= */
const THEMES = [
  { name: '靛蓝主题', color: '#303f9f' }, { name: '墨黑主题', color: '#303030' },
  { name: '棕褐主题', color: '#753c2c' }, { name: '樱花粉主题', color: '#ee6c8c' },
  { name: '活力橙主题', color: '#d2691e' }, { name: '砖红主题', color: '#a52a2a' },
  { name: '神秘紫主题', color: '#8b008b' }, { name: '森林绿主题', color: '#008000' },
];
let currentTheme = 0;

function renderThemes() {
  $('#theme-list').innerHTML = THEMES.map((t, i) => `
    <div class="theme-item ${i === currentTheme ? 'active' : ''}" data-i="${i}">
      <div class="theme-swatch" style="background:${t.color}"></div>
      <span class="theme-name">${t.name}</span>
      <span class="theme-check">${i === currentTheme ? '✓' : ''}</span>
    </div>`).join('');
}

$('#theme-list').addEventListener('click', (e) => {
  const item = e.target.closest('.theme-item');
  if (!item) return;
  currentTheme = Number(item.dataset.i);
  const color = THEMES[currentTheme].color;
  document.documentElement.style.setProperty('--primary', color);
  document.documentElement.style.setProperty('--text-primary', color);
  renderThemes();
});

/* ================= 关于 / 更多作品 ================= */
$$('#page-about .about-row').forEach(row => {
  row.addEventListener('click', () => {
    const map = {
      update: null, praise: '感谢您的支持！',
      share: '已复制分享链接', privacy: '隐私政策页面（演示）',
      agreement: '用户协议页面（演示）', permission: '请在系统设置中管理权限',
      contact: '客服邮箱: service@yhqxsoft.com',
    };
    const key = row.dataset.a;
    if (key === 'more') { openOverlay('page-moreapps'); return; }
    if (key === 'update') { ABOUT_ACTIONS.update(); return; }
    toast(map[key] || '功能演示');
  });
});

function renderMoreApps() {
  $('#moreapps-list').innerHTML = ['旅行记账', '宝宝成长记', '家庭账本'].map((n, i) => `
    <div class="moreapp-item">
      <div class="moreapp-icon">${icIcon(['ic_plane.png', 'cate_baby.png', 'ic_book.png'][i], 'ic24')}</div>
      <span class="moreapp-name">${n}</span>
      <span class="cell-arrow">›</span>
    </div>`).join('');
}

/* ================= 手势密码（完整流程：绘制→确认→找回） ================= */
let gesturePwd = [], gestureInput = [], gestureDrawing = false;
let gestureStage = 'draw'; // draw | confirm | done

function gestureHintText() {
  if (gestureStage === 'draw') return gesturePwd.length ? '绘制解锁图案' : '绘制解锁图案，请至少连接4个点';
  if (gestureStage === 'confirm') return '再次绘制图案进行确认';
  return '解锁图案已设置';
}

function renderGesturePad() {
  const svg = $('#gesture-pad');
  let dots = '', lines = '';
  const pts = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) pts.push({ x: 75 + c * 75, y: 75 + r * 75, i: r * 3 + c });
  dots = pts.map(p => `<circle class="g-dot ${gestureInput.includes(p.i) ? 'on' : ''}" cx="${p.x}" cy="${p.y}" r="12" data-i="${p.i}"/>`).join('');
  if (gestureInput.length > 1) {
    lines = gestureInput.slice(0, -1).map((a, k) => {
      const p1 = pts[a], p2 = pts[gestureInput[k + 1]];
      return `<line class="g-line" x1="${p1.x}" y1="${p1.y}" x2="${p2.x}" y2="${p2.y}"/>`;
    }).join('');
  }
  if (gestureInput.length) {
    const last = pts[gestureInput[gestureInput.length - 1]];
    lines += `<circle class="g-ring" cx="${last.x}" cy="${last.y}" r="22"/>`;
  }
  svg.innerHTML = lines + dots;
  $('#gesture-hint').textContent = gestureHintText();
}

function gesturePoint(e) {
  const rect = $('#gesture-pad').getBoundingClientRect();
  const x = (e.clientX - rect.left) / rect.width * 300;
  const y = (e.clientY - rect.top) / rect.height * 300;
  let best = -1, bestD = 40 * 40;
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const dx = x - (75 + c * 75), dy = y - (75 + r * 75);
    const d = dx * dx + dy * dy;
    if (d < bestD) { bestD = d; best = r * 3 + c; }
  }
  return best;
}

$('#gesture-pad').addEventListener('pointerdown', (e) => {
  if (gestureStage === 'done') { gestureStage = 'draw'; gesturePwd = []; }
  gestureDrawing = true;
  gestureInput = [];
  const p = gesturePoint(e);
  if (p >= 0) gestureInput.push(p);
  renderGesturePad();
});
$('#gesture-pad').addEventListener('pointermove', (e) => {
  if (!gestureDrawing) return;
  const p = gesturePoint(e);
  if (p >= 0 && !gestureInput.includes(p)) gestureInput.push(p);
  renderGesturePad();
});
$('#gesture-pad').addEventListener('pointerup', () => {
  gestureDrawing = false;
  if (!gestureInput.length) return;
  if (gestureInput.length < 4) {
    $('#gesture-hint').textContent = '至少需连接4个点，请重试';
    gestureInput = [];
    setTimeout(renderGesturePad, 500);
    return;
  }
  if (gestureStage === 'draw') {
    gesturePwd = [...gestureInput];
    gestureStage = 'confirm';
    $('#gesture-hint').textContent = '您的新解锁图案';
    gestureInput = [];
    setTimeout(renderGesturePad, 400);
  } else if (gestureStage === 'confirm') {
    if (gesturePwd.join() === gestureInput.join()) {
      gestureStage = 'done';
      $('#gesture-hint').textContent = '解锁图案已设置';
      toast('手势密码设置成功');
      gestureInput = [];
      renderGesturePad();
    } else {
      $('#gesture-hint').textContent = '两次绘制的图案不一致，请重试';
      gesturePwd = [];
      gestureStage = 'draw';
      gestureInput = [];
      setTimeout(renderGesturePad, 600);
    }
  }
});
$('#gesture-reset').addEventListener('click', () => {
  gesturePwd = []; gestureInput = []; gestureStage = 'draw';
  renderGesturePad();
});
$('#gesture-forgot').addEventListener('click', () => {
  toast('原解锁图案已删除');
  openOverlay('page-forgot');
});

/* ================= 指纹验证 ================= */
$('#finger-ring').addEventListener('click', () => {
  $('#finger-hint').textContent = '验证中…';
  setTimeout(() => {
    $('#finger-hint').textContent = '验证成功';
    toast('指纹验证成功');
    setTimeout(closeOverlay, 600);
  }, 900);
});

/* 「指纹加密保护」cell 点击 → 指纹验证页 */
$$('#page-profile .cell').forEach(c => {
  if (c.querySelector('[style*="menu_finger"]')) {
    c.addEventListener('click', () => openOverlay('page-finger'));
  }
});

/* ================= Toast ================= */
let toastEl = null;
function toast(msg) {
  if (!toastEl) {
    toastEl = document.createElement('div');
    toastEl.className = 'toast';
    document.body.appendChild(toastEl);
  }
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => toastEl.classList.remove('show'), 1800);
}

/* ================= 统计页入口更新 ================= */
function openBillStat() { renderBillStat(); openOverlay('page-billstat'); }
function openChartPage() { renderChartPage(); openOverlay('page-chart'); }
function openCustomStat() { renderCustomStat(); openOverlay('page-customstat'); }

$('#chart-more').addEventListener('click', () => openCustomStat());

/* ================= 结余趋势（ChartView） ================= */
const balanceState = { kind: 'inout' };

function renderBalance() {
  const items = tx.flatMap(g => g.items.map(it => ({ ...it, date: g.date })));
  const W = 340, H = 170, padB = 20, padT = 10, padL = 34;
  // 按月聚合
  const months = {};
  items.forEach(i => {
    const key = i.date.slice(5, 7) + '月';
    months[key] = months[key] || { income: 0, expense: 0 };
    if (i.money > 0) months[key].income += i.money;
    else months[key].expense -= i.money;
  });
  const keys = Object.keys(months).sort();
  const maxV = Math.max(...keys.map(k => Math.max(months[k].income, months[k].expense)), 1);
  const x = (i) => padL + (W - padL - 8) * (i / Math.max(keys.length - 1, 1));
  const y = (v) => H - padB - (v / maxV) * (H - padB - padT);
  // 网格
  let grid = '';
  for (let g = 0; g <= 4; g++) {
    const gy = padT + (H - padB - padT) * g / 4;
    grid += `<line x1="${padL}" y1="${gy}" x2="${W - 6}" y2="${gy}" stroke="#eeeeee" stroke-width="1"/>`;
  }
  const linePath = (field, color) => keys.map((k, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(months[k][field]).toFixed(1)}`).join(' ');
  const areaPath = (field, color) => {
    let d = keys.map((k, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(months[k][field]).toFixed(1)}`).join(' ');
    d += `L${x(keys.length - 1).toFixed(1)},${H - padB}L${x(0).toFixed(1)},${H - padB}Z`;
    return d;
  };
  const incomePath = linePath('income');
  const expensePath = linePath('expense');
  let paths;
  if (balanceState.kind === 'inout') {
    paths = `<path d="${areaPath('income')}" fill="#303f9f" opacity="0.12"/>
      <path d="${incomePath}" fill="none" stroke="#303f9f" stroke-width="2.5"/>
      <path d="${areaPath('expense')}" fill="#ee6c8c" opacity="0.12"/>
      <path d="${expensePath}" fill="none" stroke="#ee6c8c" stroke-width="2.5"/>`;
  } else {
    // 结余 = 收入 - 支出
    const bal = keys.map(k => months[k].income - months[k].expense);
    const balPath = bal.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(Math.max(v, 0)).toFixed(1)}`).join(' ');
    paths = `<path d="${balPath}" fill="none" stroke="#303f9f" stroke-width="2.5"/>`;
  }
  const labels = keys.map((k, i) => `<text x="${x(i)}" y="${H - 4}" text-anchor="middle" font-size="10" fill="#999">${k}</text>`).join('');
  const dots = keys.map((k, i) => {
    const v1 = balanceState.kind === 'inout' ? months[k].income : Math.max(months[k].income - months[k].expense, 0);
    const v2 = balanceState.kind === 'inout' ? months[k].expense : 0;
    let d = `<circle cx="${x(i)}" cy="${y(v1)}" r="3" fill="#303f9f"/>`;
    if (balanceState.kind === 'inout') d += `<circle cx="${x(i)}" cy="${y(v2)}" r="3" fill="#ee6c8c"/>`;
    return d;
  }).join('');
  $('#balance-chart').innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${grid}${paths}${dots}${labels}</svg>`;

  // 账单列表
  $('#balance-list').innerHTML = items.map(i => `
    <div class="tx-item" style="background:#fff">
      <div class="tx-icon">${icIcon(txIconFile(i.type), 'ic20')}</div>
      <div class="tx-mid">
        <div class="tx-type">${i.type}</div>
        <div class="tx-remark">${i.date} ${i.remark}</div>
      </div>
      <div class="tx-money ${moneyClass(i.money)}">${i.money > 0 ? '+' : '-'}${fmt(Math.abs(i.money))}</div>
    </div>`).join('');
}

$('#balance-kind-group').addEventListener('click', (e) => {
  const p = e.target.closest('.period');
  if (!p) return;
  $$('#balance-kind-group .period').forEach(t => t.classList.remove('active'));
  p.classList.add('active');
  balanceState.kind = p.dataset.k;
  renderBalance();
});

/* ================= 选择账本弹窗（res_K1） ================= */
function renderBookSheet() {
  $('#book-sheet-list').innerHTML = books.map((b, i) => `
    <div class="sheet-book-item ${i === state.selectedBook ? 'checked' : ''} ${bookManaging ? 'managing' : ''}" data-i="${i}">
      <span class="cell-icon">${icIcon(b.icon, 'ic20')}</span>
      <span class="book-name">${b.name}</span>
      <span class="book-manage">
        <i class="ic ic14 book-manage-del" data-del="${i}" style="--mask:url(assets/icons/ic_close.png)"></i>
        <i class="ic ic16 book-manage-edit" data-edit="${i}" style="--mask:url(assets/icons/cate_more.png)"></i>
      </span>
    </div>`).join('');
}

function openBookSheet() {
  bookManaging = false;
  renderBookSheet();
  $('#book-sheet').classList.add('show');
}
function closeBookSheet() { $('#book-sheet').classList.remove('show'); }

// 上一个月字符串（YYYY-MM）
function prevMonthStr(m) {
  const d = new Date(Number(m.slice(0, 4)), Number(m.slice(5, 7)) - 2, 1);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
}

// 切换账本：切换数据源并刷新各页面（有后端对接层时按账本异步加载）
async function switchBook(i) {
  state.selectedBook = i;
  const b = books[i];
  tx = b.tx;
  // 后端对接层可用且该账本有后端 id：异步加载该账本 当前月 + 上月
  if (window.bookAPI && b.id) {
    try {
      const cur = acctYM || (new Date().getFullYear() + '-' + String(new Date().getMonth() + 1).padStart(2, '0'));
      const [c, p] = await Promise.all([
        window.bookAPI.loadLedgerMonth(b.id, cur),
        window.bookAPI.loadLedgerMonth(b.id, prevMonthStr(cur)),
      ]);
      b.tx = c.concat(p);
      tx = b.tx;
    } catch (e) { /* 后端不可用保持现状 */ }
  }
  renderBookSheet();
  renderBooks();
  renderTxList();
  renderStat();
  renderCalendar();
}

// 长按账本 → 进入管理模式（文字抖动 + 显示红叉/三点）
let bookManaging = false;
let bookPressTimer = null;
let suppressBookClick = false;
$('#book-sheet-list').addEventListener('pointerdown', (e) => {
  if (bookManaging || !e.target.closest('.sheet-book-item')) return;
  clearTimeout(bookPressTimer);
  bookPressTimer = setTimeout(() => {
    bookManaging = true;
    suppressBookClick = true;
    renderBookSheet();
  }, 600);
});
['pointerup', 'pointercancel', 'pointerleave'].forEach(ev =>
  document.addEventListener(ev, () => { clearTimeout(bookPressTimer); bookPressTimer = null; }, true));

$('#book-sheet-list').addEventListener('click', (e) => {
  if (suppressBookClick) { suppressBookClick = false; return; }
  const delBtn = e.target.closest('.book-manage-del');
  if (delBtn) { bookManaging = false; confirmDeleteBook(Number(delBtn.dataset.del)); return; }
  const editBtn = e.target.closest('.book-manage-edit');
  if (editBtn) { bookManaging = false; closeBookSheet(); openBookEditor(Number(editBtn.dataset.edit), false); return; }
  const item = e.target.closest('.sheet-book-item');
  if (!item) return;
  if (bookManaging) { bookManaging = false; renderBookSheet(); return; }
  switchBook(Number(item.dataset.i));
  toast('已切换到「' + books[state.selectedBook].name + '」');
  setTimeout(closeBookSheet, 500);
});
$('#book-sheet-cancel').addEventListener('click', () => {
  if (bookManaging) { bookManaging = false; renderBookSheet(); return; }
  closeBookSheet();
});
$('#balance-book-btn').addEventListener('click', openBookSheet);

/* ================= 编辑/新建账本（新建入口 + 长按三点编辑） ================= */
let editBookMode = 'add';  // add | edit
let editBookIndex = -1;    // 编辑模式下当前账本索引

function refreshBooks() {
  renderBookSheet(); renderBooks(); renderMainbook();
  renderTxList(); renderStat(); renderCalendar();
}

let editBookOrigin = null; // 打开时的初始值，用于判断是否改动过

// 读取当前表单值
function bookFormValues() {
  const iconEl = $('#book-icon-grid .book-icon-opt.selected');
  return {
    name: $('#book-name').value.trim(),
    type: $('#book-type').textContent.replace(' ›', ''),
    icon: iconEl ? iconEl.dataset.ic : null,
  };
}

// 未做修改：只显示"取消"；做了修改：显示"取消 + 保存"
function updateBookSaveUI() {
  const cur = bookFormValues();
  const dirty = !!editBookOrigin && (
    cur.name !== editBookOrigin.name ||
    cur.type !== editBookOrigin.type ||
    (cur.icon !== null && cur.icon !== editBookOrigin.icon)
  );
  $('#btn-book-cancel').style.display = 'block';
  $('#btn-book-save').style.display = dirty ? 'block' : 'none';
}

// 打开账本编辑器：isNew=true 新建模式，否则编辑 books[idx]
function openBookEditor(idx, isNew) {
  editBookMode = isNew ? 'add' : 'edit';
  editBookIndex = idx;
  $('#book-editor-title').textContent = isNew ? '新建账本' : '编辑账本';
  if (isNew) {
    $('#book-name').value = '';
    $('#book-type').textContent = '标准账本 ›';
    renderBookIconGrid('ic_accounts.png');
    editBookOrigin = { name: '', type: '标准账本', icon: 'ic_accounts.png' };
  } else {
    const b = books[idx];
    $('#book-name').value = b.name;
    $('#book-type').textContent = (b.type || '标准账本') + ' ›';
    renderBookIconGrid(b.icon);
    editBookOrigin = { name: b.name, type: b.type || '标准账本', icon: b.icon };
  }
  openOverlay('page-editbook');
  updateBookSaveUI();
}

function renderBookIconGrid(sel) {
  $('#book-icon-grid').innerHTML = BOOK_ICONS.map(ic => `
    <div class="book-icon-opt ${ic === sel ? 'selected' : ''}" data-ic="${ic}">${icIcon(ic, 'ic22')}</div>`).join('');
}

// 选择账本弹窗 → "新建账本"入口
$('#book-sheet-edit').addEventListener('click', () => { closeBookSheet(); openBookEditor(-1, true); });

$('#book-icon-grid').addEventListener('click', (e) => {
  const o = e.target.closest('.book-icon-opt');
  if (!o) return;
  $$('#book-icon-grid .book-icon-opt').forEach(x => x.classList.remove('selected'));
  o.classList.add('selected');
  updateBookSaveUI();
});

// 账本类型选择弹窗
$('#book-type').addEventListener('click', () => {
  const cur = $('#book-type').textContent.replace(' ›', '');
  $('#booktype-list').innerHTML = BOOK_TYPES.map(t => `
    <div class="sheet-book-item ${t === cur ? 'checked' : ''}" data-t="${t}"><span>${t}</span></div>`).join('');
  $('#booktype-sheet').classList.add('show');
});
$('#booktype-list').addEventListener('click', (e) => {
  const it = e.target.closest('.sheet-book-item');
  if (!it) return;
  $('#book-type').textContent = it.dataset.t + ' ›';
  $('#booktype-sheet').classList.remove('show');
  updateBookSaveUI();
});
$('#booktype-cancel').addEventListener('click', () => $('#booktype-sheet').classList.remove('show'));

// 顶栏"取消"：放弃本次编辑/新建，直接关闭（返回键 data-back 同样视为取消）
$('#btn-book-cancel').addEventListener('click', closeOverlay);

// 名称输入变化 → 更新 取消/保存 显示
$('#book-name').addEventListener('input', updateBookSaveUI);

// 删除账本通用（二次确认弹窗，有后端对接层时走后端级联删除）
function confirmDeleteBook(i) {
  const b = books[i];
  if (!b) return;
  confirmMsg('删除账本', `确定删除「${b.name}」吗？该账本下的所有账单将一并删除。`, async () => {
    if (books.length <= 1) { toast('至少保留一个账本'); return; }
    try {
      if (window.bookAPI && b.id) await window.bookAPI.deleteLedger(b.id);
    } catch (e) {
      toast('后端删除失败：' + ((e && e.message) || '未知错误'));
      return;
    }
    books.splice(i, 1);
    if (state.selectedBook >= books.length) state.selectedBook = books.length - 1;
    tx = books[state.selectedBook].tx;
    refreshBooks();
    toast('账本已删除');
  });
}

// 保存（编辑 / 新建，有后端对接层时走后端持久化）
async function saveEditBook() {
  const name = $('#book-name').value.trim();
  if (!name) { toast('请输入账本名称'); return; }
  const type = $('#book-type').textContent.replace(' ›', '');
  const iconEl = $('#book-icon-grid .book-icon-opt.selected');
  const icon = iconEl ? iconEl.dataset.ic : 'ic_accounts.png';
  try {
    if (editBookMode === 'add') {
      let id;
      if (window.bookAPI) {
        const r = await window.bookAPI.createLedger({ name, type, icon });
        id = r && r.id;
      }
      books.push({ id, name, icon, type, tx: [] });
      state.selectedBook = books.length - 1;
      tx = books[state.selectedBook].tx;
      toast('账本「' + name + '」已创建');
    } else {
      const b = books[editBookIndex];
      if (window.bookAPI && b.id) {
        await window.bookAPI.updateLedger(b.id, { name, type, icon });
      }
      b.name = name; b.icon = icon; b.type = type;
      toast('账本已保存');
    }
  } catch (e) {
    toast('后端操作失败：' + ((e && e.message) || '未知错误'));
    return;
  }
  refreshBooks();
  closeOverlay();
}

/* ================= 图片大图查看（res_OH） ================= */
let picTransform = { rot: 0, flip: false };
function resetPicTransform() {
  picTransform = { rot: 0, flip: false };
  applyPicTransform();
}
function applyPicTransform() {
  const el = $('#viewpic-img');
  el.style.transform = `rotate(${picTransform.rot}deg) scaleX(${picTransform.flip ? -1 : 1})`;
}
function openViewPic() {
  resetPicTransform();
  openOverlay('page-viewpic');
}
$('#viewpic-close').addEventListener('click', closeOverlay);
$('#viewpic-rotate').addEventListener('click', () => {
  picTransform.rot = (picTransform.rot + 90) % 360;
  applyPicTransform();
});
$('#viewpic-flip').addEventListener('click', () => {
  picTransform.flip = !picTransform.flip;
  applyPicTransform();
});
$('#viewpic-share').addEventListener('click', openShare);
$('#viewpic-del').addEventListener('click', () => {
  toast('图片已删除');
  closeOverlay();
});
// 记账页图片按钮 → 大图查看
$('#btn-pic').addEventListener('click', openViewPic);
// 图片凭证页空状态点击 → 大图查看
$('#page-pic .empty-state').addEventListener('click', openViewPic);

/* ================= 注册 / 找回密码 ================= */
let regCodeSent = false;
function sendCode(btn) {
  if (regCodeSent) { toast('验证码已发送到您的手机'); return; }
  regCodeSent = true;
  toast('验证码已发送到您的手机');
  let n = 60;
  btn.textContent = n + 's';
  const t = setInterval(() => {
    n--;
    if (n <= 0) {
      clearInterval(t);
      btn.textContent = '获取验证码';
      regCodeSent = false;
    } else btn.textContent = n + 's';
  }, 1000);
}

$('#reg-getcode').addEventListener('click', function () {
  if (!/^1\d{10}$/.test($('#reg-mobile').value.trim())) { toast('手机号格式不正确'); return; }
  sendCode(this);
});
$('#reg-next').addEventListener('click', () => {
  const mobile = $('#reg-mobile').value.trim();
  const vc = $('#reg-vcode').value.trim();
  if (!/^1\d{10}$/.test(mobile)) { toast('手机号格式不正确'); return; }
  if (!vc) { toast('请输入验证码'); return; }
  $('#reg-step-1').hidden = true;
  $('#reg-step-2').hidden = false;
});
$('#reg-finish').addEventListener('click', () => {
  const p1 = $('#reg-pwd').value, p2 = $('#reg-pwd2').value;
  if (p1.length < 6) { toast('密码长度不能低于6个字符'); return; }
  if (p1 !== p2) { toast('两次输入的密码不一致'); return; }
  toast('注册成功，请登录');
  closeOverlay();
});
$('#login-register').addEventListener('click', () => openOverlay('page-register'));
$('#login-forgot').addEventListener('click', () => openOverlay('page-forgot'));

$('#forgot-getcode').addEventListener('click', function () {
  if (!/^1\d{10}$/.test($('#forgot-mobile').value.trim())) { toast('手机号格式不正确'); return; }
  sendCode(this);
});
$('#forgot-go').addEventListener('click', () => {
  const pwd = $('#forgot-pwd').value;
  if (pwd.length < 6) { toast('密码长度不能低于6个字符'); return; }
  toast('密码已重置，请重新登录');
  closeOverlay();
});

/* ================= 检查更新（关于页） ================= */
const ABOUT_ACTIONS = {
  update: () => {
    confirmMsg('检查更新', '检测到新版本(1.9.0)，是否更新？', startDownload);
  },
};

/* ================= 隐私协议弹窗（首次启动） ================= */
$('#privacy-yes').addEventListener('click', () => {
  $('#privacy-sheet').classList.remove('show');
  toast('欢迎使用简约记账');
});
$('#privacy-no').addEventListener('click', () => {
  $('#privacy-sheet').classList.remove('show');
  toast('您已拒绝协议，部分功能不可用');
});
$('#privacy-view1').addEventListener('click', () => toast('用户协议（网页加载演示）'));
$('#privacy-view2').addEventListener('click', () => toast('隐私政策（网页加载演示）'));

/* ================= 选项设置（7 项） ================= */
function renderSetting() {
  $$('#set-bigdisplay .set-radio').forEach(r => r.classList.toggle('active', r.dataset.v === settings.bigDisplay));
  $$('#set-sort .set-radio').forEach(r => r.classList.toggle('active', r.dataset.v === settings.sort));
  $('#set-moneycolor-val').textContent = settings.moneyColor === 'redGreen' ? '支出红色，收入绿色' : '支出绿色，收入红色';
  $('#set-startday-val').textContent = settings.startDay + '日';
  $('#set-totalbal').classList.toggle('on', settings.totalBalance);
  $('#set-neighbor').classList.toggle('on', settings.loadNeighbor);
  $('#set-vibrate').classList.toggle('on', settings.vibrate);
}

$('#set-bigdisplay').addEventListener('click', (e) => {
  const r = e.target.closest('.set-radio');
  if (!r) return;
  settings.bigDisplay = r.dataset.v;
  renderSetting();
  updateOverview();
});

$('#set-sort').addEventListener('click', (e) => {
  const r = e.target.closest('.set-radio');
  if (!r) return;
  settings.sort = r.dataset.v;
  renderSetting();
  renderTxList();
});

$('#set-moneycolor').addEventListener('click', () => {
  settings.moneyColor = settings.moneyColor === 'redGreen' ? 'greenRed' : 'redGreen';
  applyMoneyColors();
  renderSetting();
  renderTxList();
});

$('#set-startday').addEventListener('click', () => {
  const days = [1, 5, 10, 15, 20, 25];
  const cur = settings.startDay;
  settings.startDay = days[(days.indexOf(cur) + 1) % days.length];
  renderSetting();
  toast('账单起始日已设为每月 ' + settings.startDay + ' 日');
});

$('#set-totalbal').addEventListener('click', function () {
  settings.totalBalance = !settings.totalBalance;
  this.classList.toggle('on', settings.totalBalance);
});
$('#set-neighbor').addEventListener('click', function () {
  settings.loadNeighbor = !settings.loadNeighbor;
  this.classList.toggle('on', settings.loadNeighbor);
});
$('#set-vibrate').addEventListener('click', function () {
  settings.vibrate = !settings.vibrate;
  this.classList.toggle('on', settings.vibrate);
});

// 选项设置 → 删除区间账单
$('#set-erase').addEventListener('click', openErase);

/* ================= 支付方式弹窗 ================= */
$('#vip-buy').addEventListener('click', () => $('#pay-sheet').classList.add('show'));
$('#pay-wechat').addEventListener('click', () => {
  $('#pay-sheet').classList.remove('show');
  toast('微信支付（演示）：支付成功，已开通会员！');
  $('#vip-status').textContent = '会员已开通';
  $('#uc-vip').textContent = '会员已开通';
});
$('#pay-alipay').addEventListener('click', () => {
  $('#pay-sheet').classList.remove('show');
  toast('支付宝支付（演示）：支付成功，已开通会员！');
});
$('#pay-cancel').addEventListener('click', () => $('#pay-sheet').classList.remove('show'));

/* ================= 分享弹窗 ================= */
function openShare() { $('#share-sheet').classList.add('show'); }
$$('#share-sheet .share-item').forEach(item => {
  item.addEventListener('click', () => {
    $('#share-sheet').classList.remove('show');
    toast('已分享到' + item.dataset.p);
  });
});
$('#share-cancel').addEventListener('click', () => $('#share-sheet').classList.remove('show'));

/* ================= 删除区间账单 ================= */
function openErase() { $('#erase-sheet').classList.add('show'); }
$('#erase-cancel').addEventListener('click', () => $('#erase-sheet').classList.remove('show'));
$('#erase-go').addEventListener('click', () => {
  const s = $('#erase-start').textContent, e = $('#erase-end').textContent;
  const before = tx.flatMap(g => g.items).length;
  tx = tx.map(g => g.date >= s && g.date <= e
    ? { date: g.date, items: [] }
    : g).filter(g => g.items.length);
  const after = tx.flatMap(g => g.items).length;
  $('#erase-sheet').classList.remove('show');
  renderTxList();
  toast(`已删除 ${before - after} 笔账单`);
});
$('#erase-start').addEventListener('click', () => { toast('选择起始日期（演示）'); });
$('#erase-end').addEventListener('click', () => { toast('选择结束日期（演示）'); });

/* ================= 设置昵称 ================= */
function openNickname() {
  $('#nickname-input').value = $('#nickname').textContent === '点击登录' ? '' : $('#nickname').textContent;
  $('#nickname-sheet').classList.add('show');
}
$('#nickname-cancel').addEventListener('click', () => $('#nickname-sheet').classList.remove('show'));
$('#nickname-save').addEventListener('click', () => {
  const name = $('#nickname-input').value.trim();
  if (!name) { toast('昵称不能为空'); return; }
  $('#nickname').textContent = name;
  $('#uc-nickname').textContent = name;
  $('#pi-nickname').textContent = name;
  $('#nickname-sheet').classList.remove('show');
  toast('昵称已更新');
});
// 用户中心昵称行 → 昵称弹窗
$$('#page-usercenter .uc-row').forEach(r => {
  if (r.textContent.includes('昵称')) r.addEventListener('click', openNickname);
});

/* ================= 恢复方式 ================= */
let restoreMode = 'merge';
$$('#restore-sheet .restore-opt').forEach(opt => {
  opt.addEventListener('click', () => {
    $$('#restore-sheet .restore-opt').forEach(o => {
      o.classList.remove('active');
      const ic = o.querySelector('.ic');
      if (ic) ic.remove();
    });
    opt.classList.add('active');
    opt.insertAdjacentHTML('beforeend', icIcon('ic_check.png', 'ic18'));
    restoreMode = opt.dataset.v;
  });
});
$('#restore-cancel').addEventListener('click', () => $('#restore-sheet').classList.remove('show'));
$('#restore-go').addEventListener('click', () => {
  $('#restore-sheet').classList.remove('show');
  const log = $('#backup-log');
  log.style.display = 'block';
  log.textContent = restoreMode === 'merge' ? '正在与现有账单合并恢复…' : '正在覆盖现有账单…';
  setTimeout(() => {
    log.textContent = restoreMode === 'merge' ? '合并恢复成功' : '覆盖恢复成功';
    toast('恢复成功');
  }, 900);
});

/* ================= 自定义统计区间 ================= */
function openCustomRange() { $('#customstat-sheet').classList.add('show'); }
$('#customstat-cancel').addEventListener('click', () => $('#customstat-sheet').classList.remove('show'));
$('#customstat-go').addEventListener('click', () => {
  $('#customstat-sheet').classList.remove('show');
  toast('已按自定义区间统计');
  renderCustomStat();
});
$('#customstat-start').addEventListener('click', () => toast('选择起始日期（演示）'));
$('#customstat-end').addEventListener('click', () => toast('选择结束日期（演示）'));

/* ================= 切换账单周期 ================= */
function openMode() { $('#mode-sheet').classList.add('show'); }
$$('#mode-sheet .mode-opt').forEach(opt => {
  opt.addEventListener('click', () => {
    $$('#mode-sheet .mode-opt').forEach(o => {
      o.classList.remove('active');
      const ic = o.querySelector('.ic');
      if (ic) ic.remove();
    });
    opt.classList.add('active');
    opt.insertAdjacentHTML('beforeend', icIcon('ic_check.png', 'ic18'));
  });
});
$('#mode-cancel').addEventListener('click', () => $('#mode-sheet').classList.remove('show'));

/* ================= 年/月滚轮选择器（明细页） ================= */
function makeWheel(el, values, suffix, onChange) {
  const itemH = 46;
  el.innerHTML = values.map(v => `<div class="wheel-item" data-v="${v}">${v}${suffix}</div>`).join('');
  let selected = 0;
  const sync = (i) => {
    selected = Math.max(0, Math.min(values.length - 1, i));
    el.querySelectorAll('.wheel-item').forEach((it, idx) => it.classList.toggle('selected', idx === selected));
    onChange(values[selected]);
  };
  el.addEventListener('scroll', () => {
    const i = Math.round(el.scrollTop / itemH);
    if (i !== selected) sync(i);
  }, { passive: true });
  return {
    select: (idx) => { el.scrollTop = idx * itemH; sync(idx); },
    value: () => values[selected],
  };
}

const wheelYears = []; for (let y = 2026; y >= 2018; y--) wheelYears.push(y);
const wheelMonths = Array.from({ length: 12 }, (_, i) => i + 1);
const wYear = makeWheel($('#wheel-year'), wheelYears, '年', v => { wheelYear = Number(v); });
const wMonth = makeWheel($('#wheel-month'), wheelMonths, '月', v => { wheelMonth = Number(v); });
wYear.select(wheelYears.indexOf(2026));
wMonth.select(wheelMonths.indexOf(8));

$('#btn-month').addEventListener('click', () => {
  $('#ym-sheet').classList.add('show');
  wYear.select(wheelYears.indexOf(wheelYear));
  wMonth.select(wheelMonths.indexOf(wheelMonth));
  // 明细页：确定后切换到所选年月并过滤账单
  ymOnOk = () => {
    acctYM = `${wheelYear}-${String(wheelMonth).padStart(2, '0')}`;
    $('#month-label').textContent = `${wheelYear}年${wheelMonth}月`;
    renderTxList();
  };
});
let ymOnOk = null; // 年/月滚轮确定回调（明细页 / 日历共用）
$('#ym-ok').addEventListener('click', () => {
  if (ymOnOk) ymOnOk();
  ymOnOk = null;
  $('#ym-sheet').classList.remove('show');
});
$('#ym-cancel').addEventListener('click', () => { ymOnOk = null; $('#ym-sheet').classList.remove('show'); });

/* ================= 图片来源 ================= */
$$('#pic-sheet .mode-opt').forEach(opt => {
  opt.addEventListener('click', () => {
    $('#pic-sheet').classList.remove('show');
    toast(opt.dataset.v === 'camera' ? '打开相机（演示）' : '打开相册（演示）');
  });
});
$('#pic-sheet-cancel').addEventListener('click', () => $('#pic-sheet').classList.remove('show'));

/* ================= 初始化 ================= */
renderTxList();
renderTypeGrid();
updateMoneyDisplay();
renderYearStat();
renderBooks();
renderTypeMgr();
renderImport();
renderThemes();
renderMoreApps();
renderGesturePad();
renderBalance();
renderSetting();
applyMoneyColors();
updateLoginUI();
showPage('page-account');

// 启动页 1.2 秒后隐藏，然后显示隐私协议弹窗
setTimeout(() => $('#splash').classList.add('hide'), 1200);
setTimeout(() => $('#privacy-sheet').classList.add('show'), 1600);

// 概览底部行点击（结余）→ 结余趋势页
$('#ov-bottom').addEventListener('click', (e) => {
  const col = e.target.closest('.ov-col');
  if (!col) return;
  const label = col.querySelector('.ov-label-sm').textContent;
  if (label === '结余' || label === '支出' || label === '收入') {
    renderBalance();
    openOverlay('page-balance');
  }
});

// 图表页区域按钮 → 自定义区间弹窗
$('#chart-region-btn').addEventListener('click', openCustomRange);

// 云备份恢复 → 恢复方式弹窗
$('#backup-restore').addEventListener('click', () => $('#restore-sheet').classList.add('show'));

// 记账页图片按钮 → 图片来源弹窗
$('#btn-pic').removeEventListener('click', openViewPic);
$('#btn-pic').addEventListener('click', () => $('#pic-sheet').classList.add('show'));
// 图片来源弹窗选相册 → 打开大图查看
$$('#pic-sheet .mode-opt[data-v="album"]').forEach(o => {
  o.addEventListener('click', () => setTimeout(openViewPic, 400));
});
