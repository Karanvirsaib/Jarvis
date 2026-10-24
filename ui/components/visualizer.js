const stage = document.querySelector('#stage');
const canvas = document.querySelector('#field');
const ctx = canvas.getContext('2d');
const title = document.querySelector('#state-title');
const subtitle = document.querySelector('#state-subtitle');
const code = document.querySelector('#state-code');
const mode = document.querySelector('#mode-value');
const preview = document.querySelector('#response-preview');
const talkButton = document.querySelector('#talk');
const voiceToggle = document.querySelector('#voice-toggle');
const notice = document.querySelector('#notice');
const channel = 'BroadcastChannel' in window ? new BroadcastChannel('jarvis-visualizer') : null;

const states = {
  idle: { title: 'Standing by', subtitle: 'All systems ready. Give me something to work on.', code: 'SYS // STANDBY', mode: 'IDLE' },
  listening: { title: 'I’m listening', subtitle: 'Go ahead. I’m here.', code: 'AUDIO // INBOUND', mode: 'LISTENING' },
  thinking: { title: 'On it', subtitle: 'Working through your request.', code: 'TASK // RUNNING', mode: 'WORKING' },
  speaking: { title: 'Here’s what I found', subtitle: 'Responding to you.', code: 'AUDIO // OUTBOUND', mode: 'SPEAKING' },
  error: { title: 'Needs attention', subtitle: 'Something interrupted the request.', code: 'SYS // ATTENTION', mode: 'ATTENTION' },
};
const workLines = ['Mapping the steps', 'Checking the details', 'Working through the task', 'Putting the pieces together', 'Reviewing the available options'];
let currentState = 'idle';
let recognition = null;
let noticeTimer = null;
let phraseTimer = null;
let voiceReplies = localStorage.getItem('jarvis.voiceReplies') === 'true';
let stars = [];
let width = 0;
let height = 0;
let pixelRatio = 1;
let lastFrame = 0;

function setState(next, detail = '') {
  if (!states[next]) next = 'idle';
  currentState = next;
  if (next !== 'speaking' && 'speechSynthesis' in window && window.speechSynthesis.speaking) window.speechSynthesis.cancel();
  const labels = states[next];
  stage.dataset.state = next;
  title.childNodes[0].nodeValue = `${labels.title.replace(/[.…]+$/, '')}`;
  code.textContent = labels.code;
  mode.textContent = labels.mode;
  subtitle.textContent = detail || labels.subtitle;
  clearInterval(phraseTimer);
  if (next === 'thinking' && !detail) {
    let previous = '';
    phraseTimer = setInterval(() => {
      const choices = workLines.filter((line) => line !== previous);
      previous = choices[Math.floor(Math.random() * choices.length)];
      subtitle.textContent = `${previous}…`;
    }, 3600);
  }
}

function showNotice(message) {
  notice.textContent = message;
  notice.classList.add('visible');
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => notice.classList.remove('visible'), 4300);
}

function updateVoiceButton() {
  voiceToggle.setAttribute('aria-pressed', String(voiceReplies));
  voiceToggle.innerHTML = `VOICE REPLIES <span>${voiceReplies ? 'ON' : 'OFF'}</span>`;
}
updateVoiceButton();

voiceToggle.addEventListener('click', () => {
  if (!('speechSynthesis' in window)) {
    showNotice('Spoken replies are not supported by this browser.');
    return;
  }
  voiceReplies = !voiceReplies;
  localStorage.setItem('jarvis.voiceReplies', String(voiceReplies));
  if (!voiceReplies) window.speechSynthesis.cancel();
  updateVoiceButton();
  showNotice(voiceReplies ? 'Spoken replies enabled. Browser voice will read new answers aloud.' : 'Spoken replies are off.');
});

function speakResponse(message) {
  const text = String(message || '').trim();
  preview.textContent = text;
  preview.hidden = !text;
  if (!text || !voiceReplies || !('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {
    setState('idle', text ? 'Reply ready. Ask me what you need next.' : states.idle.subtitle);
    return;
  }
  window.speechSynthesis.cancel();
  const spokenText = text.length > 1600 ? `${text.slice(0, 1600)}. I’ve put the rest on screen.` : text;
  const utterance = new SpeechSynthesisUtterance(spokenText);
  utterance.lang = 'en-IN';
  utterance.rate = 1.02;
  utterance.pitch = 0.95;
  utterance.onstart = () => setState('speaking');
  utterance.onend = () => setState('idle', 'Reply delivered. Ask me what you need next.');
  utterance.onerror = () => setState('idle', 'Reply ready. Ask me what you need next.');
  window.speechSynthesis.speak(utterance);
}

channel?.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type === 'state') setState(data.state, data.detail || '');
  if (data.type === 'response') speakResponse(data.text);
  if (data.type === 'notice') showNotice(data.text);
});

function finishRecognition(text) {
  recognition = null;
  talkButton.classList.remove('is-listening');
  talkButton.querySelector('.talk-copy small').textContent = 'CLICK TO SPEAK';
  if (text.trim()) {
    subtitle.textContent = `Heard: “${text.trim()}”`;
    channel?.postMessage({ type: 'voice-input', text: text.trim() });
  } else if (currentState === 'listening') {
    setState('idle', 'I didn’t catch that. Try again when you’re ready.');
  }
}

