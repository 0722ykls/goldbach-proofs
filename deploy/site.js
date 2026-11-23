'use strict';

const lang = document.documentElement.lang.startsWith('zh') ? 'zh' : 'en';
const repository = 'https://github.com/CGandGameEngineLearner/goldbach-proofs';
const menu = document.querySelector('.menu-toggle');
const navigation = document.getElementById('site-nav');
menu.addEventListener('click', () => {
  menu.setAttribute('aria-expanded', String(navigation.classList.toggle('expanded')));
});
navigation.addEventListener('click', () => {
  navigation.classList.remove('expanded');
  menu.setAttribute('aria-expanded', 'false');
});
const strings = {
  zh: {
    open: '待证', proved: '已通过', accepted: '已通过', rejected: '已拒绝',
    assignments: { working: '已领取', submitted: '已提交', checking: '验证中' },
    run: '查看运行', latestRun: '最近运行', noRun: '暂无', attempt: '运行尝试',
    manifest: '查看证据清单', empty: '没有匹配的引理。', noRecords: '还没有权威验证记录。',
    count: n => '找到 ' + n + ' 条引理。',
    failure: '暂时无法获取实时数据。', published: '查看 GitHub 命题清单', actions: '查看 GitHub Actions',
    copied: '已复制', copyManual: '请复制已选中的提示词。',
    stale: '暂时无法刷新，正在显示上次获取的数据。',
    deskUnavailable: '暂时无法获取社区数据。',
    noActivity: '暂无参与记录。',
    noContributors: '暂无有署名的通过记录。',
    participant: '参与者',
    activities: {
      claimed: '领取引理', submitted: '登记提交', checking: '开始验证',
      released: '归还引理', accepted: '验证通过', rejected: '验证拒绝', expired: '任务凭证过期'
    },
    event: '任务状态更新',
    verifiedCount: n => '通过 ' + n + ' 条',
    pullRequest: '查看 PR',
    allPrograms: '全部路线',
    programCount: (verified, published) => verified + ' / ' + published + ' 已通过',
    pageRange: (first, last, total) => '第 ' + first + '–' + last + ' 条，共 ' + total + ' 条',
    shard: (lo, hi, index) => '分片 #' + index + '，闭区间 [' + lo + ', ' + hi + ']',
    file: '证明文件',
    copyLemma: '复制这条引理的参与提示词',
    occupied: '这条引理当前正在处理。',
    alreadyVerified: '这条引理已通过权威验证。',
    lemmaPrompt: id => '读取 https://www.movan.tech/goldbach/join-zh.txt，按指南用 python tools/goldbach.py claim ' + id + ' 领取并验证这一条引理。如果无法领取这条引理，请说明原因，不要改领其他题。'
  },
  en: {
    open: 'Open', proved: 'Verified', accepted: 'Accepted', rejected: 'Rejected',
    assignments: { working: 'Claimed', submitted: 'Submitted', checking: 'Checking' },
    run: 'View run', latestRun: 'Latest run', noRun: 'Pending', attempt: 'Attempt',
    manifest: 'View evidence manifest', empty: 'No matching lemmas.', noRecords: 'No authoritative runs have been recorded.',
    count: n => n === 1 ? '1 matching lemma.' : n + ' matching lemmas.',
    failure: 'Live data is temporarily unavailable.', published: 'View statements on GitHub', actions: 'View GitHub Actions',
    copied: 'Copied', copyManual: 'Copy the selected prompt.',
    stale: 'Refresh failed. Showing the last available data.',
    deskUnavailable: 'Community data is temporarily unavailable.',
    noActivity: 'No community activity yet.',
    noContributors: 'No attributed proofs have passed verification yet.',
    participant: 'Participant',
    activities: {
      claimed: 'Claimed a lemma', submitted: 'Registered a submission', checking: 'Started verification',
      released: 'Returned a lemma', accepted: 'Proof accepted', rejected: 'Proof rejected', expired: 'Lease expired'
    },
    event: 'Task status changed',
    verifiedCount: n => n === 1 ? '1 accepted' : n + ' accepted',
    pullRequest: 'View PR',
    allPrograms: 'All programs',
    programCount: (verified, published) => verified + ' / ' + published + ' verified',
    pageRange: (first, last, total) => first + '–' + last + ' of ' + total + ' lemmas',
    shard: (lo, hi, index) => 'Shard #' + index + ', inclusive range [' + lo + ', ' + hi + ']',
    file: 'Proof file',
    copyLemma: 'Copy this lemma’s join prompt',
    occupied: 'This lemma is currently in progress.',
    alreadyVerified: 'The authoritative verifier has accepted this lemma.',
    lemmaPrompt: id => 'Read https://www.movan.tech/goldbach/join.txt and follow it to claim and verify exactly ' + id + ' with python tools/goldbach.py claim ' + id + '. If that lemma is unavailable, report why and do not choose another.'
  }
}[lang];

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function anchor(label, href, className) {
  const link = element('a', label, className);
  link.href = href;
  return link;
}

