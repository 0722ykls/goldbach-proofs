const discussion = document.querySelector('.discussion-widget');
if (discussion) {
  const roomy = window.matchMedia('(min-width: 1200px) and (min-height: 650px)');
  const setting = 'goldbach-discussion-open';
  function fitDiscussion() {
    let preference = null;
    try { preference = sessionStorage.getItem(setting); } catch {}
    discussion.open = preference === null ? roomy.matches : preference === 'yes';
  }
  fitDiscussion();
  roomy.addEventListener('change', fitDiscussion);
  discussion.querySelector('summary').addEventListener('click', () => {
    try { sessionStorage.setItem(setting, discussion.open ? 'no' : 'yes'); } catch {}
  });
}
