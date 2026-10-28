const feed = document.querySelector('#chat-feed');
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');
const sendButton = form.querySelector('.send-button');
const voiceButton = document.querySelector('#voice-input');
const attachButton = document.querySelector('#attach-files');
const attachedFilesNode = document.querySelector('#attached-files');
let selectedLocalFiles = [];
const visualChannel = 'BroadcastChannel' in window ? new BroadcastChannel('jarvis-visualizer') : null;

function renderAttachedFiles() {
  attachedFilesNode.replaceChildren();
  attachedFilesNode.hidden = selectedLocalFiles.length === 0;
  selectedLocalFiles.forEach((file, index) => {
    const chip = document.createElement('span');
    chip.className = 'attached-file';
    const name = document.createElement('span');
    name.textContent = `📎 ${file.name}`;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'remove-attachment';
    remove.setAttribute('aria-label', `Remove ${file.name}`);
    remove.textContent = '×';
    remove.addEventListener('click', () => {
      selectedLocalFiles = selectedLocalFiles.filter((_, itemIndex) => itemIndex !== index);
      renderAttachedFiles();
    });
    chip.append(name, remove);
    attachedFilesNode.append(chip);
  });
}

attachButton?.addEventListener('click', async () => {
  if (attachButton.disabled) return;
  attachButton.disabled = true;
  attachButton.textContent = 'Opening…';
  try {
    const response = await fetch('/api/files/pick', { method: 'POST' });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not open the file picker.');
    const known = new Set(selectedLocalFiles.map(file => file.path));
    for (const file of result.files || []) {
      if (!known.has(file.path) && selectedLocalFiles.length < 10) selectedLocalFiles.push(file);
      known.add(file.path);
    }
    renderAttachedFiles();
  } catch (error) {
    addMessage('assistant', error.message || 'Could not open the local file picker.');
  } finally {
    attachButton.disabled = false;
    attachButton.textContent = '＋ Files';
  }
});

function setFaceState(state, detail = '') {
  const event = { type: 'state', state, detail, at: Date.now() };
  visualChannel?.postMessage(event);
  try { localStorage.setItem('jarvis.face.state', JSON.stringify(event)); } catch (_) {}
}