function runLink(run, label) {
  return anchor(label + ' ↗', repository + '/actions/runs/' + run.run_id, 'evidence-link');
}

function verdictTag(label, status) {
  return element('span', label, status ? 'verdict verdict-' + status : 'verdict');
}

function isPrime(value) {
  if (value < 2) return false;
  for (let divisor = 2; divisor * divisor <= value; divisor += 1) {
    if (value % divisor === 0) return false;
  }
  return true;
}

const exampleButtons = Array.from(document.querySelectorAll('[data-example]'));

function renderExample(value) {
  const candidates = [];
  for (let number = 2; number < value; number += 1) {
    if (isPrime(number)) candidates.push(number);
  }
  const first = candidates.find(number => number <= value / 2 && candidates.includes(value - number));
  if (first === undefined) return;
  const other = value - first;
  document.getElementById('equation').replaceChildren(
    element('span', first), element('b', '+'), element('span', other),
    element('b', '='), element('span', value, 'target-value')
  );
  document.getElementById('number-axis').replaceChildren(
    ...candidates.map(number => element('span', number, number === first || number === other ? 'prime-used' : ''))
  );
  for (const button of exampleButtons) {
    button.setAttribute('aria-pressed', String(Number(button.dataset.example) === value));
  }
}

for (const button of exampleButtons) {
  button.addEventListener('click', () => renderExample(Number(button.dataset.example)));
}

const lemmaRows = document.getElementById('lemma-rows');
const lemmaSearch = document.getElementById('lemma-search');
const lemmaState = document.getElementById('lemma-state');
const verificationLog = document.getElementById('verification-log');
const deskNotice = document.getElementById('desk-notice');
const deskActivity = document.getElementById('desk-activity');
const deskLeaderboard = document.getElementById('desk-leaderboard');
const locale = document.documentElement.lang;
const eventTime = new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' });

const mapNodes = document.getElementById('map-nodes');
const mapContext = document.getElementById('map-context');
const mapReset = document.getElementById('map-reset');
const programButtons = Array.from(document.querySelectorAll('[data-program]'));
const programs = new Map(programButtons.map(button => [button.dataset.program, button]));
const lemmaDialog = document.getElementById('lemma-detail');
const detailContent = document.getElementById('lemma-detail-content');
const pageRange = document.getElementById('lemma-page-range');
const previousPage = document.getElementById('lemma-prev');
const nextPage = document.getElementById('lemma-next');
const pageSelect = document.getElementById('lemma-page');
const pageSize = 24;

let publishedGaps = [];
let assignments = {};
let selectedProgram = '';
let selectedGap = null;
let lemmaPage = 1;
let loading = false;
let lastGaps = null;
let lastResults = null;
let lastDesk = null;

function messageRow(label, link) {
  const row = element('tr');
  const cell = element('td', label, 'empty-state');
  cell.colSpan = 3;
  if (link) cell.append(link);
  row.append(cell);
  return row;
}

function programOf(gap) {
  return gap.program || 'foundation';
}

function programName(key) {
  return programs.get(key)?.querySelector('.program-name').textContent ?? '';
}

