let screenImage = null;
const screenStatus = document.querySelector('#screen-status');
const screenPreview = document.querySelector('#screen-preview');
const analyzeButton = document.querySelector('#analyze-screen');
let screenBusy = false;

async function previewScreen(blob) {
  if (blob.size > 20 * 1024 * 1024) throw new Error('Choose an image smaller than 20 MB.');
  const bitmap = await createImageBitmap(blob);
  try {
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const data = canvas.toDataURL('image/png');
    if (data.length > 5_592_430) throw new Error('Image is too large. Choose a smaller area.');
    screenImage = data;
    screenPreview.src = data;
    screenPreview.hidden = false;
    analyzeButton.disabled = false;
    document.querySelector('#screen-answer').hidden = true;
    screenStatus.textContent = 'Preview ready. Only click Analyze locally when the image contains what you want to share with the local model.';
  } finally { bitmap.close(); }
}
document.querySelector('#screen-file').addEventListener('change', async event => {
  if (screenBusy) return;
  const file = event.target.files[0];
  if (!file) return;
  try { await previewScreen(file); }
  catch (error) { screenStatus.textContent = error.message; }
});
document.querySelector('#capture-screen').addEventListener('click', async () => {
  if (screenBusy) return;
  if (!navigator.mediaDevices?.getDisplayMedia) {
    screenStatus.textContent = 'Screen capture is unavailable in this browser. Choose a screenshot file instead.';
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    const video = document.createElement('video');
    video.srcObject = stream;
    await video.play();
    const canvas = document.createElement('canvas');
    const scale = Math.min(1, 1600 / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
    if (!blob) throw new Error('Could not capture the screen.');
    await previewScreen(blob);
  } catch (error) {
    screenStatus.textContent = error.name === 'NotAllowedError' ? 'Capture cancelled. You can choose a screenshot instead.' : error.message;
  } finally { stream?.getTracks().forEach(track => track.stop()); }
});
document.querySelector('#clear-screen').addEventListener('click', () => {
  if (screenBusy) return;
  screenImage = null;
  screenPreview.removeAttribute('src');
  screenPreview.hidden = true;
  document.querySelector('#screen-file').value = '';
  document.querySelector('#screen-answer').hidden = true;
  analyzeButton.disabled = true;
  screenStatus.textContent = 'Image cleared.';
});
document.querySelector('#screen-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!screenImage || screenBusy) return;
  screenBusy = true;
  document.querySelector('#screen-answer').hidden = true;
  analyzeButton.disabled = true;
  for (const id of ['capture-screen', 'screen-file', 'clear-screen', 'screen-question']) document.getElementById(id).disabled = true;
  screenStatus.textContent = 'Analyzing with local Qwen. This can take a few minutes…';
  try {
    const response = await fetch('/api/screen/analyze', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({image: screenImage, question: document.querySelector('#screen-question').value.trim()}) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analysis failed.');
    const answer = document.querySelector('#screen-answer');
    answer.textContent = data.answer;
    answer.hidden = false;
    screenStatus.textContent = `Analyzed locally with ${data.model}.`;
  } catch (error) { screenStatus.textContent = error.message; }
  finally {
    screenBusy = false;
    analyzeButton.disabled = !screenImage;
    for (const id of ['capture-screen', 'screen-file', 'clear-screen', 'screen-question']) document.getElementById(id).disabled = false;
  }
});

let loadingWorkflows = false;
async function loadWorkflows() {
  if (loadingWorkflows) return;
  loadingWorkflows = true;
  const feedback = document.querySelector('#workflow-status');
  try {
    const response = await fetch('/api/workflows', {cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not load workflows.');
    // Reconnect to existing IDs; never replay work after refresh or restart.
    const active = data.runs.filter(run => !['completed','failed','cancelled','expired'].includes(run.status));
    await Promise.all(active.slice(0, 10).map(async run => {
      try {
        const result = await fetch(`/api/runs/${encodeURIComponent(run.run_id)}`, {cache:'no-store'});
        if (!result.ok) { run.unavailable = true; return; }
        const current = await result.json();
        run.status = current.status || run.status;
        run.output = current.output || current.final_response || current.error || run.output;
      } catch (_) { run.unavailable = true; }
    }));
    document.querySelector('#workflow-list').innerHTML = data.workflows.length ? data.workflows.map(item => {
      const running = data.runs.some(run => run.workflow_id === item.id && !['completed','failed','cancelled','expired'].includes(run.status));
      return `<article class="memory-entry"><span>${escapeHtml(item.title)}</span><div>${escapeHtml(item.objective)}</div><ol>${item.steps.map(step => `<li>${escapeHtml(step)}</li>`).join('')}</ol><button type="button" class="run-stop" data-workflow-start="${item.id}" ${running ? 'disabled' : ''}>${running ? 'Run in progress' : 'Start workflow'}</button></article>`;
    }).join('') : '<div class="empty-state">Save a workflow to begin.</div>';
    document.querySelector('#workflow-runs').innerHTML = data.runs.length ? data.runs.map(run => `<article class="memory-entry"><span>${escapeHtml(run.title)}</span><div>${escapeHtml(run.status)}${run.unavailable ? ' · Status unavailable; last known state shown' : ''} · ${escapeHtml(new Date(run.updated_at * 1000).toLocaleString())}</div><small>${escapeHtml(run.run_id)}</small>${!['completed','failed','cancelled','expired'].includes(run.status) ? `<div><button type="button" class="run-stop" data-workflow-stop="${escapeHtml(run.run_id)}">Stop run</button></div>` : ''}${run.output ? `<details><summary>View result</summary><div class="workflow-output">${escapeHtml(typeof run.output === 'string' ? run.output : JSON.stringify(run.output))}</div></details>` : ''}</article>`).join('') : '<div class="empty-state">New chat and workflow runs will appear here.</div>';
  } catch (error) { feedback.textContent = error.message; }
  finally { loadingWorkflows = false; }
}
document.querySelector('#workflow-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button');
  if (button.disabled) return;
  button.disabled = true;
  try {
    const response = await fetch('/api/workflows', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      title:document.querySelector('#workflow-title').value.trim(), objective:document.querySelector('#workflow-objective').value.trim(),
      steps:document.querySelector('#workflow-steps').value.split('\n').map(line => line.trim()).filter(Boolean)
    })});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not save workflow.');
    document.querySelector('#workflow-form').reset();
    document.querySelector('#workflow-status').textContent = 'Workflow saved. Start it when ready.';
    await loadWorkflows();
  } catch (error) { document.querySelector('#workflow-status').textContent = error.message; }
  finally { button.disabled = false; }
});
document.querySelector('#refresh-workflows').addEventListener('click', loadWorkflows);
async function workflowAction(event) {
  const start = event.target.closest('[data-workflow-start]');
  const stop = event.target.closest('[data-workflow-stop]');
  if (!start && !stop) return;
  const button = start || stop;
  if (button.disabled) return;
  button.disabled = true;
  try {
    const response = await fetch(start ? '/api/runs' : `/api/runs/${encodeURIComponent(stop.dataset.workflowStop)}/stop`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(start ? {workflow_id:Number(start.dataset.workflowStart)} : {})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Run action failed.');
    document.querySelector('#workflow-status').textContent = start ? 'Workflow submitted to Hermes.' : 'Stop requested; waiting for Hermes to confirm.';
    await loadWorkflows();
  } catch (error) { document.querySelector('#workflow-status').textContent = error.message; button.disabled = false; }
}
document.querySelector('#workflow-list').addEventListener('click', workflowAction);
document.querySelector('#workflow-runs').addEventListener('click', workflowAction);
setInterval(() => {
  if (document.querySelector('#view-workflows').classList.contains('active-view')) loadWorkflows();
}, 5000);
