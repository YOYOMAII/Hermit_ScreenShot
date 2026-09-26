/** Save a same-origin file without relying on navigation (works in pywebview). */
async function hermitDownload(url, filename) {
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
      await hermitDownload(href, name);
      if (onSuccess) onSuccess(name);
    } catch (error) {
      if (onError) onError(error);
      else window.location.assign(href);
    } finally {
      link.classList.remove('is-busy');
      link.removeAttribute('aria-busy');
    }
  });
}

window.wireHermitDownloadLink = wireHermitDownloadLink;
