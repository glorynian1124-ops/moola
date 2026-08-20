/* ============================================================
 * prototype/api.js — 前端原型 ↔ 后端 Flask API 对接适配层（Phase 1）
 *
 * 作用：让前端原型用后端（127.0.0.1:5001）数据库的真实数据，
 *       替代 app.js 里的内存假数据（INITIAL_TX）。
 *
 * 实现方式：通过覆盖 app.js 的全局函数 + 捕获阶段监听器实现，
 *           不改动渲染逻辑；删除本文件并去掉 index.html 里的
 *           <script src="api.js"> 即可还原为纯演示模式。
 *
 * 前置条件：后端已启动 `python main.py web`（端口 5001）
 * ============================================================ */
(function () {
  'use strict';

  const API_BASE = 'http://127.0.0.1:5001/api';

  // 覆盖前保存 app.js 的原始全局函数（api.js 在 app.js 之后加载）
  const origRenderCalendar = window.renderCalendar;

  /* ---------- 基础请求封装 ---------- */
  async function apiGet(path) {
    const resp = await fetch(API_BASE + path);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  }
  async function apiPost(path, body) {
    const resp = await fetch(API_BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  }
  async function apiPut(path, body) {
    const resp = await fetch(API_BASE + path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  }
  async function apiDelete(path) {
    const resp = await fetch(API_BASE + path, { method: 'DELETE' });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  }

  /* ---------- 数据装载：后端 group -> 前端 tx 结构 ---------- */
  const loadedMonths = new Set(); // 已从后端加载的月份

  // 按日期降序（最新在前），与后端 group 顺序一致；避免合并时 concat 打乱顺序导致详情点击错位
  function sortTxDesc(arr) {
    return arr.slice().sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  }

  function groupToTx(groups) {
    return (groups || []).map(g => ({
      date: g.date,
      items: g.items.map(it => ({ id: it.id, type: it.type, remark: it.remark, money: it.money })),
    }));
  }

  // 把某月真实数据合并进全局 tx（替换同月旧数据）
  async function loadMonth(month) {
    if (loadedMonths.has(month)) return;
    loadedMonths.add(month);
    const data = await apiGet('/transactions/group?month=' + encodeURIComponent(month));
    const monthTx = groupToTx(data.groups);
    tx = sortTxDesc(tx.filter(g => !g.date.startsWith(month)).concat(monthTx));
  }

  // 按账本 + 月份加载（返回该账本该月的 tx 数组，不写全局 tx）
  async function loadLedgerMonth(ledgerId, month) {
    const data = await apiGet('/transactions/group?ledger_id=' + ledgerId + '&month=' + encodeURIComponent(month));
    return groupToTx(data.groups);
  }

  /* ---------- 账本 CRUD 封装 ---------- */
  async function fetchLedgers() {
    const data = await apiGet('/ledgers');
    return data.ledgers || [];
  }
  async function createLedger(payload) {
    return apiPost('/ledgers', payload);
  }
  async function updateLedger(id, payload) {
    return apiPut('/ledgers/' + id, payload);
  }
  async function deleteLedger(id) {
    return apiDelete('/ledgers/' + id);
  }

  // 暴露给 app.js 的账本对接接口（无 api.js 时 app.js 走本地演示数据）
  window.bookAPI = {
    loadLedgerMonth,
    fetchLedgers,
    createLedger,
    updateLedger,
    deleteLedger,
    currentMonth,
    prevMonth,
  };

  function currentMonth() {
    const d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  }
  function prevMonth(m) {
    const d = new Date(Number(m.slice(0, 4)), Number(m.slice(5, 7)) - 2, 1);
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  }

  /* ---------- 启动：拉账本 → 重建 books → 加载默认账本数据 ---------- */
  // 以后端数据库为准：成功则全量用后端数据；失败则清空为"无数据"并提示，
  // 不再回退到本地 INITIAL_TX 演示数据，避免明细/统计等页面数据源不一致。
  async function initBackend() {
    let ledgers = [];
    try {
      ledgers = await fetchLedgers();
      if (!ledgers.length) {
        await createLedger({ name: '默认账本', type: '标准账本', icon: 'ic_accounts.png' });
        ledgers = await fetchLedgers();
      }
    } catch (e) {
      console.warn('[api.js] 后端连接失败：', e);
      ledgers = [];
    }
    // 无论成败都用后端账本重建 books（失败则为空列表）
    books = ledgers.map(l => ({ id: l.id, name: l.name, icon: l.icon, type: l.type, tx: [] }));
    state.selectedBook = 0;

    if (books.length) {
      try {
        // 加载默认账本 当前月 + 上月
        const cur = currentMonth();
        const [c, p] = await Promise.all([
          loadLedgerMonth(books[0].id, cur),
          loadLedgerMonth(books[0].id, prevMonth(cur)),
        ]);
        books[0].tx = c.concat(p);
        tx = books[0].tx;
        // 默认显示「最近有数据的月份」，同步顶部月份按钮与滚轮
        const dates = tx.map(g => g.date).filter(Boolean).sort();
        if (dates.length) {
          const latest = dates[dates.length - 1].slice(0, 7);
          if (latest !== acctYM) {
            acctYM = latest;
            const [yy, mm] = latest.split('-').map(Number);
            wheelYear = yy; wheelMonth = mm;
            const label = $('#month-label');
            if (label) label.textContent = `${yy}年${mm}月`;
          }
        }
        renderBooks(); renderTxList(); renderStat(); renderCalendar();
        return;
      } catch (e) {
        console.warn('[api.js] 加载账本数据失败：', e);
      }
    }
    // 后端不可用 / 无账本：空数据 + 提示（保持各页面一致）
    tx = [];
    renderBooks(); renderTxList(); renderStat();
    const hint = document.createElement('div');
    hint.style.cssText = 'margin:12px;padding:10px 14px;border-radius:8px;background:#fff3f3;' +
      'color:#c00;font-size:13px;line-height:1.6;';
    hint.innerHTML = '⚠️ 后端未连接，无法加载真实账单。<br>' +
      '请先启动 <code>python main.py web</code>（端口 5001）后刷新页面。';
    const list = $('#tx-list');
    if (list && list.parentNode) {
      list.insertAdjacentElement('beforebegin', hint);
      setTimeout(() => hint.remove(), 8000);
    }
  }
  initBackend();

  /* ---------- 记账：先写后端，成功再走本地逻辑 ---------- */
  window.addTx = async function addTx(again = false) {
    const input = parseFloat(state.moneyStr) || 0;
    const money = calcAcc + input;
    const sign = state.naKind === 'expense' ? -1 : 1;
    if (!money || !state.naType) {
      if (!money) resetCalc();
      return;
    }
    const remark = ($('#note-input').value.trim() || state.naType);
    const curBook = books[state.selectedBook];
    let row = null;
    try {
      const r = await apiPost('/transactions', {
        amount: +(money * sign).toFixed(2), // 负=支出 正=收入
        category: state.naType,
        merchant: remark,
        note: '',
        trans_time: txDate + ' 12:00:00',
        source: 'manual',
        ledger_id: curBook && curBook.id, // 写入当前账本
      });
      if (!r || !(r.ok || r.duplicate)) {
        alert('记账失败：' + ((r && r.error) || '未知错误'));
        return;
      }
      row = r.row || null;
    } catch (e) {
      alert('无法连接后端（' + API_BASE + '）：' + e.message);
      return;
    }

    // 本地插入（带后端 id，供详情页删除/编辑定位）
    let group = tx.find(g => g.date === txDate);
    if (!group) { group = { date: txDate, items: [] }; tx.unshift(group); }
    group.items.push({
      id: row ? row.id : undefined,
      type: state.naType,
      remark,
      money: +(money * sign).toFixed(2),
      pic: hasPic,
    });
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
  };

  /* ---------- 搜索：走后端全库搜索 ---------- */
  window.runSearch = async function runSearch() {
    const q = ($('#search-input').value || '').trim();
    const list = $('#result-list');
    if (!q) { list.innerHTML = ''; return; }
    try {
      const mode = state.searchMode === 'category' ? 'category' : 'bill';
      const sort = state.searchSort === 'money' ? 'amount' : 'time';
      const rows = await apiGet('/search?q=' + encodeURIComponent(q) + '&mode=' + mode + '&sort=' + sort);
      list.innerHTML = rows.length ? rows.map(i => `
        <div class="tx-item" style="background:#fff">
          <div class="tx-icon">${icIcon(txIconFile(i.category), 'ic20')}</div>
          <div class="tx-mid">
            <div class="tx-type">${i.category}</div>
            <div class="tx-remark">${(i.merchant || '') + (i.note ? ' · ' + i.note : '')}</div>
            <div class="tx-remark" style="font-size:11px;color:#999">${(i.trans_time || '').slice(0, 10)}</div>
          </div>
          <div class="tx-money ${moneyClass(i.amount)}">${i.amount > 0 ? '+' : '-'}${fmt(Math.abs(i.amount))}</div>
        </div>`).join('')
        : '<div class="empty-text" style="text-align:center;padding:30px;color:#999">无搜索结果</div>';
    } catch (e) {
      list.innerHTML = '<div class="empty-text" style="text-align:center;padding:30px;color:#999">后端不可用，请确认已启动 python main.py web</div>';
      console.warn('[api.js] 搜索失败：', e);
    }
  };

  // app.js 顶层绑定的是旧 runSearch 引用，需 clone 替换按钮重新绑定
  (function rebindSearchGo() {
    const btn = $('#search-go');
    if (!btn) return;
    const clone = btn.cloneNode(true);
    btn.replaceWith(clone);
    clone.addEventListener('click', () => window.runSearch());
  })();

  /* ---------- 日历：切月前懒加载该月数据（按当前账本） ---------- */
  window.renderCalendar = async function renderCalendar() {
    const month = state.calYear + '-' + String(state.calMonth).padStart(2, '0');
    const b = books[state.selectedBook];
    try {
      if (b && b.id) {
        const mtx = await loadLedgerMonth(b.id, month);
        tx = sortTxDesc(tx.filter(g => !g.date.startsWith(month)).concat(mtx));
      } else {
        await loadMonth(month);
      }
    } catch (e) { /* 后端不可用则保持现状 */ }
    origRenderCalendar();
  };

  // 修正日历底部列表的硬编码日期（app.js 写死 2026-08-18），跟随当前年月
  window.renderCalList = function renderCalList(day) {
    const dateStr = state.calYear + '-' + String(state.calMonth).padStart(2, '0') +
      '-' + String(day).padStart(2, '0');
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
  };

  /* ---------- 首页概览：由 app.js 的 updateOverview 处理（基于 acctYM） ---------- */

  /* ---------- 详情页删除/编辑：捕获阶段先删后端旧记录 ---------- */
  function detailItem() {
    const g = tx.find(x => x.date === detailTx.date);
    return (g && g.items[detailTx.idx]) || null;
  }
  function delBackend(item) {
    if (!item || !item.id) return;
    apiDelete('/transactions/' + item.id).catch(err => console.warn('[api.js] 删除后端失败：', err));
  }

  // 删除：捕获阶段先 DELETE 后端 → 冒泡到 app.js 本地删除+渲染
  $('#detail-del').addEventListener('click', function () {
    delBackend(detailItem());
  }, true);

  // 编辑：捕获阶段先 DELETE 后端旧记录 → 冒泡到 app.js 本地删旧+回填+新增
  $('#detail-edit').addEventListener('click', function () {
    delBackend(detailItem());
  }, true);

})();
