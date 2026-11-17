'use strict';
// Tab navigation is independent of storage, widgets and animation initialization.
(() => {
  const dialog = document.getElementById('office-settings');
  if (!dialog) return;
  const tabs = [...dialog.querySelectorAll('[data-settings-tab]')];
  function selectSettingsTab(tab, focus = false) {
    for (const item of tabs) {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
      document.getElementById(item.getAttribute('aria-controls')).hidden = !active;
    }
    const content = dialog.querySelector('.settings-content');
    if (content) content.scrollTop = 0;
    if (focus) tab.focus({ preventScroll:true });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectSettingsTab(tab));
    tab.addEventListener('keydown', (event) => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault(); selectSettingsTab(tabs[next], true);
    });
  });

  dialog.dataset.tabsReady = 'true';
})();
