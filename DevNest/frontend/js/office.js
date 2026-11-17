'use strict';
const $ = (id) => document.getElementById(id);
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let officeEditing = false;
let speechLayoutFrame = 0;
let placementScope = 'common';
let placementBasePreview = false;
const TimeOfDay = Object.freeze({
  labels: Object.freeze({ dawn:'해뜰 때', morning:'아침', noon:'점심', sunset:'해질 때', evening:'저녁', night:'밤' }),
  weatherLabels: Object.freeze({ clear:'맑음', cloudy:'흐림', rain:'비', snow:'눈' }),
  weatherSummaries: Object.freeze({ clear:'맑은 날 ☀', cloudy:'흐린 날 ☁', rain:'비 오는 날 ☂', snow:'눈 오는 날 ❄' }),
  assetFor(period, weather) {
    const suffix = weather === 'rain' ? '' : `_${weather}`;
    return `assets/backgrounds/office_${period}${suffix}.png`;
  },
  periodForHour(hour) {
    if (hour >= 5 && hour < 7) return 'dawn';
    if (hour >= 7 && hour < 11) return 'morning';
    if (hour >= 11 && hour < 16) return 'noon';
    if (hour >= 16 && hour < 19) return 'sunset';
    if (hour >= 19 && hour < 22) return 'evening';
    return 'night';
  },
  apply(date = new Date()) {
    const selected = OfficeSettings.current.environment.timePeriod;
    const period = selected === 'auto' ? this.periodForHour(date.getHours()) : selected;
    const weather = OfficeSettings.current.environment.weatherType;
    $('scene').dataset.time = period;
    $('scene').dataset.weather = weather;
    const background = document.querySelector('.background');
    if (background.dataset.period !== period || background.dataset.weather !== weather) {
      background.src = this.assetFor(period, weather);
      background.dataset.period = period;
      background.dataset.weather = weather;
    }
    const label = this.labels[period];
    const weatherLabel = this.weatherLabels[weather];
    $('time-period-status').textContent = selected === 'auto' ? `자동 적용 중 · 현재 ${label} · ${weatherLabel}` : `미리보기 고정 · ${label} · ${weatherLabel}`;
    $('weather-icon').dataset.weather = weather;
    $('weather-icon').querySelector('.rain-dots').textContent = weather === 'rain' ? '▪ ▪ ▪' : weather === 'snow' ? '✦' : '';
    $('weather-summary').textContent = this.weatherSummaries[weather];
    return period;
  }
});
function currentOfficeLayout() {
  return placementBasePreview && $('office-settings').open ? OfficeSettings.current.office : OfficeSettings.getLayout(OfficeState.current);
}

function updateAnimation() {
  const settings = OfficeSettings.current;
  settings.office = currentOfficeLayout();
  AnimationEngine.sync({ settings, scene: OfficeState.current, editing: officeEditing });
  CatRoaming.sync({ settings, scene: OfficeState.current, editing: officeEditing });
}
function scheduleOfficeSpeech() {
  cancelAnimationFrame(speechLayoutFrame);
  speechLayoutFrame = requestAnimationFrame(() => {
    const panel = document.querySelector('.office-panel');
    const frame = panel.getBoundingClientRect(), scene = $('scene').getBoundingClientRect();
    const actor = currentOfficeLayout().developer;
    const width = scene.width * ActorAssets.developer.baseWidth * actor.scale / 100;
    const height = width * ActorAssets.developer.height / ActorAssets.developer.width;
    // Use the visible head in the PNG, excluding its transparent top padding.
    const headX = scene.left + scene.width * actor.x / 100 + width * .08;
    const headTop = scene.top + scene.height * actor.y / 100 - height * .9;
    for (const bubble of [$('work-bubble'), $('meeting-bubble')]) {
      if (bubble.hidden) continue;
      if (bubble.classList.contains('is-unanchored')) continue;
      bubble.style.maxWidth = `${Math.min(280, Math.max(130, frame.width * .38))}px`;
      const box = bubble.getBoundingClientRect();
      const padding = 12;
      let left = Math.min(frame.width - box.width - padding, Math.max(padding, headX - frame.left + width * .08));
      let top = Math.min(frame.height - box.height - 22, Math.max(padding, headTop - frame.top - box.height - 16));
      const clock = document.querySelector('.scene-clock').getBoundingClientRect();
      if (frame.left + left < clock.right + 8 && frame.left + left + box.width > clock.left && frame.top + top < clock.bottom + 8) {
        if (clock.right - frame.left + 8 + box.width < frame.width - padding) left = clock.right - frame.left + 8;
        else top = Math.min(frame.height - box.height - 22, clock.bottom - frame.top + 8);
      }
      bubble.style.left = `${left}px`;
      bubble.style.top = `${top}px`;
      bubble.style.setProperty('--speech-tail', `${Math.max(16, Math.min(box.width - 24, headX - frame.left - left))}px`);
    }
  });
}

