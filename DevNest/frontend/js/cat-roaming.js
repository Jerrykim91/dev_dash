'use strict';

// Random desk walks are a visual offset only. The saved state-specific anchor
// remains on the outer actor so roaming never mutates the user's placement.
const CatRoaming = (() => {
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const cat = document.getElementById('cat-layer');
  const scene = document.getElementById('scene');
  const walking = document.getElementById('cat-walking');
  const sleeping = document.getElementById('cat-viewport');
  const idle = document.getElementById('cat-idle');
  let context = null, timer = 0, walkAnimation = null, phase = 'stopped';
  let current = null, layoutKey = '';
  const random = (min, max) => min + Math.random() * (max - min);

  function allowed() {
    if (!context) return false;
    const { settings, scene: officeState, editing } = context;
    const options = settings.animation;
    const catTest = AnimationEngine.snapshot?.overrides?.cat;
    return !document.hidden && !motion.matches && !editing && !catTest &&
      ['working','overtime'].includes(officeState) && settings.office.cat.visible &&
      options.enabled && options.mode === 'animated' && options.catEnabled && options.catRoaming;
  }
  function clearSchedule() { clearTimeout(timer); timer = 0; }
  function cancelWalk() {
    if (walkAnimation) { walkAnimation.cancel(); walkAnimation = null; }
  }
  function base() { return context.settings.office.cat; }
  function offset(position) {
    const bounds = scene.getBoundingClientRect(), anchor = base();
    return { x:(position.x - anchor.x) / 100 * bounds.width, y:(position.y - anchor.y) / 100 * bounds.height };
  }
  function setOffset(position) {
    const delta = offset(position);
    cat.style.translate = `${delta.x}px ${delta.y}px`;
  }
  function showWalk(direction) {
    sleeping.hidden = true; idle.hidden = true; walking.hidden = false;
    cat.style.setProperty('--cat-walk-duration', `${.48 / context.settings.animation.speed}s`);
    cat.classList.add('is-roaming');
    cat.classList.toggle('faces-left', direction < 0);
  }
  function showRest() {
    walking.hidden = true; cat.classList.remove('is-roaming','faces-left');
    const engine = AnimationEngine.snapshot;
    const animateSleep = engine?.actors?.cat?.state === 'breathing' && !engine.suspended;
    sleeping.hidden = !animateSleep; idle.hidden = animateSleep;
  }
  function stop(reset = true) {
    clearSchedule(); cancelWalk(); phase = 'stopped';
    if (reset && context) { current = { x:base().x, y:base().y }; cat.style.translate = '0px 0px'; }
    showRest();
  }
  function schedule() {
    clearSchedule();
    if (!allowed()) { stop(); return; }
    phase = 'resting'; showRest();
    timer = setTimeout(() => walkTo(random(35,76), random(62.3,65.2)), random(5500,11000) / context.settings.animation.speed);
  }
  function walkTo(x, y, requestedDuration) {
    if (!allowed()) return false;
    clearSchedule(); cancelWalk();
    const width = ActorAssets.cat.baseWidth * base().scale;
    const target = {
      x:Math.max(32 + width / 2, Math.min(79 - width / 2, Number(x))),
      y:Math.max(62, Math.min(65.5, Number(y)))
    };
    if (!Number.isFinite(target.x) || !Number.isFinite(target.y)) return false;
    current ||= { x:base().x, y:base().y };
    const from = offset(current), to = offset(target);
    const distance = Math.hypot(target.x-current.x, (target.y-current.y)*2);
    const duration = requestedDuration ?? Math.max(1400, Math.min(5200, distance * 145 / context.settings.animation.speed));
    showWalk(target.x-current.x || 1); phase = 'walking';
    walkAnimation = cat.animate(
      [{ translate:`${from.x}px ${from.y}px` }, { translate:`${to.x}px ${to.y}px` }],
      { duration, easing:'linear', fill:'forwards' }
    );
    walkAnimation.onfinish = () => {
      cat.style.translate = `${to.x}px ${to.y}px`; walkAnimation.cancel(); walkAnimation = null;
      current = target; schedule();
    };
    return true;
  }
  function sync(next) {
    context = next;
    const position = next.settings.office.cat;
    const nextKey = `${next.scene}:${position.x}:${position.y}:${position.scale}`;
    if (nextKey !== layoutKey) {
      layoutKey = nextKey; stop();
      if (allowed()) schedule();
      return;
    }
    if (!allowed()) stop();
    else if (!timer && !walkAnimation) schedule();
  }
  function refresh() { if (!context) return; if (!allowed()) stop(); else sync(context); }
  motion.addEventListener('change', refresh);
  document.addEventListener('visibilitychange', refresh);
  window.addEventListener('resize', () => { if (!context) return; stop(); if (allowed()) schedule(); });
  return Object.freeze({
    sync, walkTo,
    stop:() => stop(),
    get snapshot() { return { phase, current:current ? {...current} : null, enabled:allowed() }; }
  });
})();