talkButton.addEventListener('click', () => {
  if (recognition) {
    recognition.stop();
    return;
  }
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    showNotice('Voice input is not supported here. Use Jarvis in Chrome or type in the workspace.');
    return;
  }
  recognition = new Recognition();
  recognition.lang = 'en-IN';
  recognition.interimResults = true;
  recognition.continuous = false;
  let finalText = '';
  setState('listening');
  talkButton.classList.add('is-listening');
  talkButton.querySelector('.talk-copy small').textContent = 'CLICK TO STOP';
  recognition.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const heard = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalText += `${heard} `;
      else interim += heard;
    }
    if (interim) subtitle.textContent = `Hearing: “${interim.trim()}”`;
  };
  recognition.onerror = (event) => {
    if (event.error !== 'no-speech' && event.error !== 'aborted') showNotice(`Microphone: ${event.error}`);
  };
  recognition.onend = () => finishRecognition(finalText);
  try { recognition.start(); }
  catch (_) { recognition = null; talkButton.classList.remove('is-listening'); setState('idle'); showNotice('Could not start voice input. Check browser microphone permission.'); }
});

document.querySelector('#fullscreen').addEventListener('click', async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch (_) { showNotice('Fullscreen is unavailable in this browser window.'); }
});
document.addEventListener('fullscreenchange', () => {
  const fullscreen = Boolean(document.fullscreenElement);
  document.querySelector('#fullscreen').textContent = fullscreen ? '⤢' : '⛶';
  document.querySelector('#fullscreen').setAttribute('aria-label', fullscreen ? 'Exit fullscreen' : 'Enter fullscreen');
});

function resize() {
  const rect = canvas.getBoundingClientRect();
  width = rect.width;
  height = rect.height;
  pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.floor(width * pixelRatio);
  canvas.height = Math.floor(height * pixelRatio);
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  const count = Math.min(210, Math.max(90, Math.floor(width * height / 6500)));
  stars = Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    phase: Math.random() * Math.PI * 2,
    radius: Math.random() * 1.15 + 0.25,
    speed: Math.random() * 0.7 + 0.15,
  }));
}
new ResizeObserver(resize).observe(canvas);

function draw(now) {
  requestAnimationFrame(draw);
  if (now - lastFrame < 28) return;
  lastFrame = now;
  ctx.clearRect(0, 0, width, height);
  const centerX = width / 2;
  const centerY = height * .43;
  let energy = currentState === 'listening' ? .72 : currentState === 'thinking' ? .48 : currentState === 'speaking' ? .86 : .18;
  const glow = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, Math.min(width, height) * .39);
  glow.addColorStop(0, `rgba(43,150,151,${.025 + energy * .06})`);
  glow.addColorStop(.58, 'rgba(16,67,74,.025)');
  glow.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, width, height);

  for (const star of stars) {
    const twinkle = .15 + (Math.sin(now * .0005 * star.speed + star.phase) + 1) * .2;
    ctx.fillStyle = `rgba(143,219,215,${twinkle + energy * .12})`;
    ctx.beginPath();
    ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
    ctx.fill();
  }

  const radius = Math.min(width, height) * .27;
  const rings = currentState === 'speaking' ? 5 : currentState === 'listening' ? 4 : 3;
  for (let ring = 0; ring < rings; ring++) {
    const base = radius * (.78 + ring * .12);
    const points = 220;
    ctx.beginPath();
    for (let i = 0; i <= points; i++) {
      const angle = i / points * Math.PI * 2;
      const wave = Math.sin(angle * (3 + ring) + now * .00045 + ring) * energy * (5 + ring * 1.2)
        + Math.sin(angle * 11 - now * .0008) * energy * 2.1;
      const r = base + wave;
      const x = centerX + Math.cos(angle) * r;
      const y = centerY + Math.sin(angle) * r * .82;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = `rgba(102,222,216,${.08 + energy * .12 - ring * .012})`;
    ctx.lineWidth = ring === 0 ? 1.1 : .7;
    ctx.shadowBlur = ring === 0 ? 17 : 7;
    ctx.shadowColor = 'rgba(72,224,216,.4)';
    ctx.stroke();
  }
  ctx.shadowBlur = 0;

  if (currentState === 'speaking' || currentState === 'listening') {
    const bars = 76;
    for (let i = 0; i < bars; i++) {
      const angle = i / bars * Math.PI * 2;
      const pulse = .35 + Math.abs(Math.sin(now * .004 + i * .67)) * energy;
      const inner = radius * 1.19;
      const outer = inner + 2 + pulse * 10;
      ctx.strokeStyle = `rgba(111,229,221,${.15 + pulse * .32})`;
      ctx.lineWidth = i % 4 === 0 ? 1.2 : .7;
      ctx.beginPath();
      ctx.moveTo(centerX + Math.cos(angle) * inner, centerY + Math.sin(angle) * inner * .82);
      ctx.lineTo(centerX + Math.cos(angle) * outer, centerY + Math.sin(angle) * outer * .82);
      ctx.stroke();
    }
  }
}
resize();
requestAnimationFrame(draw);

function updateClock() {
  document.querySelector('#clock').textContent = new Intl.DateTimeFormat(undefined, {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date());
}
updateClock();
setInterval(updateClock, 1000);
try {
  const active = JSON.parse(localStorage.getItem('jarvis.face.state') || 'null');
  const recentReply = JSON.parse(localStorage.getItem('jarvis.face.lastResponse') || 'null');
  if (recentReply && Date.now() - recentReply.at < 120000) {
    preview.textContent = recentReply.text;
    preview.hidden = false;
  }
  setState(active && Date.now() - active.at < 600000 ? active.state : 'idle', active?.detail || '');
} catch (_) {
  setState('idle');
}
