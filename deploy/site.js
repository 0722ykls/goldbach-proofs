'use strict';

const lang = document.documentElement.lang.startsWith('zh') ? 'zh' : 'en';
const repository = 'https://github.com/CGandGameEngineLearner/goldbach-proofs';
const strings = {
  zh: {
    open: '待证', proved: '已通过', accepted: '已通过', rejected: '已拒绝',
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
    pullRequest: '查看 PR'
  },
  en: {
    open: 'Open', proved: 'Verified', accepted: 'Accepted', rejected: 'Rejected',
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
    pullRequest: 'View PR'
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

let publishedGaps = [];
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

function lemmaRow(gap) {
  const row = element('tr');
  const claim = element('td');
  claim.append(
    element('code', gap.id, 'statement-id'),
    element('span', gap.plain_statement[lang]),
    element('code', gap.statement, 'formal-statement')
  );
  const status = element('td');
  status.append(verdictTag(gap.proved ? strings.proved : strings.open, gap.proved ? 'accepted' : ''));
  const evidence = element('td');
  if (gap.latest) {
    evidence.append(runLink(gap.latest, strings.latestRun));
  } else {
    evidence.append(element('span', strings.noRun));
  }
  row.append(claim, status, evidence);
  return row;
}

function renderLemmas() {
  const query = lemmaSearch.value.trim().toLocaleLowerCase();
  const selection = lemmaState.value;
  const visibleGaps = publishedGaps.filter(gap => {
    if (selection === 'proved' && !gap.proved) return false;
    if (selection === 'open' && gap.proved) return false;
    const content = [gap.id, gap.statement, gap.plain_statement.zh, gap.plain_statement.en];
    return content.some(text => text.toLocaleLowerCase().includes(query));
  });
  lemmaRows.replaceChildren(...(visibleGaps.length ? visibleGaps.map(lemmaRow) : [messageRow(strings.empty)]));
  document.getElementById('lemma-announcement').textContent = strings.count(visibleGaps.length);
}

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

lemmaSearch.addEventListener('input', renderLemmas);
lemmaState.addEventListener('change', renderLemmas);

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
    const gapsSnapshot = JSON.stringify(gaps);
    if (lastGaps !== gapsSnapshot) {
      publishedGaps = gaps;
      renderLemmas();
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

const copyButton = document.getElementById('copy-prompt');
const copyLabel = copyButton.textContent;
const announcement = document.getElementById('copy-announcement');
let resetCopy;

copyButton.addEventListener('click', async () => {
  const prompt = document.getElementById('agent-prompt');
  try {
    await navigator.clipboard.writeText(prompt.textContent);
    copyButton.textContent = strings.copied;
    announcement.textContent = strings.copied;
    clearTimeout(resetCopy);
    resetCopy = setTimeout(() => {
      copyButton.textContent = copyLabel;
      announcement.textContent = '';
    }, 1700);
  } catch {
    const range = document.createRange();
    range.selectNodeContents(prompt);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    announcement.textContent = strings.copyManual;
  }
});

loadStatus();
window.setInterval(loadStatus, 45000);
document.addEventListener('visibilitychange', loadStatus);
