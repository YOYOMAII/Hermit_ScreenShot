/** Save files in the browser or via the desktop app native Save dialog. */

function waitForDesktopApi(timeoutMs = 8000) {
  return new Promise(resolve => {
    if (window.pywebview?.api?.save_download) {
      resolve(window.pywebview.api);
      return;
    }
    const onReady = () => {
      window.removeEventListener('pywebviewready', onReady);
      resolve(window.pywebview?.api?.save_download ? window.pywebview.api : null);
    };
    window.addEventListener('pywebviewready', onReady);
    window.setTimeout(() => {
      window.removeEventListener('pywebviewready', onReady);
      resolve(window.pywebview?.api?.save_download ? window.pywebview.api : null);
    }, timeoutMs);
  });
}

async function hermitDownload(url, filename) {
  const api = await waitForDesktopApi();
  if (api?.save_download) {
    const result = await api.save_download(url, filename || 'download');
    if (result?.cancelled) {
      const err = new Error('Save cancelled');
      err.cancelled = true;
      throw err;
    }
    if (!result?.ok) {
      throw new Error(result?.error || 'Could not save file.');
    }
    return { mode: 'desktop', path: result.path };
  }

  const absolute = new URL(url, window.location.href).href;
  const response = await fetch(absolute, { credentials: 'same-origin' });
  if (!response.ok) {
    throw new Error('Could not download file. Try again.');
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename || 'download';
  link.style.display = 'none';
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
  return { mode: 'browser' };
}

window.hermitDownload = hermitDownload;

function wireHermitDownloadLink(link, { onSuccess, onError } = {}) {
  if (!link) return;
  link.addEventListener('click', async event => {
    const href = link.getAttribute('href');
    if (!href || href === '#') return;
    event.preventDefault();
    const name = link.getAttribute('download') || '';
    link.classList.add('is-busy');
    link.setAttribute('aria-busy', 'true');
    try {
      const result = await hermitDownload(href, name);
      if (onSuccess) onSuccess(name, result);
    } catch (error) {
      if (error.cancelled) return;
      if (onError) onError(error);
      else window.location.assign(href);
    } finally {
      link.classList.remove('is-busy');
      link.removeAttribute('aria-busy');
    }
  });
}

window.wireHermitDownloadLink = wireHermitDownloadLink;