function syncStateBubble(developerHidden = false) {
  const settings = OfficeSettings.current;
  const state = OfficeState.current;
  const videoCall = state === 'meeting' && settings.meeting.mode === 'executive' && !officeEditing;
  const bubble = $('work-bubble');
  const message = settings.stateMessages[state] || '';
  const supported = Object.hasOwn(settings.speechPositions, state);
  bubble.textContent = message;
  bubble.classList.add('is-unanchored');
  if (supported) {
    const position = settings.speechPositions[state];
    bubble.style.left = `${position.x}%`;
    bubble.style.top = `${position.y}%`;
  } else {
    bubble.style.removeProperty('left');
    bubble.style.removeProperty('top');
  }
  bubble.style.removeProperty('max-width');
  bubble.style.removeProperty('--speech-tail');
  bubble.hidden = officeEditing || videoCall || !supported || message.trim() === '';
}

function renderOfficeScene(state, scene) {
  const settings = OfficeSettings.current;
  const awayMeeting = state === 'meeting' && settings.meeting.mode === 'away' && !officeEditing;
  const executiveMeeting = state === 'meeting' && settings.meeting.mode === 'executive' && !officeEditing;
  const videoCall = executiveMeeting;
  applyOfficePlacement(currentOfficeLayout());
  $('closed-title').textContent = settings.holidayCard.title;
  $('closed-message').textContent = settings.holidayCard.message;
  $('closed-sign').style.setProperty('--holiday-scale', settings.holidayCard.scale);
  $('scene').dataset.status = state;
  $('scene').dataset.lighting = settings.environment.lighting ? 'on' : 'off';
  $('scene').dataset.background = settings.environment.background;
  const timePeriod = TimeOfDay.apply();
  $('lighting-toggle').setAttribute('aria-pressed', String(settings.environment.lighting));
  $('lighting-toggle').setAttribute('aria-label', settings.environment.lighting ? '실내 조명 끄기' : '실내 조명 켜기');
  $('lighting-toggle').title = `${settings.environment.lighting ? '실내 조명 끄기' : '실내 조명 켜기'} · ${TimeOfDay.labels[timePeriod]}`;
  $('lighting-toggle').querySelector('span').textContent = settings.environment.lighting ? '☀' : '◐';
  $('scene').classList.toggle('video-meeting-active', videoCall);
  $('video-meeting').classList.toggle('is-executive', executiveMeeting);
  $('video-meeting').hidden = !videoCall;
  $('meeting-away-message').textContent = settings.meeting.awayMessage;
  $('meeting-away-sign').hidden = !awayMeeting;
  $('executive-sign-title').textContent = settings.meeting.executiveSign.title;
  $('executive-sign-message').textContent = settings.meeting.executiveSign.message;
  $('executive-sign').style.setProperty('--executive-scale', settings.meeting.executiveSign.scale);
  $('executive-sign').hidden = !executiveMeeting;
  document.querySelector('.office-panel').dataset.status = state;
  syncStateBubble();
  $('meeting-bubble').hidden = true;
  $('closed-sign').hidden = officeEditing || state !== 'holiday';
  $('scene-status').textContent = officeEditing ? '배치 편집' : `${OfficeState.isPreview ? '미리보기 · ' : ''}${executiveMeeting ? '대표님 회의' : scene.label}`;
  $('work-heading').textContent = OfficeState.actualScene.label;
  $('status-description').textContent = settings.stateMessages[OfficeState.actual] || OfficeState.actualScene.description;
  $('scene-caption').textContent = officeEditing ? '캐릭터를 드래그해 배치하세요' : scene.caption;
  $('actual-state').value = OfficeState.actual;
  $('header-office-state').value = OfficeState.actual;
  $('preview-status').textContent = OfficeState.isPreview ? `미리보기: ${scene.label} · 실제 상태: ${OfficeState.actualScene.label}` : '미리보기 꺼짐';
  document.querySelectorAll('button[data-status]').forEach((button) => {
    button.setAttribute('aria-pressed', String(OfficeState.isPreview && button.dataset.status === state));
  });
  updateAnimation();
  scheduleOfficeSpeech();
}
function applyOfficePlacement(layout) {
  for (const name of Object.keys(ActorAssets)) {
    const actor = $(ActorAssets[name].id);
    const position = layout[name];
    actor.style.left = `${position.x}%`;
    actor.style.top = `${position.y}%`;
    actor.style.width = `${ActorAssets[name].baseWidth * position.scale}%`;
    actor.style.aspectRatio = `${ActorAssets[name].width} / ${ActorAssets[name].height}`;
    actor.style.setProperty('--actor-z', String(position.zIndex));
    actor.classList.toggle('configured-hidden', !position.visible);
    if (name.startsWith('plant') || name.startsWith('desk')) actor.hidden = !position.visible && !officeEditing;
  }
}
function applyOfficeSettings(settings) {
  document.querySelector('.office-panel').dataset.fit = 'desk';
  renderOfficeScene(OfficeState.current, OfficeState.scene);
}
function updateClock() {
  const now = new Date();
  TimeOfDay.apply(now);
  $('clock').textContent = now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false });
  $('clock').dateTime = now.toISOString();
  $('date').textContent = now.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' });
  document.querySelectorAll('[data-widget-time]').forEach((node) => { node.textContent = $('clock').textContent; node.dateTime = now.toISOString(); });
  document.querySelectorAll('[data-widget-date]').forEach((node) => { node.textContent = $('date').textContent; });
}
document.querySelectorAll('.scene img').forEach((img) => {
  const report = () => {
    if (!img.hasAttribute('src')) return;
    $('asset-error').hidden = false;
    $('asset-error').textContent = `이미지 자산을 불러올 수 없습니다: ${img.getAttribute('src')}. 자산 경로와 파일을 확인해 주세요.`;
  };
  img.addEventListener('error', report);
  if (img.complete && img.hasAttribute('src') && !img.naturalWidth) report();
});
let clockTimer = null;
function syncClock() {
  clearInterval(clockTimer); clockTimer = null;
  if (!document.hidden) { updateClock(); clockTimer = setInterval(updateClock, 10000); }
}
document.addEventListener('visibilitychange', syncClock);
syncClock();
OfficeSettings.subscribe(applyOfficeSettings);
OfficeState.subscribe(renderOfficeScene);

