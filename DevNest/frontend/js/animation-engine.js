'use strict';

// Small state machine. CSS owns discrete frames; JS owns states and lifecycle.
const AnimationEngine = (() => {
  const actions = Object.freeze({
    developer: Object.freeze(['idle', 'typing', 'blink', 'away']),
    cat: Object.freeze(['sleep', 'breathing', 'tail']),
    laptop: Object.freeze(['open', 'closed'])
  });
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const listeners = new Set(), channels = new Map();
  let context = null, overrides = {}, snapshot = null;
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const element = (id) => document.getElementById(id);
  function stop(element) {
    element.getAnimations().forEach((animation) => animation.cancel());
    element.style.animationName = 'none';
    element.style.animationPlayState = 'paused';
  }
  function channel(id, name, duration, playing) {
    const target = element(id), previous = channels.get(id);
    if (!playing) {
      if (!previous || previous.playing) stop(target);
    } else {
      // Changing a state first cancels its previous channel; unchanged states keep phase.
      if (!previous || !previous.playing || previous.name !== name) {
        stop(target);
        void target.offsetWidth;
        target.style.animationName = name;
      }
      target.style.animationDuration = `${duration}s`;
      target.style.animationIterationCount = 'infinite';
      target.style.animationPlayState = 'running';
    }
    channels.set(id, { name, playing });
  }
  function refresh() {
    if (!context) return;
    const { settings, scene, editing } = context, options = settings.animation;
    const hidden = document.hidden;
    const suspended = hidden || motion.matches || editing || !options.enabled || options.mode === 'static';
    const reason = hidden ? 'page-hidden' : motion.matches ? 'reduced-motion' : editing ? 'editing' : !options.enabled ? 'disabled' : options.mode === 'static' ? 'static-mode' : '';
    const requested = {
      developer: overrides.developer || (['working','overtime'].includes(scene) ? (options.handEnabled ? 'typing' : 'idle') : 'away'),
      cat: overrides.cat || (options.catEnabled ? 'breathing' : 'sleep'),
      laptop: overrides.laptop || (['working','overtime'].includes(scene) ? 'open' : 'closed')
    };
    const developer = {
      requested: requested.developer,
      state: editing ? 'idle' : requested.developer === 'away' ? 'away' : suspended ? 'idle' : requested.developer,
      supported: true, fallback: '', hidden: !editing && (!settings.office.developer.visible || requested.developer === 'away')
    };
    const cat = {
      requested: requested.cat,
      state: suspended || requested.cat === 'tail' ? 'sleep' : requested.cat,
      supported: requested.cat !== 'tail',
      fallback: requested.cat === 'tail' ? '꼬리 전용 자산 없음 → 정적 수면' : '',
      hidden: !editing && !settings.office.cat.visible
    };
    const laptop = {
      requested: requested.laptop, state: requested.laptop, supported: true, fallback: '',
      hidden: !editing && !settings.office.laptop.visible, powerOff: requested.laptop === 'closed'
    };
    const typing = !suspended && !developer.hidden && developer.state === 'typing';
    const blinking = !suspended && !developer.hidden && (developer.state === 'blink' || (!overrides.developer && options.blinkEnabled && developer.state !== 'away'));
    const breathing = !suspended && !cat.hidden && cat.state === 'breathing';
    element('developer').hidden = developer.hidden;
    element('cat-layer').hidden = cat.hidden;
    element('laptop').hidden = laptop.hidden;
    element('typing-viewport').hidden = !typing;
    element('developer-idle').hidden = typing;
    element('developer-blink').hidden = !blinking;
    element('cat-viewport').hidden = !breathing;
    element('cat-idle').hidden = breathing;
    const typingRate = scene === 'overtime' ? .65 : 1;
    channel('developer-animation', 'developer-typing', ActorAssets.developer.duration * typingRate / options.speed, typing);
    channel('developer-blink', 'developer-blink', 4.8 / options.speed, blinking);
    channel('cat-animation', 'developer-typing', ActorAssets.cat.duration / options.speed, breathing);
    element('laptop').classList.toggle('is-off', laptop.powerOff);
    element('laptop-open').hidden = laptop.state === 'closed';
    element('laptop-closed').hidden = laptop.state !== 'closed';
    element('monitor-off').hidden = true;
    element('monitor-status').hidden = true;
    element('laptop').title = laptop.powerOff ? '닫힌 노트북' : '사용 중';
    element('scene').classList.toggle('animations-disabled', suspended);
    element('scene').classList.toggle('weather-disabled', hidden || motion.matches || !options.enabled || !options.weatherEffects);
    element('scene').style.setProperty('--rain-duration', `${.7 / options.speed}s`);
    const actors = { developer, cat, laptop };
    for (const [actor, result] of Object.entries(actors)) {
      const wrapper = element(ActorAssets[actor].id);
      wrapper.dataset.requestedAction = result.requested;
      wrapper.dataset.animationState = result.state;
      wrapper.dataset.assetFallback = String(!result.supported);
    }
    snapshot = { scene, actors, suspended, reason, typingRate, testing: Object.keys(overrides).length > 0, overrides: { ...overrides }, playing: { typing, blinking, breathing } };
    listeners.forEach((listener) => listener(clone(snapshot)));
  }
  motion.addEventListener('change', refresh);
  document.addEventListener('visibilitychange', refresh);
  return Object.freeze({
    actions,
    get snapshot() { return snapshot ? clone(snapshot) : null; },
    sync(next) {
      if (context && (context.scene !== next.scene || (!context.editing && next.editing))) overrides = {};
      context = next; refresh();
    },
    testActor(actor, action) {
      if (!Object.hasOwn(actions, actor) || !actions[actor].includes(action)) return false;
      overrides[actor] = action; refresh(); return true;
    },
    clearTests(actor) {
      if (actor) delete overrides[actor]; else overrides = {};
      refresh();
    },
    resetLayout() {
      // Invalidate only sprite channels on a real size change; never alter placement.
      for (const id of channels.keys()) stop(element(id));
      channels.clear(); refresh();
    },
    subscribe(listener) {
      listeners.add(listener); if (snapshot) listener(clone(snapshot));
      return () => listeners.delete(listener);
    }
  });
})();
