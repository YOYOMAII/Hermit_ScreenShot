const form = document.querySelector('#render-form');
const themeSelect = document.querySelector('#screenshot-theme');
const previewStage = document.querySelector('#preview-stage');
const input = document.querySelector('#files');
const dropzone = document.querySelector('#dropzone');
const fileList = document.querySelector('#file-list');
const error = document.querySelector('#form-error');
const button = document.querySelector('#render-button');
const buttonLabel = document.querySelector('#render-button .button-label');
const buttonSpinner = document.querySelector('#render-button .button-spinner');
const buttonIcon = document.querySelector('#render-button .button-icon');
const previewLoading = document.querySelector('#preview-loading');
const emptyState = document.querySelector('#empty-state');
const result = document.querySelector('#result');
const previewImage = document.querySelector('#preview-image');
const zoomOut = document.querySelector('#zoom-out');
const zoomIn = document.querySelector('#zoom-in');
const zoomLevel = document.querySelector('#zoom-level');
const ZOOM_STEPS = [1, 1.5, 2, 3, 4];
const count = document.querySelector('#preview-count');
const controls = document.querySelector('#result-controls');
const strip = document.querySelector('#thumbnail-strip');
const position = document.querySelector('#image-position');
const previous = document.querySelector('#previous');
const next = document.querySelector('#next');
const currentDownload = document.querySelector('#download-current');
const allDownload = document.querySelector('#download-all');

let selectedFiles = [];
let images = [];
let active = 0;
let zoomStep = 0;

const MAX_FILES = 20;
const MAX_UPLOAD_BYTES = 40 * 1024 * 1024;

function showError(message) {
  error.textContent = message;
  error.hidden = !message;
}

const defaultPreviewCount = count.textContent;

function setGenerating(active) {
  button.disabled = active;
  button.classList.toggle('is-loading', active);
  button.setAttribute('aria-busy', active ? 'true' : 'false');
  if (buttonLabel) buttonLabel.textContent = active ? 'Generating…' : 'Generate screenshots';
  if (buttonSpinner) buttonSpinner.hidden = !active;
  if (buttonIcon) buttonIcon.hidden = active;
  previewStage.classList.toggle('is-generating', active);
  previewLoading.hidden = !active;
  previewLoading.setAttribute('aria-busy', active ? 'true' : 'false');
  if (active) {
    count.textContent = 'Generating…';
    emptyState.hidden = true;
    result.hidden = true;
    controls.hidden = true;
    strip.hidden = true;
  }
}

async function postForm(url, data, fallback) {
  let response;
  try {
    response = await fetch(url, { method: 'POST', body: data });
  } catch {
    throw new Error('Could not reach Hermit. Check that "python app.py" is still running, then try again.');
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || fallback);
  return payload;
}

function setFiles(files) {
  const all = [...files];
  selectedFiles = all.filter(file => /\.(html|css)$/i.test(file.name));
  fileList.replaceChildren();
  for (const file of selectedFiles) {
    const item = document.createElement('li');
    const badge = document.createElement('span');
    const name = document.createElement('span');
    badge.className = 'file-badge';
    badge.textContent = file.name.toLowerCase().endsWith('.css') ? 'CSS' : 'HTML';
    name.textContent = file.name;
    item.append(badge, name);
    fileList.append(item);
  }
  const skipped = all.length - selectedFiles.length;
  showError(skipped ? `Skipped ${skipped} file${skipped === 1 ? '' : 's'} that ${skipped === 1 ? 'is' : 'are'} not .html or .css.` : '');
}

input.addEventListener('change', () => setFiles(input.files));
for (const eventName of ['dragenter', 'dragover']) {
  dropzone.addEventListener(eventName, event => {
    event.preventDefault();
    dropzone.classList.add('dragging');
  });
}
for (const eventName of ['dragleave', 'drop']) {
  dropzone.addEventListener(eventName, event => {
    event.preventDefault();
    dropzone.classList.remove('dragging');
  });
}
dropzone.addEventListener('drop', event => setFiles(event.dataTransfer.files));

function applyScreenshotPreviewTheme() {
  const isDarkScreenshot = themeSelect.value === 'dark';
  previewStage.classList.toggle('ss-theme-dark', isDarkScreenshot);
}

themeSelect.addEventListener('change', applyScreenshotPreviewTheme);
applyScreenshotPreviewTheme();