document.querySelectorAll('[data-video-control]').forEach((button) => button.addEventListener('click', () => {
  const pressed = button.getAttribute('aria-pressed') === 'true';
  button.setAttribute('aria-pressed', String(!pressed));
  button.classList.toggle('is-off', !pressed);
}));
$('lighting-toggle').addEventListener('click', () => OfficeSettings.update((settings) => { settings.environment.lighting = !settings.environment.lighting; }));
$('header-office-state').addEventListener('change', () => {
  AnimationEngine.clearTests();
  if (OfficeState.isPreview) OfficeState.endPreview();
  setOfficeState($('header-office-state').value);
});
$('video-hangup').addEventListener('click', () => {
  if (OfficeState.isPreview) OfficeState.endPreview();
  else setOfficeState('working');
});

const speechResizeObserver = new ResizeObserver((entries) => {
  if (entries.some((entry) => entry.target === $('scene') || entry.target.classList.contains('actor'))) {
    // Percentage transforms may retain a compositor frame at the previous pixel size.
    // Restart discrete sprite steps after camera/scale changes, keeping wrappers fixed.
    AnimationEngine.resetLayout();
  }
  scheduleOfficeSpeech();
});
speechResizeObserver.observe(document.querySelector('.office-panel'));
speechResizeObserver.observe($('scene'));
speechResizeObserver.observe($('developer'));
speechResizeObserver.observe($('cat-layer'));

AnimationEngine.subscribe((snapshot) => {
  syncStateBubble(snapshot.actors.developer.hidden);
  const labels = { developer:'개발자', cat:'고양이', laptop:'노트북' };
  $('animation-test-status').textContent = Object.entries(snapshot.actors).map(([name, actor]) =>
    `${labels[name]}: ${actor.requested}${actor.fallback ? ` (${actor.fallback})` : snapshot.suspended && actor.state !== actor.requested ? ` → ${actor.state} (정지)` : ''}`
  ).join(' · ');
  $('end-action-tests').disabled = !snapshot.testing;
  document.querySelectorAll('[data-action-test]').forEach((button) => button.setAttribute('aria-pressed', String(Boolean(snapshot.overrides[button.dataset.actionTest]))));
  if (document.hidden) { cancelAnimationFrame(speechLayoutFrame); return; }
  scheduleOfficeSpeech();
});
