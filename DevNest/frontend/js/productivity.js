'use strict';

const ProductivityTools = (() => {
  const storageKey = 'devnest.productivity';
  const defaults = Object.freeze({
    alarm: Object.freeze({ time: '18:00', message: '오늘 업무를 정리할 시간이에요.', enabled: false }),
    timer: Object.freeze({ duration: 1500, remaining: 1500, running: false, endAt: 0 })
  });
  const byId = (id) => document.getElementById(id);
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const validDurations = [300, 900, 1500, 2700, 3600];
  function normalize(input) {
    const source = input && typeof input === 'object' ? input : {};
    const alarm = source.alarm && typeof source.alarm === 'object' ? source.alarm : {};
    const timer = source.timer && typeof source.timer === 'object' ? source.timer : {};
    const duration = validDurations.includes(Number(timer.duration)) ? Number(timer.duration) : defaults.timer.duration;
    const remaining = Number.isFinite(Number(timer.remaining)) ? Math.min(duration, Math.max(0, Number(timer.remaining))) : duration;
    return {
      alarm: {
        time: typeof alarm.time === 'string' && /^([01]\d|2[0-3]):[0-5]\d$/.test(alarm.time) ? alarm.time : defaults.alarm.time,
        message: typeof alarm.message === 'string' ? alarm.message.slice(0, 80) : defaults.alarm.message,
        enabled: typeof alarm.enabled === 'boolean' ? alarm.enabled : defaults.alarm.enabled
      },
      timer: {
        duration,
        remaining,
        running: timer.running === true && Number.isFinite(Number(timer.endAt)),
        endAt: Number.isFinite(Number(timer.endAt)) ? Number(timer.endAt) : 0
      }
    };
  }
  function read() {
    try { return normalize(JSON.parse(localStorage.getItem(storageKey) || '{}')); }
    catch { return normalize({}); }
  }
  let state = read();
  let alarmTimeout = 0;
  let timerInterval = 0;
  function save() {
    try { localStorage.setItem(storageKey, JSON.stringify(state)); }
    catch { /* The live timer remains usable when storage is unavailable. */ }
  }
  function nextAlarmDate(now = new Date()) {
    const [hours, minutes] = state.alarm.time.split(':').map(Number);
    const next = new Date(now);
    next.setHours(hours, minutes, 0, 0);
    if (next <= now) next.setDate(next.getDate() + 1);
    return next;
  }
  function updateAlarmStatus() {
    const status = byId('alarm-next-status');
    if (!state.alarm.enabled) { status.textContent = '알람 꺼짐'; return; }
    const next = nextAlarmDate();
    status.textContent = `다음 알람 · ${next.toLocaleDateString('ko-KR', { month:'short', day:'numeric', weekday:'short' })} ${state.alarm.time}`;
  }
  function beep() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    try {
      const context = new AudioContextClass();
      const start = context.currentTime;
      for (let index = 0; index < 3; index += 1) {
        const oscillator = context.createOscillator(), gain = context.createGain();
        oscillator.type = 'square'; oscillator.frequency.value = 660 + index * 110;
        gain.gain.setValueAtTime(.0001, start + index * .22);
        gain.gain.exponentialRampToValueAtTime(.08, start + index * .22 + .02);
        gain.gain.exponentialRampToValueAtTime(.0001, start + index * .22 + .16);
        oscillator.connect(gain).connect(context.destination);
        oscillator.start(start + index * .22); oscillator.stop(start + index * .22 + .18);
      }
      setTimeout(() => context.close().catch(() => {}), 1000);
    } catch { /* Visual alarm remains available when audio is blocked. */ }
  }
  function triggerAlarm(title = '알람', message = state.alarm.message) {
    byId('alarm-toast-title').textContent = title;
    byId('alarm-toast-message').textContent = message || '설정한 시간이 되었습니다.';
    byId('alarm-toast').hidden = false;
    beep();
  }
  function scheduleAlarm() {
    clearTimeout(alarmTimeout); alarmTimeout = 0;
    updateAlarmStatus();
    if (!state.alarm.enabled) return;
    const delay = Math.min(2147483647, Math.max(0, nextAlarmDate().getTime() - Date.now()));
    alarmTimeout = setTimeout(() => {
      triggerAlarm('업무 알람', state.alarm.message);
      scheduleAlarm();
    }, delay);
  }
  function timerRemaining() {
    if (!state.timer.running) return state.timer.remaining;
    return Math.max(0, Math.ceil((state.timer.endAt - Date.now()) / 1000));
  }
  function formatSeconds(seconds) {
    const safe = Math.max(0, Math.ceil(seconds));
    return `${String(Math.floor(safe / 60)).padStart(2, '0')}:${String(safe % 60).padStart(2, '0')}`;
  }
  function renderTimer() {
    const remaining = timerRemaining(), ratio = state.timer.duration ? remaining / state.timer.duration : 0;
    byId('time-timer-display').textContent = formatSeconds(remaining);
    byId('time-timer-dial').style.setProperty('--timer-progress', `${Math.max(0, Math.min(1, ratio)) * 360}deg`);
    byId('time-timer-dial').setAttribute('aria-label', `남은 시간 ${Math.ceil(remaining / 60)}분`);
    byId('time-timer-toggle').textContent = state.timer.running ? '일시정지' : remaining === 0 ? '다시 시작' : '시작';
    byId('time-timer-duration').value = String(state.timer.duration);
  }
  function stopTimerInterval() { clearInterval(timerInterval); timerInterval = 0; }
  function tickTimer() {
    const remaining = timerRemaining();
    if (state.timer.running && remaining <= 0) {
      state.timer.running = false; state.timer.remaining = 0; state.timer.endAt = 0;
      stopTimerInterval(); save(); renderTimer();
      triggerAlarm('Time Timer 완료', '집중 시간이 끝났어요. 잠깐 쉬어 가세요!');
      return;
    }
    renderTimer();
  }
  function startTimerInterval() {
    stopTimerInterval();
    if (state.timer.running) timerInterval = setInterval(tickTimer, 250);
    tickTimer();
  }
  function toggleTimer() {
    if (state.timer.running) {
      state.timer.remaining = timerRemaining(); state.timer.running = false; state.timer.endAt = 0;
    } else {
      if (state.timer.remaining <= 0) state.timer.remaining = state.timer.duration;
      state.timer.running = true; state.timer.endAt = Date.now() + state.timer.remaining * 1000;
    }
    save(); startTimerInterval();
  }
  function resetTimer() {
    state.timer.running = false; state.timer.remaining = state.timer.duration; state.timer.endAt = 0;
    save(); startTimerInterval();
  }
  byId('alarm-time').value = state.alarm.time;
  byId('alarm-message').value = state.alarm.message;
  byId('alarm-enabled').checked = state.alarm.enabled;
  byId('alarm-time').addEventListener('change', () => { state.alarm.time = byId('alarm-time').value; save(); scheduleAlarm(); });
  byId('alarm-message').addEventListener('change', () => { state.alarm.message = byId('alarm-message').value.slice(0, 80); save(); });
  byId('alarm-enabled').addEventListener('change', () => { state.alarm.enabled = byId('alarm-enabled').checked; save(); scheduleAlarm(); });
  byId('alarm-test').addEventListener('click', () => triggerAlarm('알람 테스트', state.alarm.message));
  byId('alarm-dismiss').addEventListener('click', () => { byId('alarm-toast').hidden = true; });
  byId('time-timer-duration').addEventListener('change', () => {
    state.timer.duration = Number(byId('time-timer-duration').value);
    state.timer.remaining = state.timer.duration; state.timer.running = false; state.timer.endAt = 0;
    save(); startTimerInterval();
  });
  byId('time-timer-toggle').addEventListener('click', toggleTimer);
  byId('time-timer-reset').addEventListener('click', resetTimer);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { tickTimer(); scheduleAlarm(); } });
  scheduleAlarm(); startTimerInterval();
  return Object.freeze({
    storageKey,
    triggerAlarm,
    toggleTimer,
    resetTimer,
    get state() { return clone(state); }
  });
})();
