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
    copied: '已复制', copyManual: '请复制已选中的任务说明。'
  },
  en: {
    open: 'Open', proved: 'Verified', accepted: 'Accepted', rejected: 'Rejected',
    run: 'View run', latestRun: 'Latest run', noRun: 'Pending', attempt: 'Attempt',
    manifest: 'View evidence manifest', empty: 'No matching lemmas.', noRecords: 'No authoritative runs have been recorded.',
    count: n => n === 1 ? '1 matching lemma.' : n + ' matching lemmas.',
    failure: 'Live data is temporarily unavailable.', published: 'View statements on GitHub', actions: 'View GitHub Actions',
    copied: 'Copied', copyManual: 'Copy the selected instructions.'
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
let publishedGaps = [];

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

async function loadStatus() {
  try {
    const response = await fetch('api/status', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error('Status request failed');
    const { gaps, counts, results } = await response.json();
    publishedGaps = gaps;
    renderLemmas();
    for (const name of ['accepted', 'open', 'published', 'attempts']) {
      document.getElementById('count-' + name).textContent = counts[name].toLocaleString(document.documentElement.lang);
    }
    verificationLog.replaceChildren(...(results.length ? results.map(renderLogEntry) : [element('p', strings.noRecords, 'empty-state')]));
    lemmaSearch.addEventListener('input', renderLemmas);
    lemmaState.addEventListener('change', renderLemmas);
  } catch {
    lemmaRows.replaceChildren(messageRow(strings.failure, anchor(strings.published, repository + '/blob/main/research/gaps.json')));
    const error = element('p', strings.failure, 'empty-state');
    error.append(anchor(strings.actions, repository + '/actions'));
    verificationLog.replaceChildren(error);
    lemmaSearch.disabled = true;
    lemmaState.disabled = true;
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