function assigned(gap) {
  return !gap.proved && Object.hasOwn(strings.assignments, assignments[gap.id]);
}

function gapStatus(gap) {
  if (gap.proved) return { label: strings.proved, kind: 'verified', style: 'accepted' };
  if (assigned(gap)) {
    return { label: strings.assignments[assignments[gap.id]], kind: 'occupied', style: 'in-progress' };
  }
  return { label: strings.open, kind: 'available', style: '' };
}

function shardText(gap) {
  const shard = gap.shard;
  if (!shard || ![shard.lo, shard.hi, shard.index].every(Number.isSafeInteger)) return '';
  return strings.shard(shard.lo, shard.hi, shard.index);
}

function renderProgramCounts() {
  const counts = new Map(Array.from(programs.keys(), key => [key, { published: 0, verified: 0 }]));
  for (const gap of publishedGaps) {
    const count = counts.get(programOf(gap));
    if (!count) continue;
    count.published += 1;
    if (gap.proved) count.verified += 1;
  }
  for (const [key, count] of counts) {
    programs.get(key).querySelector('.program-count').textContent = strings.programCount(count.verified, count.published);
  }
  const shards = publishedGaps.filter(gap => gap.program === 'coverage' && gap.shard)
    .sort((a, b) => a.shard.index - b.shard.index);
  const grid = document.getElementById('coverage-grid');
  grid.replaceChildren(...shards.map((gap, index) => {
    const status = gapStatus(gap);
    const tile = element('button', undefined, 'shard-tile ' + status.kind);
    tile.type = 'button';
    tile.tabIndex = index === 0 ? 0 : -1;
    tile.title = gap.shard.lo + '–' + gap.shard.hi + ' · ' + status.label;
    tile.setAttribute('aria-label', tile.title);
    tile.addEventListener('click', () => openGap(gap.id));
    return tile;
  }));
  const accepted = shards.filter(gap => gap.proved).length;
  const working = shards.filter(assigned).length;
  document.getElementById('coverage-summary').textContent = lang === 'zh'
    ? accepted + ' / ' + shards.length + ' 分片通过 · ' + working + ' 处理中'
    : accepted + ' / ' + shards.length + ' verified · ' + working + ' working';
}

document.getElementById('coverage-grid').addEventListener('keydown', event => {
  const steps = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -25, ArrowDown: 25 };
  if (!Object.hasOwn(steps, event.key)) return;
  event.preventDefault();
  const tiles = [...event.currentTarget.children];
  const index = Math.max(0, Math.min(tiles.length - 1, tiles.indexOf(event.target) + steps[event.key]));
  if (tiles[index]) {
    for (const tile of tiles) tile.tabIndex = -1;
    tiles[index].tabIndex = 0;
    tiles[index].focus();
  }
});

function chooseProgram(program) {
  selectedProgram = program;
  for (const [key, button] of programs) {
    button.setAttribute('aria-pressed', String(key === program));
  }
  mapContext.textContent = programName(program) || strings.allPrograms;
  mapReset.hidden = !program;
  lemmaPage = 1;
  if (lastGaps !== null) renderLemmas();
}

for (const [key, button] of programs) {
  button.addEventListener('click', () => chooseProgram(selectedProgram === key ? '' : key));
}
mapReset.addEventListener('click', () => {
  programs.get(selectedProgram)?.focus();
  chooseProgram('');
});

function openGap(id) {
  selectedGap = id;
  renderGapDetail();
  if (!lemmaDialog.open) lemmaDialog.showModal();
  detailContent.scrollTop = 0;
}

