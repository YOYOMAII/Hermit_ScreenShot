const smartForm = document.querySelector('#smart-form');
const docxInput = document.querySelector('#docx');
const docxDropzone = document.querySelector('#docx-dropzone');
const docStatus = document.querySelector('#doc-status');
const docName = document.querySelector('#doc-name');
const docSummary = document.querySelector('#doc-summary');
const codeInput = document.querySelector('#code-files');
const codeDropzone = document.querySelector('#code-dropzone');
const codeList = document.querySelector('#code-list');
const insertMode = document.querySelector('#insert-mode');
const afterPageField = document.querySelector('#after-page-field');
const pageHint = document.querySelector('#page-hint');
const startFigure = document.querySelector('#start-figure');
const buildButton = document.querySelector('#build-button');
const formError = document.querySelector('#form-error');
const emptyState = document.querySelector('#empty-state');
const smartResult = document.querySelector('#smart-result');
const previewCount = document.querySelector('#preview-count');
const resultControls = document.querySelector('#result-controls');
const smartSummary = document.querySelector('#smart-summary');
const keepAdding = document.querySelector('#keep-adding');
const downloadDocx = document.querySelector('#download-docx');

let docFile = null;
let docId = null;
let lastBuild = null;
let codeFiles = [];

const MAX_FILES = 20;
const MAX_UPLOAD_BYTES = 40 * 1024 * 1024;

function showError(message) {
  formError.textContent = message;
  formError.hidden = !message;
}

