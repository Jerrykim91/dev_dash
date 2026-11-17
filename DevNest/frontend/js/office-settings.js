'use strict';
(() => {
  const dialog = $('office-settings');
  const scene = $('scene');
  const decorActors = Object.freeze({
    plantUpperLeft: '왼쪽 위 덩굴', plantDeskLeft: '왼쪽 책상', plantFloorLeft: '왼쪽 바닥',
    plantDeskRight: '오른쪽 책상', plantHangingRight: '오른쪽 위 걸이', plantSideRight: '오른쪽 탁자',
    deskBooks: '책 더미', deskLantern: '사각 조명', deskPencils: '연필꽂이', deskMug: '고양이 머그컵'
  });
  let drag = null;
  let speechPositionState = 'working';
  function refreshSpeechPositionFields(settings = OfficeSettings.current) {
    const position = settings.speechPositions[speechPositionState];
    $('speech-position-state').value = speechPositionState;
    $('speech-position-x').value = position.x;
    $('speech-position-y').value = position.y;
    $('speech-position-x-value').value = `${position.x}%`;
    $('speech-position-y-value').value = `${position.y}%`;
  }
  function setEditing(enabled) {
    officeEditing = enabled;
    $('position-edit').checked = enabled;
    scene.classList.toggle('is-editing', enabled);
    document.querySelector('.office-panel').classList.toggle('position-editing', enabled);
    dialog.classList.toggle('editing', enabled);
    document.querySelectorAll('.actor').forEach((actor) => { actor.tabIndex = enabled ? 0 : -1; });
    if (!enabled && drag) { OfficeSettings.save(); drag = null; }
    renderOfficeScene(OfficeState.current, OfficeState.scene);
  }
  function selectActor(name) {
    $('selected-actor').value = name;
    const settingsCard = Object.hasOwn(decorActors, name) ? 'decor' : name;
    document.querySelectorAll('[data-actor-settings]').forEach((card) => { card.hidden = card.dataset.actorSettings !== settingsCard; });
    if (Object.hasOwn(decorActors, name)) {
      $('plant-control-target').value = name;
      $('plant-settings-legend').textContent = `${name.startsWith('plant') ? '화분' : '책상 소품'} · ${decorActors[name]}`;
      document.querySelectorAll('[data-plant-field]').forEach((input) => { input.dataset.position = `${name}.${input.dataset.plantField}`; });
      $('plant-visible').dataset.visible = name;
    }
    document.querySelectorAll('.actor').forEach((actor) => actor.classList.toggle('is-selected', actor.dataset.actor === name));
    refreshPlacementFields();
  }
  function refreshPlacementFields(settings = OfficeSettings.current) {
    const layout = OfficeSettings.getLayout(placementScope);
    document.querySelectorAll('[data-position]').forEach((input) => {
      const [actor, field] = input.dataset.position.split('.');
      input.value = String(Number(layout[actor][field].toFixed(3)));
    });
    document.querySelectorAll('[data-visible]').forEach((input) => { input.checked = layout[input.dataset.visible].visible; });
    $('placement-scope').value = placementScope;
    const common = placementScope === 'common', custom = Object.hasOwn(settings.stateLayouts, placementScope);
    $('layout-profile-status').textContent = common ? '공통 기본 배치 편집 · 상태별 배치가 없는 상태에 적용됩니다.' : custom ? '이 상태의 독립 배치가 저장되어 있습니다.' : '현재 공통 배치를 따릅니다. 값을 바꾸면 이 상태에만 저장됩니다.';
    $('copy-common-layout').disabled = common;
    $('inherit-common-layout').disabled = common || !custom;
  }
  function setPlacementScope(scope, preview = true) {
    if (scope !== 'common' && !OfficeSettings.layoutStates.includes(scope)) return;
    if (drag) { OfficeSettings.save(); drag = null; }
    placementScope = scope;
    placementBasePreview = preview && scope === 'common';
    refreshPlacementFields();
    if (preview && dialog.open) { AnimationEngine.clearTests(); OfficeState.preview(scope === 'common' ? 'working' : scope); }
    else renderOfficeScene(OfficeState.current, OfficeState.scene);
  }
  $('placement-scope').addEventListener('change', () => setPlacementScope($('placement-scope').value));
  $('copy-common-layout').addEventListener('click', () => OfficeSettings.copyCommon(placementScope));
  $('inherit-common-layout').addEventListener('click', () => OfficeSettings.resetPositions(placementScope));
  $('preview-holiday-card').addEventListener('click', () => setPlacementScope('holiday'));
  for (const [id, field] of [['holiday-title','title'], ['holiday-message','message'], ['holiday-scale','scale']]) {
    $(id).addEventListener('input', () => OfficeSettings.update((settings) => { settings.holidayCard[field] = field === 'scale' ? Number($(id).value) : $(id).value; }));
  }
  $('open-settings').addEventListener('click', () => {
    if (!dialog.open) dialog.show(); // Non-modal: the office remains available to drag.
    setPlacementScope(OfficeState.current, false);
    $('open-settings').setAttribute('aria-expanded', 'true');
  });
  function restoreNormalScene() {
    placementBasePreview = false;
    AnimationEngine.clearTests();
    if (officeEditing) setEditing(false);
    if (OfficeState.isPreview) OfficeState.endPreview();
    $('open-settings').setAttribute('aria-expanded', 'false');
    $('open-settings').focus({ preventScroll: true });
  }
  function closeSettings() {
    restoreNormalScene();
    dialog.close();
  }
  $('close-settings').addEventListener('click', closeSettings);
  // The native close event is queued: do not reset a panel already reopened.
  dialog.addEventListener('close', () => { if (!dialog.open) restoreNormalScene(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && dialog.open && !$('projects').open) closeSettings();
  });
  $('position-edit').addEventListener('change', () => setEditing($('position-edit').checked));
  $('selected-actor').addEventListener('change', () => selectActor($('selected-actor').value));
  $('plant-control-target').addEventListener('change', () => selectActor($('plant-control-target').value));
  document.querySelectorAll('[data-position]').forEach((input) => {
    function apply(event) {
      if (input.value === '' && event.type === 'input') return;
      const [actor, field] = input.dataset.position.split('.');
      OfficeSettings.setActor(placementScope, actor, (position) => { position[field] = input.valueAsNumber; });
    }
    input.addEventListener('input', apply);
    input.addEventListener('change', apply);
  });
  document.querySelectorAll('[data-visible]').forEach((input) => {
    input.addEventListener('change', () => OfficeSettings.setActor(placementScope, input.dataset.visible, (position) => { position.visible = input.checked; }));
  });
  document.querySelectorAll('[data-test-selection]').forEach((select) => {
    select.addEventListener('change', () => OfficeSettings.update((s) => { s.animation.testActions[select.dataset.testSelection] = select.value; }));
  });
  document.querySelectorAll('[data-action-test]').forEach((button) => button.addEventListener('click', () => {
    const actor = button.dataset.actionTest;
    AnimationEngine.testActor(actor, OfficeSettings.current.animation.testActions[actor]);
    updateAnimation();
  }));
  document.querySelectorAll('[data-action-auto]').forEach((button) => button.addEventListener('click', () => { AnimationEngine.clearTests(button.dataset.actionAuto); updateAnimation(); }));
  $('end-action-tests').addEventListener('click', () => { AnimationEngine.clearTests(); updateAnimation(); });
  $('animation-mode').addEventListener('change', () => OfficeSettings.update((s) => { s.animation.mode = $('animation-mode').value; }));
  for (const [id, key] of [['hand-enabled','handEnabled'], ['blink-enabled','blinkEnabled'], ['cat-enabled','catEnabled'], ['cat-roaming','catRoaming']]) {
    $(id).addEventListener('change', () => OfficeSettings.update((s) => { s.animation[key] = $(id).checked; }));
  }
  $('animation-enabled').addEventListener('change', () => OfficeSettings.update((s) => { s.animation.enabled = $('animation-enabled').checked; }));
  $('weather-enabled').addEventListener('change', () => OfficeSettings.update((s) => { s.animation.weatherEffects = $('weather-enabled').checked; }));
  $('lighting-enabled').addEventListener('change', () => OfficeSettings.update((s) => { s.environment.lighting = $('lighting-enabled').checked; }));
  $('time-period').addEventListener('change', () => OfficeSettings.update((s) => { s.environment.timePeriod = $('time-period').value; }));
  $('weather-type').addEventListener('change', () => OfficeSettings.update((s) => { s.environment.weatherType = $('weather-type').value; }));
  $('animation-speed').addEventListener('change', () => OfficeSettings.update((s) => { s.animation.speed = Number($('animation-speed').value); }));
  $('reset-positions').addEventListener('click', () => OfficeSettings.resetPositions(placementScope));
  $('actual-state').addEventListener('change', () => { AnimationEngine.clearTests(); setPlacementScope($('actual-state').value, false); setOfficeState($('actual-state').value); });
  $('meeting-mode').addEventListener('change', () => OfficeSettings.update((settings) => { settings.meeting.mode = $('meeting-mode').value; }));
  $('meeting-away-message-input').addEventListener('input', () => OfficeSettings.update((settings) => { settings.meeting.awayMessage = $('meeting-away-message-input').value; }));
  for (const [id, field] of [['executive-sign-title-input','title'], ['executive-sign-message-input','message'], ['executive-sign-scale','scale']]) {
    $(id).addEventListener('input', () => OfficeSettings.update((settings) => { settings.meeting.executiveSign[field] = field === 'scale' ? Number($(id).value) : $(id).value; }));
  }
  document.querySelectorAll('[data-state-message]').forEach((input) => input.addEventListener('input', () => {
    OfficeSettings.update((settings) => { settings.stateMessages[input.dataset.stateMessage] = input.value; });
  }));
  $('speech-position-state').addEventListener('change', () => {
    speechPositionState = $('speech-position-state').value;
    refreshSpeechPositionFields();
    AnimationEngine.clearTests(); OfficeState.preview(speechPositionState);
  });
  for (const [id, field] of [['speech-position-x','x'], ['speech-position-y','y']]) {
    $(id).addEventListener('input', () => OfficeSettings.update((settings) => { settings.speechPositions[speechPositionState][field] = Number($(id).value); }));
  }
  $('reset-speech-position').addEventListener('click', () => OfficeSettings.update((settings) => { settings.speechPositions[speechPositionState] = OfficeSettings.defaults.speechPositions[speechPositionState]; }));
  document.querySelectorAll('button[data-status]').forEach((button) => button.addEventListener('click', () => { AnimationEngine.clearTests(); setPlacementScope(button.dataset.status, false); OfficeState.preview(button.dataset.status); }));
  $('end-preview').addEventListener('click', () => { placementBasePreview = false; AnimationEngine.clearTests(); OfficeState.endPreview(); });
  OfficeSettings.subscribe((settings, error) => {
    refreshPlacementFields(settings);
    refreshSpeechPositionFields(settings);
    $('holiday-title').value = settings.holidayCard.title;
    $('holiday-message').value = settings.holidayCard.message;
    $('holiday-scale').value = settings.holidayCard.scale;
    $('holiday-scale-value').value = `${settings.holidayCard.scale}배`;
    $('meeting-mode').value = settings.meeting.mode;
    $('meeting-away-message-input').value = settings.meeting.awayMessage;
    $('executive-sign-title-input').value = settings.meeting.executiveSign.title;
    $('executive-sign-message-input').value = settings.meeting.executiveSign.message;
    $('executive-sign-scale').value = settings.meeting.executiveSign.scale;
    $('executive-sign-scale-value').value = `${settings.meeting.executiveSign.scale}배`;
    document.querySelectorAll('[data-state-message]').forEach((input) => { input.value = settings.stateMessages[input.dataset.stateMessage]; });
    $('animation-enabled').checked = settings.animation.enabled;
    $('animation-mode').value = settings.animation.mode;
    document.querySelectorAll('[data-test-selection]').forEach((select) => { select.value = settings.animation.testActions[select.dataset.testSelection]; });
    $('hand-enabled').checked = settings.animation.handEnabled;
    $('blink-enabled').checked = settings.animation.blinkEnabled;
    $('cat-enabled').checked = settings.animation.catEnabled;
    $('cat-roaming').checked = settings.animation.catRoaming;
    $('weather-enabled').checked = settings.animation.weatherEffects;
    $('lighting-enabled').checked = settings.environment.lighting;
    $('time-period').value = settings.environment.timePeriod;
    $('weather-type').value = settings.environment.weatherType;
    // Preserve migrated fractional speeds, even if not one of the presets.
    const speed = String(settings.animation.speed);
    if (![...$('animation-speed').options].some((option) => option.value === speed)) $('animation-speed').add(new Option(`${speed}배`, speed));
    $('animation-speed').value = speed;
    $('settings-save-status').textContent = error || '설정 저장됨';
  });
  document.querySelectorAll('.actor').forEach((actor) => {
    actor.addEventListener('dragstart', (event) => event.preventDefault());
    actor.addEventListener('pointerdown', (event) => {
      if (!officeEditing || !event.isPrimary || (event.pointerType === 'mouse' && event.button !== 0)) return;
      const name = actor.dataset.actor;
      selectActor(name);
      const bounds = scene.getBoundingClientRect(), position = OfficeSettings.getLayout(placementScope)[name];
      drag = { id: event.pointerId, name, scope: placementScope, offsetX: event.clientX - bounds.left - position.x / 100 * bounds.width, offsetY: event.clientY - bounds.top - position.y / 100 * bounds.height };
      actor.setPointerCapture(event.pointerId);
      actor.focus({ preventScroll: true });
      event.preventDefault();
    });
    actor.addEventListener('pointermove', (event) => {
      if (!drag || drag.id !== event.pointerId) return;
      const bounds = scene.getBoundingClientRect();
      const x = Math.min(100, Math.max(0, (event.clientX - bounds.left - drag.offsetX) / bounds.width * 100));
      const y = Math.min(100, Math.max(0, (event.clientY - bounds.top - drag.offsetY) / bounds.height * 100));
      OfficeSettings.setActor(drag.scope, drag.name, (position) => { position.x = x; position.y = y; }, false);
    });
    function finish(event) {
      if (!drag || drag.id !== event.pointerId) return;
      drag = null;
      if (actor.hasPointerCapture(event.pointerId)) actor.releasePointerCapture(event.pointerId);
      OfficeSettings.save();
    }
    actor.addEventListener('pointerup', finish);
    actor.addEventListener('pointercancel', finish);
    actor.addEventListener('lostpointercapture', finish);
    actor.addEventListener('keydown', (event) => {
      if (!officeEditing || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault(); selectActor(actor.dataset.actor);
      const amount = event.shiftKey ? .1 : 1;
      OfficeSettings.setActor(placementScope, actor.dataset.actor, (target) => {
        const key = event.key.includes('Left') || event.key.includes('Right') ? 'x' : 'y';
        target[key] = Math.min(100, Math.max(0, target[key] + (event.key.includes('Left') || event.key.includes('Up') ? -amount : amount)));
      });
    });
  });
  OfficeState.subscribe((state) => {
    if (dialog.open && !placementBasePreview && placementScope !== state) { placementScope = state; refreshPlacementFields(); }
  });
  selectActor('developer');
})();