function renderGapDetail() {
  const gap = publishedGaps.find(entry => entry.id === selectedGap);
  if (!gap) return;
  const status = gapStatus(gap);
  const identity = element('div', undefined, 'detail-identity');
  identity.append(element('code', gap.id), verdictTag(status.label, status.style));
  const context = [programName(programOf(gap)), shardText(gap)].filter(Boolean).join(' · ');
  detailContent.replaceChildren(
    identity,
    element('h3', gap.plain_statement[lang]),
    element('p', context, 'detail-context'),
    element('pre', gap.statement, 'detail-statement')
  );

  if (gap.file) {
    const file = element('p', undefined, 'detail-file');
    file.append(element('strong', strings.file), element('code', gap.file));
    detailContent.append(file);
  }
  if (gap.latest) {
    detailContent.append(runLink(gap.latest, strings.latestRun));
  }
  if (gap.proved || assigned(gap)) {
    detailContent.append(element('p', gap.proved ? strings.alreadyVerified : strings.occupied, 'detail-context'));
    return;
  }
  const join = element('div', undefined, 'detail-join');
  const copy = element('button', strings.copyLemma, 'button button-primary');
  copy.type = 'button';
  const prompt = element('p', strings.lemmaPrompt(gap.id), 'join-prompt');
  const announcement = element('span', undefined, 'join-feedback');
  announcement.setAttribute('role', 'status');
  bindPromptCopy(copy, prompt, announcement);
  join.append(copy, prompt, announcement);
  detailContent.append(join);
}

lemmaDialog.addEventListener('close', () => { selectedGap = null; });

function lemmaRow(gap) {
  const row = element('tr');
  const claim = element('td');
  const button = element('button', gap.plain_statement[lang], 'statement-link');
  button.type = 'button';
  button.addEventListener('click', () => openGap(gap.id));
  claim.append(element('code', gap.id, 'statement-id'), button);
  const context = [programName(programOf(gap)), shardText(gap)].filter(Boolean).join(' · ');
  if (context) claim.append(element('span', context, 'row-context'));

  const statusCell = element('td');
  const status = gapStatus(gap);
  statusCell.append(verdictTag(status.label, status.style));
  const evidence = element('td');
  if (gap.latest) {
    evidence.append(runLink(gap.latest, strings.latestRun));
  } else {
    evidence.append(element('span', strings.noRun));
  }
  row.append(claim, statusCell, evidence);
  return row;
}

function mapNode(gap) {
  const status = gapStatus(gap);
  const button = element('button', undefined, 'map-node');
  const dot = element('span', undefined, 'map-dot ' + status.kind);
  dot.setAttribute('aria-hidden', 'true');
  button.type = 'button';
  button.setAttribute('aria-label', gap.id + ' · ' + status.label);
  button.title = gap.plain_statement[lang];
  button.append(dot, element('code', gap.id.replace(/^L-goldbach-/, '')));
  button.addEventListener('click', () => openGap(gap.id));
  return button;
}

