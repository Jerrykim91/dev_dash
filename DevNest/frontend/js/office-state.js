'use strict';

// State transitions have no DOM dependency. Rendering subscribes in office.js.
const OfficeState = (() => {
  const scenes = Object.freeze({
    before_work: Object.freeze({ label: '출근 전', description: '하루를 시작하기 전, 조용한 사무실.', caption: '곧 새로운 하루가 시작돼요.' }),
    working: Object.freeze({ label: '근무 중', description: '집중하는 시간. 차근차근 만들어 가요.', caption: '작은 사무실에서, 오늘도 한 줄씩.' }),
    overtime: Object.freeze({ label: '야근 중', description: '아직 켜진 모니터… 조금만 더 하고 쉬어요.', caption: '오늘의 마지막 커밋… 아마도!' }),
    meeting: Object.freeze({ label: '회의 중', description: '잠시 함께 이야기하는 시간이에요.', caption: '회의를 마치고 돌아올게요.' }),
    after_work: Object.freeze({ label: '퇴근 완료', description: '오늘도 수고했어요. 내일 다시 만나요.', caption: '오늘의 작업을 마쳤어요. 편안한 저녁 보내세요.' }),
    holiday: Object.freeze({ label: '휴무', description: '쉬어 가는 날. 재충전도 소중한 일이에요.', caption: '사무실도 쉬어 가는 하루.' })
  });
  // The selected real state is a user setting; previews remain temporary.
  let actual = OfficeSettings.current.actualState;
  let preview = null;
  const listeners = new Set();
  const notify = () => listeners.forEach((render) => render(preview || actual, scenes[preview || actual]));
  return Object.freeze({
    get current() { return preview || actual; },
    get actual() { return actual; },
    get isPreview() { return preview !== null; },
    get scene() { return scenes[preview || actual]; },
    get actualScene() { return scenes[actual]; },
    set(state) {
      if (!Object.hasOwn(scenes, state)) return false;
      if (state !== actual) {
        actual = state;
        OfficeSettings.update((settings) => { settings.actualState = state; });
        notify();
      }
      return true;
    },
    preview(state) {
      if (!Object.hasOwn(scenes, state)) return false;
      preview = state; notify(); return true;
    },
    endPreview() { preview = null; notify(); },
    subscribe(render) {
      listeners.add(render);
      render(preview || actual, scenes[preview || actual]);
      return () => listeners.delete(render);
    }
  });
})();

// Public entry point for local controls and future integrations.
function setOfficeState(state) {
  return OfficeState.set(state);
}
