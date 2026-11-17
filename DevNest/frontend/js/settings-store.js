'use strict';

// The UI uses this adapter only; replace it with a FastAPI adapter later.
const SettingsStorage = {
  key: 'devnest.settings',
  read() {
    for (const key of [this.key, 'devnest.officeSettings', 'devnest-office-settings']) {
      const raw = localStorage.getItem(key);
      if (raw !== null) {
        try { return JSON.parse(raw); } catch { return {}; }
      }
    }
    return {};
  },
  write(value) { localStorage.setItem(this.key, JSON.stringify(value)); }
};
const OfficeSettings = (() => {
  const defaults = {
    version: 23,
    actualState: 'working',
    office: {
      developer: { x: 43, y: 63.7, scale: 1, visible: true, zIndex: 2 },
      cat: { x: 64.5, y: 64.4, scale: 1, visible: true, zIndex: 4 },
      laptop: { x: 51.5, y: 64.4, scale: 1, visible: true, zIndex: 3 },
      plantUpperLeft: { x: 6.638755980861244, y: 50.690754516471834, scale: 1, visible: true, zIndex: 2 },
      plantDeskLeft: { x: 25.08971291866029, y: 62.16790648246546, scale: 1, visible: true, zIndex: 2 },
      plantFloorLeft: { x: 7.535885167464115, y: 90.11689691817216, scale: 1, visible: true, zIndex: 2 },
      plantDeskRight: { x: 70.72368421052632, y: 64.82465462274176, scale: 1, visible: true, zIndex: 2 },
      plantHangingRight: { x: 94.91626794258373, y: 46.3336875664187, scale: 1, visible: true, zIndex: 2 },
      plantSideRight: { x: 95.45454545454545, y: 80.34006376195538, scale: 1, visible: true, zIndex: 2 },
      deskBooks: { x: 25.8, y: 64.8, scale: 1, visible: true, zIndex: 2 },
      deskLantern: { x: 29.5, y: 64.8, scale: 1, visible: true, zIndex: 2 },
      deskPencils: { x: 33.1, y: 64.8, scale: 1, visible: true, zIndex: 2 },
      deskMug: { x: 36.8, y: 64.8, scale: 1, visible: true, zIndex: 2 }
    },
    animation: { enabled: true, weatherEffects: true, speed: 1, mode: 'animated', handEnabled: true, blinkEnabled: true, catEnabled: true, catRoaming: true, testActions: { developer: 'typing', cat: 'breathing', laptop: 'open' } },
    environment: { lighting: true, background: 'night', timePeriod: 'auto', weatherType: 'rain' },
    screen: { fit: 'desk' },
    widgets: WidgetConfig.defaults,
    stateLayouts: {},
    meeting: { mode: 'away', awayMessage: '회의실 다녀오는 중!', executiveSign: { title: '대표님 회의', message: '화상회의 중입니다', scale: 1 } },
    stateMessages: {
      before_work: '출근 준비 중이에요.',
      working: '열심히 개발 중... (아마도!)',
      overtime: '마지막 커밋만… 진짜 마지막!',
      meeting: '회의 다녀올게요!',
      after_work: '오늘도 수고했어요.',
      holiday: '오늘은 푹 쉬어 가요.'
    },
    speechPositions: {
      before_work: { x: 54, y: 16 },
      working: { x: 58, y: 18 },
      overtime: { x: 52, y: 18 },
      meeting: { x: 34, y: 19 }
    },
    profile: { displayName: '', email: '', timezone: 'Asia/Seoul' },
    integrations: {
      fastApi: { baseUrl: '' },
      googleCalendar: { calendarId: 'primary' },
      github: { username: '' },
      weather: { location: '서울' }
    },
    holidayCard: { title: 'CLOSED', message: '오늘은 쉬어 가요', scale: 1.5 }
  };
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const object = (value) => value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const number = (value, fallback, min, max) => typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max ? value : fallback;
  const boolean = (value, fallback) => typeof value === 'boolean' ? value : fallback;
  const layoutStates = Object.freeze(['before_work','working','overtime','meeting','after_work','holiday']);
  function normalizeOffice(input, baseline) {
    const office = object(input), result = {};
    for (const name of Object.keys(ActorAssets)) {
      const value = object(office[name]), fallback = baseline[name];
      const scale = number(value.scale, fallback.scale, .5, 2);
      const asset = ActorAssets[name];
      const width = asset.baseWidth * scale;
      const height = width * asset.height / asset.width * 1672 / 941;
      result[name] = {
        x: Math.min(100 - width / 2, Math.max(width / 2, number(value.x, fallback.x, 0, 100))),
        y: Math.min(100, Math.max(height, number(value.y, fallback.y, 0, 100))),
        scale, visible: boolean(value.visible, fallback.visible),
        zIndex: Math.round(number(value.zIndex ?? value.z, fallback.zIndex, 2, 20))
      };
    }
    return result;
  }
  function meetingLayout(office) {
    const layout = clone(office);
    layout.cat = { ...layout.cat, x: 51, y: 62, scale: 1.45, visible: true, zIndex: 2 };
    layout.laptop = { ...layout.laptop, x: 51.5, y: 66, scale: 1, visible: true, zIndex: 3 };
    return normalizeOffice(layout, office);
  }
  function normalize(input) {
    const source = object(input), office = object(source.office), animation = object(source.animation);
    const result = clone(defaults);
    result.actualState = layoutStates.includes(source.actualState) ? source.actualState : defaults.actualState;
    result.office = normalizeOffice(office, defaults.office);
    const profiles = object(source.stateLayouts);
    result.stateLayouts = {};
    for (const state of layoutStates) {
      if (Object.hasOwn(profiles,state) && profiles[state] && typeof profiles[state] === 'object' && !Array.isArray(profiles[state])) result.stateLayouts[state] = normalizeOffice(profiles[state], result.office);
    }
    const meeting = object(source.meeting);
    result.meeting.mode = meeting.mode === 'executive' ? 'executive' : 'away';
    result.meeting.awayMessage = typeof meeting.awayMessage === 'string' ? meeting.awayMessage.slice(0,60) : defaults.meeting.awayMessage;
    const executiveSign = object(meeting.executiveSign);
    result.meeting.executiveSign = {
      title: typeof executiveSign.title === 'string' ? executiveSign.title.slice(0,40) : defaults.meeting.executiveSign.title,
      message: typeof executiveSign.message === 'string' ? executiveSign.message.slice(0,120) : defaults.meeting.executiveSign.message,
      scale: number(executiveSign.scale, defaults.meeting.executiveSign.scale, .8, 1.8)
    };
    const stateMessages = object(source.stateMessages);
    result.stateMessages = Object.fromEntries(layoutStates.map((state) => [
      state,
      typeof stateMessages[state] === 'string' ? stateMessages[state].slice(0, 100) : defaults.stateMessages[state]
    ]));
    const speechPositions = object(source.speechPositions);
    result.speechPositions = Object.fromEntries(Object.keys(defaults.speechPositions).map((state) => {
      const position = object(speechPositions[state]), fallback = defaults.speechPositions[state];
      return [state, { x: number(position.x, fallback.x, 8, 92), y: number(position.y, fallback.y, 5, 75) }];
    }));
    const profile = object(source.profile), integrations = object(source.integrations);
    const storedText = (value, fallback, max) => typeof value === 'string' ? value.slice(0, max) : fallback;
    result.profile = {
      displayName: storedText(profile.displayName, defaults.profile.displayName, 60),
      email: storedText(profile.email, defaults.profile.email, 160),
      timezone: ['Asia/Seoul','UTC','America/Los_Angeles','Europe/London'].includes(profile.timezone) ? profile.timezone : defaults.profile.timezone
    };
    result.integrations = {
      fastApi: { baseUrl: storedText(object(integrations.fastApi).baseUrl, defaults.integrations.fastApi.baseUrl, 300) },
      googleCalendar: { calendarId: storedText(object(integrations.googleCalendar).calendarId, defaults.integrations.googleCalendar.calendarId, 200) },
      github: { username: storedText(object(integrations.github).username, defaults.integrations.github.username, 80) },
      weather: { location: storedText(object(integrations.weather).location, defaults.integrations.weather.location, 100) }
    };
    const card = object(source.holidayCard);
    result.holidayCard = {
      title: typeof card.title === 'string' ? card.title.slice(0,40) : defaults.holidayCard.title,
      message: typeof card.message === 'string' ? card.message.slice(0,200) : defaults.holidayCard.message,
      scale: number(card.scale, defaults.holidayCard.scale, 1, 2.2)
    };
    result.animation = {
      enabled: boolean(animation.enabled, true), weatherEffects: boolean(animation.weatherEffects, true),
      speed: number(animation.speed, 1, .5, 2),
      mode: animation.mode === 'static' ? 'static' : 'animated',
      handEnabled: boolean(animation.handEnabled, true), blinkEnabled: boolean(animation.blinkEnabled, true), catEnabled: boolean(animation.catEnabled, true), catRoaming: boolean(animation.catRoaming, true),
      testActions: Object.fromEntries(Object.entries({ developer:['idle','typing','blink','away'], cat:['sleep','breathing','tail'], laptop:['open','closed'] }).map(([actor, allowed]) => [actor, allowed.includes(object(animation.testActions)[actor]) ? animation.testActions[actor] : defaults.animation.testActions[actor]]))
    };
    const environment = object(source.environment);
    result.environment = {
      lighting: boolean(environment.lighting, defaults.environment.lighting),
      // Day is reserved until a real matching background asset is supplied.
      background: environment.background === 'night' ? 'night' : defaults.environment.background,
      timePeriod: ['auto','dawn','morning','noon','sunset','evening','night'].includes(environment.timePeriod) ? environment.timePeriod : defaults.environment.timePeriod,
      weatherType: ['clear','cloudy','rain','snow'].includes(environment.weatherType) ? environment.weatherType : defaults.environment.weatherType
    };
    // Desk camera is fixed; normalize previous contain/cover preferences as well.
    result.screen.fit = 'desk';
    result.widgets = WidgetConfig.normalize(source.widgets);
    return result;
  }
  function migrate(input) {
    let source = object(input);
    // Version 13 introduces a deliberate meeting-room composition. Clear only
    // the old meeting profile once so saved common/other-state layouts survive.
    if (Number(source.version || 0) < 13 && source.stateLayouts) {
      const stateLayouts = { ...object(source.stateLayouts) };
      delete stateLayouts.meeting;
      source = { ...source, stateLayouts };
    }
    // This revision changes the camera only; retain every saved actor coordinate.
    if (source.office && Number(source.version || 0) < 5) source = { ...source, screen: { ...object(source.screen), fit: 'desk' } };
    if (source.office) {
      // Preserve saved independent positions; seed the newly split laptop by the hands.
      if (!object(source.office).laptop) {
        const developer = object(source.office.developer);
        return { ...source, office: { ...source.office, laptop: {
          x: Math.min(90, number(developer.x, 43, 0, 100) + 8.5),
          y: Math.min(100, number(developer.y, 63.7, 0, 100) + .7),
          scale: number(developer.scale, 1, .5, 2), visible: true
        } } };
      }
      return source;
    }
    // Older developer controls used left-edge X and width percent, not center X.
    const old = object(source.developer || source);
    const x = old.characterX ?? old.x, y = old.characterY ?? old.y;
    const width = old.characterSize ?? old.size;
    if ([x, y, width].some((value) => typeof value === 'number')) {
      const size = number(width, 27, 13.5, 54);
      return { office: { developer: { x: number(x, 31, 0, 100) + size / 2, y: number(y, 68, 0, 100), scale: size / 27 } } };
    }
    return source;
  }
  let current, storageError = '';
  try { current = normalize(migrate(SettingsStorage.read())); }
  catch { current = clone(defaults); storageError = '저장소를 사용할 수 없어 이번 화면에서만 설정이 유지됩니다.'; }
  const listeners = new Set();
  function persist() {
    try { SettingsStorage.write(current); storageError = ''; }
    catch { storageError = '설정을 저장하지 못했습니다. 이번 화면에는 적용되지만 새로고침 후 유지되지 않을 수 있습니다.'; }
  }
  persist();
  function notify() { listeners.forEach((listener) => listener(clone(current), storageError)); }
  return Object.freeze({
    get current() { return clone(current); },
    get defaults() { return clone(defaults); },
    normalize, layoutStates,
    getLayout(scope) {
      if (scope === 'common' || !layoutStates.includes(scope)) return clone(current.office);
      return clone(current.stateLayouts[scope] || (scope === 'meeting' ? meetingLayout(current.office) : current.office));
    },
    setActor(scope, actor, mutate, save = true) {
      if (!Object.hasOwn(ActorAssets,actor) || (scope !== 'common' && !layoutStates.includes(scope))) return false;
      this.update((next) => {
        const office = scope === 'common' ? next.office : (next.stateLayouts[scope] ||= scope === 'meeting' ? meetingLayout(next.office) : clone(next.office));
        mutate(office[actor]);
      }, save);
      return true;
    },
    copyCommon(scope) {
      if (!layoutStates.includes(scope)) return false;
      this.update((next) => { next.stateLayouts[scope] = clone(next.office); });return true;
    },
    update(change, save = true) {
      const next = clone(current); change(next); current = normalize(next);
      if (save) persist();
      notify();
    },
    save() { persist(); notify(); },
    resetPositions(scope = 'common') {
      if (scope !== 'common' && !layoutStates.includes(scope)) return false;
      this.update((next) => { if(scope === 'common') next.office = clone(defaults.office); else delete next.stateLayouts[scope]; });return true;
    },
    subscribe(listener) { listeners.add(listener); listener(clone(current), storageError); return () => listeners.delete(listener); }
  });
})();