const graph = document.getElementById('network-map');
const palette = { available: '#a6ae9e', occupied: '#f2be63', verified: '#86ca92' };
let graphGaps = [];
let graphTargets = [];
function drawNetwork() {
  const w = graph.clientWidth;
  const h = graph.clientHeight;
  const ctx = graph.getContext('2d');
  if (!ctx || !w || !h) return;
  const scale = Math.min(window.devicePixelRatio || 1, 2);
  graph.width = Math.round(w * scale);
  graph.height = Math.round(h * scale);
  ctx.scale(scale, scale);
  graphTargets = [];
  const center = { x: w / 2, y: h / 2 };
  function edge(a, b, color) {
    ctx.strokeStyle = color;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  }
  function dot(p, radius, color) {
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(p.x, p.y, radius, 0, 2 * Math.PI); ctx.fill();
  }
  function caption(p, text) {
    ctx.font = '500 13px system-ui, sans-serif';
    ctx.textAlign = 'center';
    const width = ctx.measureText(text).width;
    ctx.fillStyle = '#222421'; ctx.fillRect(p.x - width / 2 - 4, p.y - 9, width + 8, 18);
    ctx.fillStyle = '#f3eee0'; ctx.fillText(text, p.x, p.y + 4);
  }
  const keys = selectedProgram ? [selectedProgram] : [...programs.keys()];
  keys.forEach((key, index) => {
    const gaps = graphGaps.filter(gap => programOf(gap) === key);
    if (!gaps.length) return;
    const hub = selectedProgram ? center : {
      x: w * (index % 2 ? 0.75 : 0.25), y: h * (index < 2 ? 0.25 : 0.75)
    };
    if (!selectedProgram) edge(center, hub, '#7b806c');
    const radiusX = w * (selectedProgram ? .44 : .19);
    const radiusY = h * (selectedProgram ? .43 : .20);
    gaps.forEach((gap, i) => {
      const angle = i * Math.PI * (3 - Math.sqrt(5));
      const radius = Math.sqrt((i + 1) / gaps.length);
      const p = { x: hub.x + radius * radiusX * Math.cos(angle),
        y: hub.y + radius * radiusY * Math.sin(angle) };
      edge(hub, p, '#43493e');
      dot(p, selectedProgram ? 4 : 3, palette[gapStatus(gap).kind]);
      graphTargets.push({ ...p, gap, radius: 7 });
    });
    caption(hub, programName(key));
    graphTargets.push({ ...hub, program: key, radius: 15 });
  });
  if (!selectedProgram || !graphGaps.length) {
    caption(center, graphGaps.length ? (lang === 'zh' ? '强哥德巴赫' : 'Binary Goldbach') : strings.empty);
  }
}
function graphTarget(event) {
  const bounds = graph.getBoundingClientRect();
  const x = event.clientX - bounds.left;
  const y = event.clientY - bounds.top;
  let nearest, distance = Infinity;
  for (const target of graphTargets) {
    const d = Math.hypot(x - target.x, y - target.y);
    if (d <= target.radius && d < distance) { nearest = target; distance = d; }
  }
  return nearest;
}
graph.addEventListener('pointermove', event => {
  const target = graphTarget(event);
  graph.style.cursor = target ? 'pointer' : 'default';
  graph.title = target?.gap?.plain_statement[lang] || (target ? programName(target.program) : '');
});
graph.addEventListener('click', event => {
  const target = graphTarget(event);
  if (target?.gap) openGap(target.gap.id);
  else if (target) chooseProgram(selectedProgram ? '' : target.program);
});
new ResizeObserver(drawNetwork).observe(graph);

function renderLemmas() {
  const query = lemmaSearch.value.trim().toLocaleLowerCase();
  const selection = lemmaState.value;
  const visibleGaps = publishedGaps.filter(gap => {
    if (selectedProgram && programOf(gap) !== selectedProgram) return false;
    if (selection === 'proved' && !gap.proved) return false;
    if (selection === 'open' && gap.proved) return false;
    if (selection === 'progress' && !assigned(gap)) return false;
    if (selection === 'available' && (gap.proved || assigned(gap))) return false;
    if (!query) return true;
    const program = programOf(gap);
    const content = [
      gap.id, gap.statement, gap.plain_statement.zh, gap.plain_statement.en,
      program, programName(program), shardText(gap)
    ];
    return content.some(text => text.toLocaleLowerCase().includes(query));
  });
  graphGaps = visibleGaps;
  drawNetwork();
  const maxPage = Math.max(1, Math.ceil(visibleGaps.length / pageSize));
  lemmaPage = Math.min(lemmaPage, maxPage);
  const offset = (lemmaPage - 1) * pageSize;
  const current = visibleGaps.slice(offset, offset + pageSize);
  mapNodes.replaceChildren(...current.map(mapNode));
  lemmaRows.replaceChildren(...(current.length ? current.map(lemmaRow) : [messageRow(strings.empty)]));
  pageRange.textContent = current.length ? strings.pageRange(offset + 1, offset + current.length, visibleGaps.length) : strings.empty;
  previousPage.disabled = lemmaPage === 1;
  nextPage.disabled = lemmaPage === maxPage;
  pageSelect.disabled = maxPage === 1;
  if (pageSelect.options.length !== maxPage) {
    pageSelect.replaceChildren(...Array.from({ length: maxPage }, (_, index) => new Option(index + 1, index + 1)));
  }
  pageSelect.value = String(lemmaPage);
}

function setPage(page) {
  lemmaPage = page;
  renderLemmas();
}

previousPage.addEventListener('click', () => setPage(lemmaPage - 1));
nextPage.addEventListener('click', () => setPage(lemmaPage + 1));
pageSelect.addEventListener('change', () => setPage(Number(pageSelect.value)));

