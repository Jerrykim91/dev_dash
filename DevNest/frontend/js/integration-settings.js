'use strict';

// Non-secret profile/integration metadata uses OfficeSettings. Credentials stay
// in this page session only and are intentionally excluded from localStorage.
(() => {
  const secrets = new Map();
  const secretInputs = [...document.querySelectorAll('[data-session-secret]')];
  const status = document.getElementById('secret-session-status');

  function updateSecretStatus() {
    const count = [...secrets.values()].filter(Boolean).length;
    status.textContent = count ? `세션에 비밀값 ${count}개 보관 중` : '입력된 비밀값 없음';
  }

  document.querySelectorAll('[data-profile-field]').forEach((input) => {
    input.addEventListener('input', () => OfficeSettings.update((settings) => {
      settings.profile[input.dataset.profileField] = input.value;
    }));
    input.addEventListener('change', () => input.reportValidity());
  });

  document.querySelectorAll('[data-integration-field]').forEach((input) => {
    input.addEventListener('input', () => OfficeSettings.update((settings) => {
      const [service, field] = input.dataset.integrationField.split('.');
      settings.integrations[service][field] = input.value;
    }));
    input.addEventListener('change', () => input.reportValidity());
  });

  secretInputs.forEach((input) => input.addEventListener('input', () => {
    if (input.value) secrets.set(input.dataset.sessionSecret, input.value);
    else secrets.delete(input.dataset.sessionSecret);
    updateSecretStatus();
  }));

  document.getElementById('clear-session-secrets').addEventListener('click', () => {
    secrets.clear();
    secretInputs.forEach((input) => { input.value = ''; });
    updateSecretStatus();
  });

  OfficeSettings.subscribe((settings) => {
    document.querySelectorAll('[data-profile-field]').forEach((input) => {
      input.value = settings.profile[input.dataset.profileField];
    });
    document.querySelectorAll('[data-integration-field]').forEach((input) => {
      const [service, field] = input.dataset.integrationField.split('.');
      input.value = settings.integrations[service][field];
    });
  });

  // Expose presence only for diagnostics. Secret values never leave this module.
  window.IntegrationSecrets = Object.freeze({
    get count() { return [...secrets.values()].filter(Boolean).length; },
    has(name) { return Boolean(secrets.get(name)); },
    clear() { document.getElementById('clear-session-secrets').click(); }
  });
  updateSecretStatus();
})();