visualChannel?.addEventListener('message', (event) => {
  if (event.data?.type !== 'voice-input' || typeof event.data.text !== 'string') return;
  input.value = event.data.text.trim();
  input.dispatchEvent(new Event('input', { bubbles: true }));
  form.requestSubmit();
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
}

function addMessage(role, content, { temporary = false } = {}) {
  const user = role === 'user';
  const node = document.createElement('div');
  node.className = `message ${user ? 'user-message' : 'assistant-message'}${temporary ? ' thinking' : ''}`;
  node.innerHTML = `<div class="message-avatar">${user ? 'KS' : 'J'}</div><div class="message-body"><div class="message-meta">${user ? 'YOU' : 'JARVIS'} <span>•</span> ${temporary ? 'WORKING' : 'NOW'}</div><div class="message-bubble">${escapeHtml(content)}</div></div>`;
  feed.append(node);
  feed.scrollTop = feed.scrollHeight;
  return node;
}

const taskWorkspace = document.querySelector('#task-workspace');
let activeTaskRunId = '';

function taskPhase(label, detail, state) {
  const row = document.createElement('div');
  row.className = `task-phase ${state}`;
  const marker = document.createElement('span'); marker.className = 'task-phase-marker';
  const copy = document.createElement('div'); copy.className = 'task-phase-copy';
  const title = document.createElement('strong'); title.textContent = label;
  const note = document.createElement('small'); note.textContent = detail;
  copy.append(title, note); row.append(marker, copy);
  return row;
}

function renderTaskWorkspace(message, runId, status = {}) {
  const state = String(status.status || 'queued').toLowerCase();
  const terminal = ['completed', 'failed', 'cancelled', 'expired'].includes(state);
  const stateLabel = state === 'waiting_for_approval' ? 'NEEDS APPROVAL' : state.replaceAll('_', ' ').toUpperCase();
  document.querySelector('#task-workspace-title').textContent = message.slice(0, 96) || 'Working on your task';
  document.querySelector('#task-focus-title').textContent = message.slice(0, 150) || 'Working on your task';
  document.querySelector('#task-run-state').textContent = stateLabel;
  document.querySelector('#task-run-state').className = `task-run-pill ${terminal ? state : 'active'}`;
  document.querySelector('#task-run-id').textContent = `Run ${runId}`;
  const lastEvent = typeof status.last_event === 'string' ? status.last_event.trim().slice(0, 180) : '';
  document.querySelector('#task-focus-status').textContent = state === 'waiting_for_approval'
    ? 'Waiting for your approval in the chat panel.'
    : terminal ? `Task ${state}${lastEvent ? ` · ${lastEvent}` : ''}`
      : `${state === 'queued' ? 'Queued for execution' : 'Hermes is working'}${lastEvent ? ` · ${lastEvent}` : ''}`;
  const phases = document.querySelector('#task-phase-list');
  phases.replaceChildren(
    taskPhase('Request received', 'Task accepted by Jarvis', 'complete'),
    taskPhase('Hermes execution', state === 'queued' ? 'Waiting to start' : lastEvent || `Run state: ${state}`, terminal ? 'complete' : 'active'),
    taskPhase('Result', terminal ? `Run ${state}` : 'Waiting for run completion', terminal ? 'complete' : 'pending'),
  );
  const activity = document.querySelector('#task-activity');
  const events = Array.isArray(status.activity) ? status.activity : [];
  const verifiedTools = Array.isArray(status.tool_evidence) ? status.tool_evidence : [];
  const entries = events.length ? events : verifiedTools.map(name => ({kind:'tool', name, state:'completed'}));
  document.querySelector('#task-observed-count').textContent = `${entries.length} EVENT${entries.length === 1 ? '' : 'S'}`;
  activity.replaceChildren();
  if (!entries.length) {
    const empty = document.createElement('div'); empty.className = 'empty-state';
    empty.textContent = 'No agent or tool events recorded yet. Jarvis will show only work Hermes reports.';
    activity.append(empty);
  } else {
    for (const entry of entries) {
      const card = document.createElement('article'); card.className = `task-activity-card ${entry.kind === 'agent' ? 'agent' : 'tool'}`;
      const glyph = document.createElement('span'); glyph.className = 'task-activity-glyph'; glyph.textContent = entry.kind === 'agent' ? '⌘' : '⌁';
      const copy = document.createElement('div'); copy.className = 'task-activity-copy';
      const name = document.createElement('strong'); name.textContent = `${entry.kind === 'agent' ? 'Agent' : 'Tool'} · ${String(entry.name || 'Unknown').slice(0, 80)}`;
      const detail = document.createElement('small'); detail.textContent = [entry.task, entry.state].filter(Boolean).join(' · ') || 'Event recorded';
      copy.append(name, detail); card.append(glyph, copy); activity.append(card);
    }
  }
  const stopButton = document.querySelector('#task-stop');
  stopButton.disabled = terminal;
  stopButton.textContent = terminal ? 'Task ended' : 'Stop task';
  taskWorkspace.dataset.runState = state;
}

function openTaskWorkspace() {
  if (!taskWorkspace.open) taskWorkspace.showModal();
}

window.updateJarvisTask = (message, runId, status, options = {}) => {
  activeTaskRunId = runId;
  window.activeJarvisTaskRunId = runId;
  if (options.open) document.querySelector('#task-result-panel').hidden = true;
  renderTaskWorkspace(message, runId, status);
  if (options.result !== undefined) setTaskResult(options.result);
  if (options.open) openTaskWorkspace();
};

function setTaskResult(result) {
  const panel = document.querySelector('#task-result-panel');
  panel.hidden = false;
  document.querySelector('#task-result').textContent = String(result || 'Run ended without a result.');
}

document.querySelector('#task-workspace-close').addEventListener('click', () => taskWorkspace.close());
document.querySelector('#task-workspace-done').addEventListener('click', () => taskWorkspace.close());
document.querySelector('#task-stop').addEventListener('click', async event => {
  if (!activeTaskRunId) return;
  event.currentTarget.disabled = true;
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(activeTaskRunId)}/stop`, {method:'POST'});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not stop task.');
    document.querySelector('#task-focus-status').textContent = 'Stop requested. Waiting for Hermes to confirm.';
  } catch (error) {
    document.querySelector('#task-focus-status').textContent = error.message;
    event.currentTarget.disabled = false;
  }
});

async function refreshStatus() {
  try {
    const response = await fetch('/api/status', { cache: 'no-store' });
    if (!response.ok) throw new Error('Server unavailable');
    const status = await response.json();
    document.querySelector('#agent-state').textContent = status.hermes_online ? 'Hermes online' : 'Offline';
    const harnessPill = document.querySelector('#harness-pill');
    harnessPill.innerHTML = `<i></i> ${status.hermes_online ? 'CONNECTED' : 'OFFLINE'}`;
    harnessPill.className = `status-pill ${status.hermes_online ? 'good' : 'neutral'}`;
    const delegationConfigured = status.delegation_configured ?? Number(status.delegation_max_parallel) > 0;
    const executedTools = Array.isArray(status.tool_execution_verified_tools)
      ? status.tool_execution_verified_tools.filter(Boolean).join(', ') : '';
    const agentsStatus = document.querySelector('#agents-status');
    if (agentsStatus) {
      agentsStatus.textContent = status.council_available
        ? 'Council review is available for substantial tasks. Delegation results are shown only after a child completion event.'
        : status.delegation_runtime_verified
          ? 'Hermes recorded a completed delegated task in this Jarvis session. Role cards are blueprints; agents are created for individual tasks.'
          : 'Hermes delegation is enabled, but Jarvis has not verified a completed child-agent run. Council review is not implemented yet; these cards are role blueprints only.';
    }
    document.querySelector('#harness-note').textContent = status.hermes_online
      ? `${delegationConfigured ? 'Delegation configured' : 'Delegation unavailable'} · ${status.tool_execution_verified
        ? `tool calls verified${executedTools ? `: ${executedTools}` : ''}`
        : 'tool calls not yet verified'}`
      : 'Start Hermes through scripts/start_jarvis.ps1';
    const memoryNote = document.querySelector('#memory-note');
    if (memoryNote) {
      const profileState = typeof status.user_profile_document_available === 'boolean'
        ? status.user_profile_document_available ? 'Local profile available by request' : 'No profile document found'
        : 'Profile inclusion ready after server restart';
      memoryNote.textContent = `${profileState} · Honcho ${status.honcho_connected ? 'connected' : 'not connected'}`;
    }
    const honchoState = document.querySelector('#honcho-state');
    if (honchoState) honchoState.textContent = status.honcho_connected
      ? 'CONNECTED'
      : status.honcho_plugin_installed
        ? (status.honcho_api_key_configured ? 'READY · NOT ENABLED' : 'PLUGIN INSTALLED · KEY NEEDED')
        : 'NOT INSTALLED';
    const browserState = document.querySelector('#browser-state');
    if (browserState) browserState.textContent = status.browser_tools_available
      ? 'TOOLS ENABLED · LOGIN SEPARATE · EXECUTION UNVERIFIED' : 'NOT AVAILABLE';
    const jobsState = document.querySelector('#job-search-state');
    if (jobsState) jobsState.textContent = status.job_search_available && status.xlsx_export_available && status.resume_pdf_extraction_available
      ? 'SEARCH TOOLS CONFIGURED · LOCAL PDF · EXCEL READY'
      : status.job_search_available
        ? status.resume_pdf_extraction_available ? 'SEARCH TOOLS CONFIGURED · EXPORT SETUP NEEDED' : 'SEARCH TOOLS CONFIGURED · PDF READER NEEDED'
        : 'WEB SEARCH NOT AVAILABLE';
    const pcState = document.querySelector('#pc-state');
    if (pcState) pcState.textContent = status.desktop_control_available
      ? 'TOOLS ENABLED · LIVE EXECUTION UNVERIFIED'
      : status.workspace_file_tools_available ? 'FILES & TERMINAL ENABLED · EXECUTION UNVERIFIED' : 'NOT AVAILABLE';
    for (const id of ['gmail-state', 'calendar-state', 'drive-state']) {
      const element = document.querySelector(`#${id}`);
      if (element && status.google_workspace_skill_available) element.textContent = status.google_oauth_connected
        ? 'CONNECTED' : status.google_oauth_client_configured ? 'OAUTH SETUP READY · SIGN IN NEEDED' : 'GOOGLE OAUTH CLIENT NEEDED';
    }
    const youtubeState = document.querySelector('#youtube-state');
    if (youtubeState) youtubeState.textContent = status.youtube_skill_available
      ? 'VIDEO SKILL READY · CHANNEL LOGIN NEEDED' : 'NOT AVAILABLE';
    const claudeCodeState = document.querySelector('#claude-code-state');
    if (claudeCodeState) claudeCodeState.textContent = status.claude_code_available
      ? status.claude_code_skill_available ? 'CLI & SKILL INSTALLED · LOGIN UNVERIFIED' : 'CLI PRESENT · SKILL / LOGIN NEEDED'
      : 'CLI NOT INSTALLED';
    document.querySelector('#service-state').textContent = status.hermes_online ? 'ONLINE' : 'LIMITED';
    document.querySelector('#service-state').style.color = status.hermes_online ? 'var(--green)' : 'var(--amber)';
    document.querySelector('#model-route').textContent = status.model_route;
    const configured = status.openrouter_key_configured;
    const localReady = status.ollama_reachable && status.ollama_model_available;
    const pill = document.querySelector('#brain-pill');
    const value = document.querySelector('#brain-value');
    const note = document.querySelector('#brain-note');
    if (status.hermes_online && configured) {
      pill.innerHTML = '<i></i> CONNECTED';
      pill.className = 'status-pill good';
      value.textContent = 'Hermes · OpenRouter';
      note.textContent = localReady ? 'Ollama fallback model is ready' : 'OpenRouter active; local fallback needs setup';
    } else if (status.hermes_online && localReady) {
      pill.innerHTML = '<i></i> LOCAL READY';
      pill.className = 'status-pill good';
      value.textContent = 'Hermes · Ollama';
      note.textContent = 'Using local inference route';
    } else {
      pill.innerHTML = `<i></i> ${status.hermes_online ? 'MODEL SETUP' : 'OFFLINE'}`;
      pill.className = 'status-pill';
      value.textContent = 'Hermes agent harness';
      note.textContent = status.hermes_online ? 'Add a model key or install the configured local model' : 'Start Jarvis to connect the agent runtime';
    }
  } catch (_) {
    document.querySelector('#service-state').textContent = 'OFFLINE';
    document.querySelector('#service-state').style.color = 'var(--amber)';
    document.querySelector('#brain-note').textContent = 'Start the Jarvis local server to connect';
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if ((!message && !selectedLocalFiles.length) || sendButton.disabled) return;
  const attachments = selectedLocalFiles;
  const autoOpenTaskRoom = attachments.length > 0 || message.length > 80 || /\b(build|make|create|analy[sz]e|inspect|research|find|search|run|edit|fix|update|automate|plan|compare|review|summari[sz]e|draft|apply|organize|convert|generate|calculate|process|clean|visuali[sz]e|dashboard|job|resume|spreadsheet|excel)\b/i.test(message);
  const includeMemory = document.querySelector('#include-memory').checked;
  document.querySelector('#include-memory').checked = false;
  setFaceState('thinking');
  addMessage('user', `${message}${attachments.length ? `${message ? '\n' : ''}${attachments.map(file => `📎 ${file.name}`).join('\n')}` : ''}`);
  selectedLocalFiles = [];
  renderAttachedFiles();
  input.value = '';
  input.style.height = 'auto';
  sendButton.disabled = true;
  activeTaskRunId = '';
  window.activeJarvisTaskRunId = '';
  document.querySelector("#new-conversation").disabled = true;
  const pending = addMessage('assistant', 'Starting Hermes run…', { temporary: true });
  try {
    const response = await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: message || 'Please inspect the selected local file(s) and tell me what you find.', include_memory: includeMemory, attachments })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Request failed');
    if (result.memory_used?.length) {
      addMessage('assistant', `Using ${result.memory_used.length} saved fact(s): ${[...new Set(result.memory_used.map(item => item.category))].join(', ')}.`);
    }
    if (result.profile_reference_used) {
      addMessage('assistant', 'Using your local profile document for this request; it was shared with the configured AI model because memory consent was enabled.');
    }
    const runId = result.run_id || result.id;
    if (!runId) throw new Error('Hermes accepted the request but returned no run id.');
    activeTaskRunId = runId;
    window.activeJarvisTaskRunId = runId;
    document.querySelector('#task-result-panel').hidden = true;
    renderTaskWorkspace(message || attachments.map(file => file.name).join(', '), runId, result);
    if (autoOpenTaskRoom) openTaskWorkspace();
    const bubble = pending.querySelector('.message-bubble');
    bubble.replaceChildren(document.createTextNode(`Run ${runId.slice(0, 10)} · `));
    const runState = document.createElement('span');
    runState.className = 'run-live-state';
    runState.textContent = result.status || 'queued';
    bubble.append(runState, document.createElement('br'));
    const stop = document.createElement('button');
    stop.className = 'run-stop'; stop.type = 'button'; stop.textContent = 'Stop run';
    const openTask = document.createElement('button');
    openTask.className = 'run-stop'; openTask.type = 'button'; openTask.textContent = 'Open task room';
    openTask.addEventListener('click', openTaskWorkspace);
    bubble.append(stop, openTask);
    stop.addEventListener('click', async () => {
      stop.disabled = true;
      await fetch(`/api/runs/${encodeURIComponent(runId)}/stop`, { method: 'POST' });
    });
    const workPhrases = [
      'Thinking it through…', 'Working on it…', 'Putting the pieces together…',
      'Making progress…', 'On the case…', 'Checking the details…',
      'Working through the task…', 'Taking a closer look…', 'Still at it…'
    ];
    let currentPhrase = '';
    let approvalCardId = '';
    let polls = 0;
    while (polls++ < 600) {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      const statusResponse = await fetch(`/api/runs/${encodeURIComponent(runId)}`, { cache: 'no-store' });
      const status = await statusResponse.json();
      if (!statusResponse.ok) throw new Error(status.error || 'Could not read run status.');
      const state = status.status || 'running';
      renderTaskWorkspace(message || attachments.map(file => file.name).join(', '), runId, status);
      const approval = status.approval;
      if (state === 'waiting_for_approval' && approval && approval.request_id && approvalCardId !== approval.request_id) {
        approvalCardId = approval.request_id;
        const card = document.createElement('section');
        card.className = 'approval-card';
        const heading = document.createElement('strong');
        heading.textContent = 'Jarvis needs approval';
        const detail = document.createElement('p');
        detail.textContent = [approval.tool_name || approval.tool, approval.command, approval.description || approval.reason].filter(Boolean).join(' · ') || 'Hermes requested permission for an action.';
        const approve = document.createElement('button');
        approve.type = 'button'; approve.className = 'run-stop'; approve.textContent = 'Approve once';
        const deny = document.createElement('button');
        deny.type = 'button'; deny.className = 'run-stop'; deny.textContent = 'Deny';
        const feedback = document.createElement('small');
        async function resolveApproval(choice, button) {
          approve.disabled = deny.disabled = true;
          try {
            const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/approval`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({choice, request_id:approval.request_id})});
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Approval response failed.');
            feedback.textContent = choice === 'once' ? 'Approved for this action only.' : 'Denied.';
          } catch (error) { feedback.textContent = error.message; approve.disabled = deny.disabled = false; }
        }
        approve.addEventListener('click', () => resolveApproval('once', approve));
        deny.addEventListener('click', () => resolveApproval('deny', deny));
        card.append(heading, detail, approve, deny, feedback);
        bubble.append(card);
      }
      if (['completed', 'failed', 'cancelled', 'expired'].includes(state)) {
        pending.remove();
        const answer = status.output || status.final_response || status.error || `Run ${state}.`;
        setTaskResult(answer);
        const answerNode = addMessage('assistant', answer);
        if (status.job_export?.id) {
          const bubble = answerNode.querySelector('.message-bubble');
          const note = document.createElement('div');
          note.className = 'job-export-note';
          note.textContent = `${status.job_export.count} listing(s) exported · retrieved ${status.job_export.retrieved_at || 'just now'}`;
          const link = document.createElement('a');
          link.className = 'job-export-link';
          link.href = `/api/exports/${encodeURIComponent(status.job_export.id)}`;
          link.textContent = 'Download Excel workbook';
          link.setAttribute('download', 'jarvis-job-matches.xlsx');
          bubble.append(document.createElement('br'), note, link);
        }
        if (status.action_verification) {
          const receipt = document.createElement('small');
          receipt.className = `action-receipt ${status.action_verification}`;
          const tools = Array.isArray(status.tool_evidence) ? status.tool_evidence : [];
          receipt.textContent = status.action_verification === 'verified'
            ? `Tool receipt: Hermes recorded successful call${tools.length === 1 ? '' : 's'}${tools.length ? ` (${tools.join(', ')})` : ''}. This confirms tool events, not the final state of an external service.`
            : `Tool receipt: action not verified. ${status.tool_evidence_reason || 'No successful tool completion evidence was returned.'}`;
          answerNode.querySelector('.message-bubble').append(document.createElement('br'), receipt);
        }
        visualChannel?.postMessage({ type: 'response', text: String(answer), runState: state, at: Date.now() });
        try {
          localStorage.setItem('jarvis.face.lastResponse', JSON.stringify({ text: String(answer), at: Date.now() }));
          localStorage.setItem('jarvis.face.state', JSON.stringify({ state: 'idle', detail: 'Reply ready. Ask me what you need next.', at: Date.now() }));
        } catch (_) {}
        break;
      }
      if (polls % 2 === 0 || !currentPhrase) {
        const choices = workPhrases.filter((phrase) => phrase !== currentPhrase);
        currentPhrase = choices[Math.floor(Math.random() * choices.length)];
      }
      runState.textContent = `${currentPhrase} · ${state}${status.last_event ? ` · ${status.last_event}` : ''}`;
      if (polls === 600) runState.textContent = 'Still running. Check Hermes logs for the current state.';
    }
    if (document.querySelector('#view-memory').classList.contains('active-view')) loadMemory();
  } catch (error) {
    selectedLocalFiles = attachments;
    renderAttachedFiles();
    pending.remove();
    addMessage('assistant', error.message || 'Jarvis could not reach the local service.');
    if (activeTaskRunId) {
      renderTaskWorkspace(message || 'Task could not start', activeTaskRunId, {status:'failed', last_event:error.message || 'Request failed'});
      setTaskResult(error.message || 'Jarvis could not reach the local service.');
    }
    visualChannel?.postMessage({ type: 'response', text: error.message || 'Jarvis could not reach the local service.', runState: 'failed', at: Date.now() });
    try { localStorage.setItem('jarvis.face.state', JSON.stringify({ state: 'idle', detail: 'The request stopped. You can try again.', at: Date.now() })); } catch (_) {}
  } finally {
    sendButton.disabled = false;
    document.querySelector("#new-conversation").disabled = false;
    input.focus();
  }
});

if (voiceButton) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    voiceButton.disabled = true;
    voiceButton.title = 'Voice input is not supported by this browser';
    voiceButton.setAttribute('aria-label', 'Voice input is not supported by this browser');
  } else {
    let recognition = null;
    voiceButton.addEventListener('click', () => {
      if (recognition) {
        recognition.stop();
        return;
      }
      recognition = new Recognition();
      recognition.lang = 'en-IN';
      recognition.interimResults = true;
      recognition.continuous = false;
      let finalText = '';
      voiceButton.classList.add('listening');
      voiceButton.setAttribute('aria-label', 'Stop listening to Jarvis');
      setFaceState('listening', 'Listening to your voice');
      recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const text = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalText += `${text} `;
          else interim += text;
        }
        input.value = `${finalText}${interim}`.trim();
        input.dispatchEvent(new Event('input', { bubbles: true }));
      };
      recognition.onerror = (event) => {
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          visualChannel?.postMessage({ type: 'notice', text: `Voice input: ${event.error}` });
        }
      };
      recognition.onend = () => {
        recognition = null;
        voiceButton.classList.remove('listening');
        voiceButton.setAttribute('aria-label', 'Speak to Jarvis');
        if (finalText.trim()) form.requestSubmit();
        else setFaceState('idle', 'Standing by');
      };
      try { recognition.start(); }
      catch (_) { recognition = null; voiceButton.classList.remove('listening'); setFaceState('idle', 'Standing by'); }
    });
  }
}

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
});
input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

let savedFacts = [];
function memoryFeedback(text) {
  document.querySelector('#memory-feedback').textContent = text;
}
function resetMemoryForm() {
  document.querySelector('#memory-form').reset();
  document.querySelector('#memory-id').value = '';
  document.querySelector('#memory-cancel').hidden = true;
}
function renderFacts() {
  const query = document.querySelector('#memory-search').value.toLowerCase();
  const matches = savedFacts.filter(item => `${item.category} ${item.content}`.toLowerCase().includes(query));
  document.querySelector('#memory-facts').innerHTML = matches.length
    ? matches.map(item => `<article class="memory-entry"><span>${escapeHtml(item.category)}</span><div>${escapeHtml(item.content)}</div><small>Source: ${escapeHtml(item.source)} · Updated ${escapeHtml(new Date(item.updated_at * 1000).toLocaleString())}</small><div><button type="button" class="run-stop" data-memory-edit="${item.id}">Edit</button> <button type="button" class="run-stop" data-memory-delete="${item.id}">Delete</button></div></article>`).join('')
    : '<div class="empty-state">No matching saved facts. Add one above.</div>';
}
async function loadMemory() {
  try {
    const [history, facts] = await Promise.all([
      fetch('/api/history', { cache: 'no-store' }), fetch('/api/memory', { cache: 'no-store' })
    ]);
    if (!history.ok || !facts.ok) throw new Error('Could not load local memory.');
    const data = await history.json();
    savedFacts = (await facts.json()).facts;
    document.querySelector('#memory-messages').innerHTML = data.messages.length
      ? data.messages.slice(-12).reverse().map(item => `<div class="memory-entry"><span>${escapeHtml(item.role.toUpperCase())}</span>${escapeHtml(item.content)}</div>`).join('')
      : '<div class="empty-state">No saved conversations yet.</div>';
    renderFacts();
  } catch (error) { memoryFeedback(error.message); }
}
async function mutateMemory(path, body) {
  const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Could not save memory.');
  return result;
}
document.querySelector('#memory-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('[type="submit"]');
  if (button.disabled) return;
  button.disabled = true;
  const id = document.querySelector('#memory-id').value;
  try {
    await mutateMemory(id ? `/api/memory/${id}/update` : '/api/memory', {
      category: document.querySelector('#memory-category').value.trim(),
      content: document.querySelector('#memory-content').value.trim()
    });
    resetMemoryForm();
    await loadMemory();
    memoryFeedback(id ? 'Fact updated.' : 'Fact saved locally.');
  } catch (error) { memoryFeedback(error.message); }
  finally { button.disabled = false; }
});
document.querySelector('#memory-cancel').addEventListener('click', resetMemoryForm);
document.querySelector('#memory-search').addEventListener('input', renderFacts);
document.querySelector('#memory-facts').addEventListener('click', async event => {
  const edit = event.target.closest('[data-memory-edit]');
  const remove = event.target.closest('[data-memory-delete]');
  if (edit) {
    const item = savedFacts.find(fact => fact.id === Number(edit.dataset.memoryEdit));
    if (!item) return;
    document.querySelector('#memory-id').value = item.id;
    document.querySelector('#memory-category').value = item.category;
    document.querySelector('#memory-content').value = item.content;
    document.querySelector('#memory-cancel').hidden = false;
    document.querySelector('#memory-content').focus();
  } else if (remove && window.confirm('Delete this saved fact? Previous conversations and copies already sent to a model remain.')) {
    remove.disabled = true;
    try {
      await mutateMemory(`/api/memory/${remove.dataset.memoryDelete}/delete`, {});
      if (document.querySelector('#memory-id').value === remove.dataset.memoryDelete) resetMemoryForm();
      await loadMemory();
      memoryFeedback('Fact deleted.');
    } catch (error) { memoryFeedback(error.message); remove.disabled = false; }
  }
});

document.querySelectorAll('[data-view]').forEach((button) => {
  button.addEventListener('click', () => {
    const view = button.dataset.view;
    document.querySelectorAll('.view').forEach((element) => element.classList.remove('active-view'));
    document.querySelector(`#view-${view}`).classList.add('active-view');
    document.querySelectorAll('[data-view]').forEach((element) => element.classList.toggle('active', element === button));
    document.querySelector('#crumb-current').textContent = button.textContent.trim().replace('BUILDING', '').trim();
    if (view === 'memory') loadMemory();
    if (view === 'knowledge') loadKnowledge();
    if (view === 'content') loadContentBoard();
    if (view === 'workflows') loadWorkflows();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});

function updateClock() {
  document.querySelector('#clock').textContent = new Intl.DateTimeFormat(undefined, {
    hour: '2-digit', minute: '2-digit', hour12: false
  }).format(new Date());
}
updateClock();
setInterval(updateClock, 30_000);
refreshStatus();
setInterval(refreshStatus, 60_000);

// Start a new Hermes conversation without deleting history or replaying old work.
document.querySelector('#new-conversation').addEventListener('click', async event => {
  const button = event.currentTarget;
  if (sendButton.disabled) return;
  button.disabled = true;
  sendButton.disabled = true;
  try {
    const response = await fetch('/api/chat/new', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not start a new conversation.');
    addMessage('assistant', 'New conversation ready. Previous history is preserved in Memory; earlier tasks have not been restarted.');
    document.querySelector('#include-memory').checked = false;
  } catch (error) { addMessage('assistant', error.message); }
  finally { button.disabled = false; sendButton.disabled = false; input.focus(); }
});