function renderLogEntry(run) {
  const article = element('article');
  article.dataset.run = run.run_id + '/' + run.run_attempt;
  const row = element('div', undefined, 'log-entry');
  const judgement = run.verdict === 'ACCEPTED' ? 'accepted' : 'rejected';
  const label = element('div');
  label.append(
    element('code', run.lemma_id, 'log-id'),
    element('span', strings.attempt + ' ' + run.run_attempt + ' · #' + run.run_id, 'log-note')
  );
  row.append(label, verdictTag(strings[judgement], judgement), runLink(run, strings.run));
  article.append(row);
  if (run.manifest) {
    const details = element('details', undefined, 'manifest');
    details.append(
      element('summary', strings.manifest),
      element('pre', JSON.stringify(run.manifest, null, 2))
    );
    article.append(details);
  }
  return article;
}

function renderActivity(event) {
  const item = element('li', undefined, 'activity-item');
  const details = element('div', undefined, 'activity-details');
  const label = Object.hasOwn(strings.activities, event.kind) ? strings.activities[event.kind] : strings.event;
  const byline = element('div', undefined, 'activity-byline');
  byline.append(element('span', event.handle || strings.participant), element('code', event.lemma_id));
  details.append(element('strong', label), byline);

  const links = element('div', undefined, 'activity-links');
  const date = new Date(typeof event.at === 'number' ? event.at * 1000 : event.at);
  if (Number.isFinite(date.getTime())) {
    const timestamp = element('time', eventTime.format(date));
    timestamp.dateTime = date.toISOString();
    links.append(timestamp);
  }
  if (Number.isSafeInteger(event.run_id) && event.run_id > 0) {
    links.append(runLink(event, strings.run));
  } else if (Number.isSafeInteger(event.pr) && event.pr > 0) {
    links.append(anchor(strings.pullRequest + ' ↗', repository + '/pull/' + event.pr, 'evidence-link'));
  }
  item.append(details, links);
  return item;
}

function renderContributor(contributor, position) {
  const item = element('li', undefined, 'contributor-item');
  const name = '@' + contributor.handle;
  const profile = anchor(name, 'https://github.com/' + encodeURIComponent(contributor.handle), 'contributor-name');
  item.append(
    element('span', position + 1, 'contributor-position'),
    profile,
    element('span', strings.verifiedCount(contributor.accepted), 'contributor-score')
  );
  return item;
}

function showDeskNotice(message) {
  if (deskNotice.textContent !== message) deskNotice.textContent = message;
  deskNotice.hidden = !message;
}

function renderDesk(desk) {
  if (!desk) {
    showDeskNotice(lastDesk === null ? strings.deskUnavailable : strings.stale);
    if (lastDesk === null) {
      deskActivity.replaceChildren();
      deskLeaderboard.replaceChildren();
    }
    return;
  }
  showDeskNotice('');
  const snapshot = JSON.stringify(desk);
  if (lastDesk === snapshot) return;
  lastDesk = snapshot;
  document.getElementById('desk-active').textContent = desk.active.toLocaleString(locale);
  document.getElementById('live-hero').textContent = desk.active.toLocaleString(locale);
  document.getElementById('hero-sessions').textContent = desk.sessions.toLocaleString(locale);
  const frontier = document.getElementById('frontier-events');
  frontier.replaceChildren(...desk.activities.slice(0, 2).map(activity => {
    const item = element('div', undefined, 'frontier-entry');
    item.append(element('small', eventTime.format(new Date(activity.at * 1000))),
      element('strong', strings.activities[activity.kind] || strings.event),
      element('code', activity.lemma_id));
    return item;
  }));
  if (!desk.activities.length) frontier.textContent = strings.noActivity;
  document.getElementById('desk-sessions').textContent = desk.sessions.toLocaleString(locale);
  deskActivity.replaceChildren(...(desk.activities.length
    ? desk.activities.map(renderActivity) : [element('li', strings.noActivity, 'empty-state')]));
  deskLeaderboard.replaceChildren(...(desk.leaderboard.length
    ? desk.leaderboard.map(renderContributor) : [element('li', strings.noContributors, 'empty-state')]));
}