function showImage(index) {
  active = index;
  const image = images[index];
  previewImage.src = image.url;
  previewImage.alt = `Code screenshot ${image.name}`;
  position.textContent = `${index + 1} / ${images.length}`;
  currentDownload.href = image.url;
  currentDownload.download = image.name;
  previous.disabled = index === 0;
  next.disabled = index === images.length - 1;
  [...strip.children].forEach((child, childIndex) => {
    child.classList.toggle('active', childIndex === index);
    child.setAttribute('aria-current', childIndex === index ? 'true' : 'false');
  });
}
previous.addEventListener('click', () => showImage(Math.max(0, active - 1)));
next.addEventListener('click', () => showImage(Math.min(images.length - 1, active + 1)));

// Zoom is relative to the size that fits the whole image in the stage.
function applyZoom(scrollToStart = false) {
  const zoom = ZOOM_STEPS[zoomStep];
  zoomLevel.textContent = zoom === 1 ? 'Fit' : `${zoom}×`;
  zoomOut.disabled = zoomStep === 0;
  zoomIn.disabled = zoomStep === ZOOM_STEPS.length - 1;
  result.classList.toggle('zoomed', zoom > 1);
  if (zoom === 1 || !previewImage.naturalWidth) {
    previewImage.style.width = '';
    return;
  }
  const available = Math.min(
    (result.clientWidth - 32) / previewImage.naturalWidth,
    (result.clientHeight - 32) / previewImage.naturalHeight,
  );
  previewImage.style.width = `${Math.round(previewImage.naturalWidth * available * zoom)}px`;
  if (scrollToStart) {
    // Code starts at the left edge, so show that side first.
    result.scrollLeft = 0;
    result.scrollTop = (result.scrollHeight - result.clientHeight) / 2;
  }
}

function setZoom(step) {
  zoomStep = Math.max(0, Math.min(ZOOM_STEPS.length - 1, step));
  result.classList.remove('zoomed');
  previewImage.style.width = '';
  applyZoom(true);
}

zoomOut.addEventListener('click', () => setZoom(zoomStep - 1));
zoomIn.addEventListener('click', () => setZoom(zoomStep + 1));
previewImage.addEventListener('click', () => setZoom(zoomStep ? 0 : 2));
previewImage.addEventListener('load', () => applyZoom(true));
window.addEventListener('resize', () => applyZoom());

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!selectedFiles.length) {
    showError('Choose at least one HTML or CSS file.');
    return;
  }
  if (selectedFiles.length > MAX_FILES) {
    showError(`Choose up to ${MAX_FILES} files per batch.`);
    return;
  }
  if (selectedFiles.reduce((total, file) => total + file.size, 0) > MAX_UPLOAD_BYTES) {
    showError('These files are larger than 40 MB together. Upload fewer at a time.');
    return;
  }
  showError('');
  setGenerating(true);
  const data = new FormData(form);
  data.delete('files');
  for (const file of selectedFiles) data.append('files', file, file.name);
  try {
    const payload = await postForm('/api/render', data, 'Could not render these files.');
    images = payload.images;
    strip.replaceChildren();
    for (const [index, image] of images.entries()) {
      const thumbnail = document.createElement('button');
      thumbnail.type = 'button';
      thumbnail.setAttribute('aria-label', `Show ${image.name}`);
      const picture = document.createElement('img');
      picture.src = image.url;
      picture.alt = '';
      thumbnail.append(picture);
      thumbnail.addEventListener('click', () => showImage(index));
      strip.append(thumbnail);
    }
    emptyState.hidden = true;
    result.hidden = false;
    controls.hidden = false;
    strip.hidden = false;
    count.textContent = `${images.length} image${images.length === 1 ? '' : 's'} ready · download within ${count.dataset.keep}`;
    allDownload.href = payload.zip_url;
    allDownload.download = payload.zip_name || 'screenshots.zip';
    zoomStep = 0;
    showImage(0);
    applyZoom();
    requestAnimationFrame(() => {
      controls.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    });
  } catch (failure) {
    showError(failure.message);
    if (images.length) {
      emptyState.hidden = true;
      result.hidden = false;
      controls.hidden = false;
      strip.hidden = false;
      count.textContent = `${images.length} image${images.length === 1 ? '' : 's'} ready · download within ${count.dataset.keep}`;
    } else {
      emptyState.hidden = false;
      result.hidden = true;
      controls.hidden = true;
      strip.hidden = true;
      count.textContent = defaultPreviewCount;
    }
  } finally {
    setGenerating(false);
  }
});

if (window.wireHermitDownloadLink) {
  window.wireHermitDownloadLink(currentDownload);
  window.wireHermitDownloadLink(allDownload);
}
