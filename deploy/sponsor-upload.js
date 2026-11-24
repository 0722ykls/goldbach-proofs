const logoForm = document.querySelector('#logo-upload');
if (logoForm) {
  const input = logoForm.elements.logo;
  const feedback = logoForm.querySelector('[role="alert"]');
  const button = logoForm.querySelector('button');
  const zh = document.documentElement.lang === 'zh';
  const label = button.textContent;
  const t = (chinese, english) => zh ? chinese : english;

  function showError(message, signIn = false) {
    feedback.textContent = message;
    if (signIn) {
      const link = document.createElement('a');
      link.href = '/auth/zhihu/sponsors?lang=' + (zh ? 'zh' : 'en');
      link.textContent = t('打开登录页', 'Open the sign-in page');
      feedback.append(' ', link);
    }
    feedback.hidden = false;
  }

  function validSize() {
    feedback.hidden = true;
    if (input.files[0]?.size > Number(logoForm.dataset.maxBytes)) {
      showError(t('文件超过 4 MiB，请压缩或换一张图片。', 'The file exceeds 4 MiB. Compress it or choose another image.'));
      return false;
    }
    return true;
  }

  input.addEventListener('change', validSize);
  logoForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (button.disabled || !validSize()) return;
    button.disabled = true;
    button.textContent = t('正在提交…', 'Submitting…');
    const fallback = t('提交未完成，请检查连接后重试。', 'Submission incomplete. Check your connection and retry.');
    try {
      const result = await fetch(logoForm.action, {
        method: 'POST',
        body: new FormData(logoForm),
        signal: AbortSignal.timeout(30000),
      });
      if (result.ok && result.redirected) {
        location.assign(result.url);
        return;
      }
      const response = new DOMParser().parseFromString(await result.text(), 'text/html');
      showError(response.querySelector('[role="alert"]')?.textContent || fallback, result.status === 403);
    } catch {
      showError(fallback);
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  });
}
