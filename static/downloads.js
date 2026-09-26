/** Save files: desktop app writes straight to Downloads; browsers use a normal download. */

const isDesktopApp = document.body?.dataset.desktop === '1';

function waitForDesktopApi(timeoutMs = 8000) {
  return new Promise(resolve => {
    const ready = () => (window.pywebview?.api?.save_download ? window.pywebview.api : null);
    if (ready()) {
      resolve(ready());
      return;
    }
    const onReady = () => {
      window.removeEventListener('pywebviewready', onReady);
      resolve(ready());
    };
    window.addEventListener('pywebviewready', onReady);
    window.setTimeout(() => {
      window.removeEventListener('pywebviewready', onReady);
      resolve(ready());
    }, timeoutMs);
  });
}

async function hermitDownload(url, filename) {
  if (isDesktopApp) {
    const api = await waitForDesktopApi();
    if (!api) throw new Error('The app is still starting. Wait a moment and click Download again.');
    const result = await api.save_download(url, filename || 'download');
    if (!result?.ok) throw new Error(result?.error || 'Could not save file.');
    return { mode: 'desktop', ...result };
  }

  const absolute = new URL(url, window.location.href).href;
  const response = await fetch(absolute, { credentials: 'same-origin' });
  if (response.status === 404) throw new Error('This file has expired. Build it again.');
  if (!response.ok) throw new Error('Could not download file. Try again.');
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename || 'download';
  link.style.display = 'none';
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
  return { mode: 'browser', name: filename || 'download' };
}

window.hermitDownload = hermitDownload;

let savedNotice = null;

function noticeButton(label, onClick) {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = label;
  button.addEventListener('click', onClick);
  return button;
}

function showSavedNotice(result, error) {
  savedNotice?.remove();
  const notice = document.createElement('div');
  notice.className = `saved-notice${error ? ' is-error' : ''}`;
  notice.setAttribute('role', error ? 'alert' : 'status');

  const text = document.createElement('div');
  text.className = 'saved-notice-text';
  const title = document.createElement('strong');
  const detail = document.createElement('span');
  if (error) {
    title.textContent = 'Download failed';
    detail.textContent = error.message;
  } else if (result.mode === 'desktop') {
    title.textContent = `Saved to ${result.folder}`;
    detail.textContent = result.name;
    detail.title = result.path;
  } else {
    title.textContent = 'Downloaded';
    detail.textContent = `${result.name} — check your Downloads folder.`;
  }
  text.append(title, detail);

  const actions = document.createElement('div');
  actions.className = 'saved-notice-actions';
  if (!error && result.mode === 'desktop') {
    const api = window.pywebview.api;
    const run = async call => {
      const outcome = await call(result.path);
      if (!outcome?.ok) detail.textContent = outcome?.error || 'Could not open the file.';
    };
    const folderLabel = result.platform === 'darwin' ? 'Show in Finder'
      : result.platform === 'win32' ? 'Show in folder' : 'Open folder';
    actions.append(
      noticeButton('Open', () => run(api.open_file)),
      noticeButton(folderLabel, () => run(api.show_in_folder)),
    );
  }
  const close = noticeButton('×', () => notice.remove());
  close.className = 'saved-notice-close';
  close.setAttribute('aria-label', 'Close');
  actions.append(close);

  notice.append(text, actions);
  (document.querySelector('.app-shell') || document.body).append(notice);
  savedNotice = notice;
}

window.showSavedNotice = showSavedNotice;

function wireHermitDownloadLink(link) {
  if (!link) return;
  link.addEventListener('click', async event => {
    const href = link.getAttribute('href');
    event.preventDefault();
    if (!href || href === '#' || link.classList.contains('is-busy')) return;
    const name = link.getAttribute('download') || '';
    link.classList.add('is-busy');
    link.setAttribute('aria-busy', 'true');
    try {
      showSavedNotice(await hermitDownload(href, name));
    } catch (error) {
      showSavedNotice(null, error);
    } finally {
      link.classList.remove('is-busy');
      link.removeAttribute('aria-busy');
    }
  });
}

window.wireHermitDownloadLink = wireHermitDownloadLink;