async function postForm(url, data, fallback) {
  let response;
  try {
    response = await fetch(url, { method: 'POST', body: data });
  } catch {
    throw new Error('Could not reach HermitSmart. Check that "python app.py" is still running, then try again.');
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || fallback);
  return payload;
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`;
}

function describeDocument(name, info, note) {
  docName.textContent = name;
  const figures = info.figures
    ? `${plural(info.figures, 'HermitSmart figure')} found. New figures start at Fig ${info.next_figure}.`
    : 'No HermitSmart figures yet.';
  docSummary.textContent = `${note ? `${note} · ` : ''}About ${plural(info.pages_estimate, 'page')}. ${figures}`;
  docStatus.hidden = false;
  startFigure.placeholder = `Auto (${info.next_figure})`;
}

function updateInsertFields() {
  const afterPage = insertMode.value === 'after_page';
  afterPageField.hidden = !afterPage;
  pageHint.hidden = !afterPage;
}
insertMode.addEventListener('change', updateInsertFields);

async function setDocument(file) {
  if (!file) return;
  if (!/\.docx$/i.test(file.name)) {
    showError('Only Word .docx documents are supported.');
    return;
  }
  showError('');
  docFile = file;
  docId = null;
  describeDocument(file.name, { pages_estimate: 1, figures: 0, next_figure: 1 }, 'Reading…');
  const data = new FormData();
  data.append('docx', file, file.name);
  try {
    const payload = await postForm('/api/smart/inspect', data, 'Could not read this Word document.');
    if (docFile !== file) return;
    describeDocument(file.name, payload);
    insertMode.value = payload.figures ? 'continue' : 'end';
    updateInsertFields();
  } catch (failure) {
    if (docFile !== file) return;
    docFile = null;
    docStatus.hidden = true;
    showError(failure.message);
  }
}

function setCodeFiles(files) {
  const all = [...files];
  codeFiles = all.filter(file => /\.(html|css)$/i.test(file.name));
  codeList.replaceChildren();
  for (const file of codeFiles) {
    const item = document.createElement('li');
    const badge = document.createElement('span');
    const name = document.createElement('span');
    badge.className = 'file-badge';
    badge.textContent = file.name.toLowerCase().endsWith('.css') ? 'CSS' : 'HTML';
    name.textContent = file.name;
    item.append(badge, name);
    codeList.append(item);
  }
  const skipped = all.length - codeFiles.length;
  showError(skipped ? `Skipped ${skipped} file${skipped === 1 ? '' : 's'} that ${skipped === 1 ? 'is' : 'are'} not .html or .css.` : '');
}

function wireDropzone(zone, onFiles) {
  for (const eventName of ['dragenter', 'dragover']) {
    zone.addEventListener(eventName, event => {
      event.preventDefault();
      zone.classList.add('dragging');
    });
  }
  for (const eventName of ['dragleave', 'drop']) {
    zone.addEventListener(eventName, event => {
      event.preventDefault();
      zone.classList.remove('dragging');
    });
  }
  zone.addEventListener('drop', event => onFiles(event.dataTransfer.files));
}

docxInput.addEventListener('change', () => setDocument(docxInput.files[0]));
wireDropzone(docxDropzone, files => setDocument(files[0]));
codeInput.addEventListener('change', () => setCodeFiles(codeInput.files));
wireDropzone(codeDropzone, setCodeFiles);

function figureSlot(figure) {
  const slot = document.createElement('figure');
  slot.className = 'doc-slot';
  const image = document.createElement('img');
  image.src = figure.image_url;
  image.alt = `Screenshot for ${figure.caption}`;
  const caption = document.createElement('figcaption');
  caption.className = 'doc-caption';
  caption.textContent = figure.caption;
  slot.append(image, caption);
  return slot;
}

function renderPages(figures) {
  smartResult.replaceChildren();
  let page = null;
  for (const figure of figures) {
    if (!page || figure.page_slot === 1) {
      page = document.createElement('div');
      page.className = 'doc-page';
      smartResult.append(page);
      if (figure.page_slot === 2) {
        const earlier = document.createElement('div');
        earlier.className = 'doc-slot doc-slot-earlier';
        earlier.textContent = 'Earlier figure';
        page.append(earlier);
      }
    }
    page.append(figureSlot(figure));
  }
  return smartResult.children.length;
}

smartForm.addEventListener('submit', async event => {
  event.preventDefault();
  if (!docFile && !docId) {
    showError('Choose a Word (.docx) document.');
    return;
  }
  if (!codeFiles.length) {
    showError('Choose at least one HTML or CSS file.');
    return;
  }
  if (codeFiles.length > MAX_FILES) {
    showError(`Choose up to ${MAX_FILES} code files at a time.`);
    return;
  }
  const uploadBytes = codeFiles.reduce((total, file) => total + file.size, docFile ? docFile.size : 0);
  if (uploadBytes > MAX_UPLOAD_BYTES) {
    showError('The document and code files are larger than 40 MB together. Upload fewer code files at a time.');
    return;
  }
  showError('');
  buildButton.disabled = true;
  buildButton.querySelector('span').textContent = 'Building…';
  const data = new FormData(smartForm);
  data.delete('docx');
  data.delete('files');
  if (docId) data.append('doc_id', docId);
  else data.append('docx', docFile, docFile.name);
  for (const file of codeFiles) data.append('files', file, file.name);
  try {
    const payload = await postForm('/api/smart/build', data, 'Could not build this document.');
    lastBuild = payload;
    const pages = renderPages(payload.figures);
    const first = payload.figures[0].n;
    const last = payload.figures[payload.figures.length - 1].n;
    emptyState.hidden = true;
    smartResult.hidden = false;
    resultControls.hidden = false;
    previewCount.textContent = `${plural(payload.figures.length, 'figure')} on ${plural(pages, 'page')} · download within ${previewCount.dataset.keep}`;
    smartSummary.textContent = first === last ? `Added Fig ${first}` : `Added Fig ${first}–${last}`;
    downloadDocx.href = payload.download_url;
    downloadDocx.download = payload.name;
    keepAdding.disabled = false;
  } catch (failure) {
    showError(failure.message);
  } finally {
    buildButton.disabled = false;
    buildButton.querySelector('span').textContent = 'Build Word document';
  }
});

keepAdding.addEventListener('click', () => {
  if (!lastBuild) return;
  docId = lastBuild.doc_id;
  docFile = null;
  docxInput.value = '';
  describeDocument(lastBuild.name, {
    pages_estimate: lastBuild.pages_estimate,
    figures: lastBuild.total_figures,
    next_figure: lastBuild.next_figure,
  }, 'Updated copy');
  codeInput.value = '';
  setCodeFiles([]);
  startFigure.value = '';
  insertMode.value = 'continue';
  updateInsertFields();
  keepAdding.disabled = true;
  codeDropzone.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

updateInsertFields();