function renderResults(results) {
  const snapshot = JSON.stringify(results);
  if (lastResults === snapshot) return;
  lastResults = snapshot;
  const expanded = new Set(Array.from(
    verificationLog.querySelectorAll('details[open]'), details => details.parentElement.dataset.run
  ));
  const entries = results.map(run => {
    const entry = renderLogEntry(run);
    if (expanded.has(entry.dataset.run)) {
      const manifest = entry.querySelector('details');
      if (manifest) manifest.open = true;
    }
    return entry;
  });
  verificationLog.replaceChildren(...(entries.length ? entries : [element('p', strings.noRecords, 'empty-state')]));
}

lemmaSearch.addEventListener('input', () => setPage(1));
lemmaState.addEventListener('change', () => setPage(1));

document.addEventListener('keydown', event => {
  if (event.key !== '/' || event.altKey || event.ctrlKey || event.metaKey ||
      lemmaDialog.open || lemmaSearch.disabled || event.target.closest('input, textarea, select, [contenteditable]')) return;
  event.preventDefault();
  lemmaSearch.focus();
});

async function loadStatus() {
  if (loading || document.hidden) return;
  loading = true;
  const request = new AbortController();
  const timeout = window.setTimeout(() => request.abort(), 10000);
  try {
    const response = await fetch('api/status', {
      headers: { Accept: 'application/json' },
      signal: request.signal,
    });
    if (!response.ok) throw new Error('Status request failed');
    const { gaps, counts, results, desk } = await response.json();
    assignments = desk?.assignments ?? assignments;
    document.getElementById('hero-available').textContent = gaps.filter(gap => !gap.proved && !assigned(gap)).length;
    const latest = results[0];
    document.getElementById('news-verdict').textContent = latest
      ? latest.lemma_id + ' · ' + (latest.verdict === 'ACCEPTED' ? strings.accepted : strings.rejected)
      : strings.noRecords;
    const gapsSnapshot = JSON.stringify([gaps, assignments]);
    if (lastGaps !== gapsSnapshot) {
      publishedGaps = gaps;
      renderProgramCounts();
      renderLemmas();
      if (lemmaDialog.open) renderGapDetail();
      lastGaps = gapsSnapshot;
    }
    lemmaSearch.disabled = false;
    lemmaState.disabled = false;
    for (const name of ['accepted', 'open', 'published', 'attempts']) {
      document.getElementById('count-' + name).textContent = counts[name].toLocaleString(locale);
    }
    renderResults(results);
    renderDesk(desk);
  } catch {
    if (lastGaps === null) {
      lemmaRows.replaceChildren(messageRow(strings.failure, anchor(strings.published, repository + '/blob/main/research/gaps.json')));
      lemmaSearch.disabled = true;
      lemmaState.disabled = true;
    }
    if (lastResults === null) {
      const error = element('p', strings.failure, 'empty-state');
      error.append(anchor(strings.actions, repository + '/actions'));
      verificationLog.replaceChildren(error);
    }
    renderDesk(null);
  } finally {
    window.clearTimeout(timeout);
    loading = false;
  }
}

function bindPromptCopy(button, prompt, announcement) {
  const label = button.textContent;
  let reset;
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(prompt.textContent);
      button.textContent = strings.copied;
      announcement.textContent = strings.copied;
      window.clearTimeout(reset);
      reset = window.setTimeout(() => {
        button.textContent = label;
        announcement.textContent = '';
      }, 1900);
    } catch {
      const disclosure = prompt.closest('details');
      if (disclosure) disclosure.open = true;
      const range = document.createRange();
      range.selectNodeContents(prompt);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      announcement.textContent = strings.copyManual;
    }
  });
}

bindPromptCopy(
  document.getElementById('copy-prompt'),
  document.getElementById('agent-prompt'),
  document.getElementById('copy-announcement')
);

loadStatus();
window.setInterval(loadStatus, 45000);
document.addEventListener('visibilitychange', loadStatus);
