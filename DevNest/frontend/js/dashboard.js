'use strict';

const app = document.querySelector('.app');
const virtualOffice = document.getElementById('virtual-office');
const dashboardViews = document.querySelectorAll('.dashboard-view');
let viewFocusTimer = 0;
const VirtualOfficeNavigation = Object.freeze({
  get view() { return app.dataset.view; },
  get connection() { return 'offline'; },
  enter() {
    clearTimeout(viewFocusTimer);
    const settings = document.getElementById('office-settings');
    if (settings.open) settings.close();
    const projects = document.getElementById('projects');
    if (projects.open) projects.close();
    app.dataset.view = 'virtual';
    dashboardViews.forEach((view) => view.setAttribute('aria-hidden','true'));
    virtualOffice.setAttribute('aria-hidden','false');
    viewFocusTimer = setTimeout(() => document.getElementById('virtual-office-heading').focus({preventScroll:true}), 400);
    return true;
  },
  leave() {
    clearTimeout(viewFocusTimer);
    app.dataset.view = 'dashboard';
    dashboardViews.forEach((view) => view.setAttribute('aria-hidden','false'));
    virtualOffice.setAttribute('aria-hidden','true');
    viewFocusTimer = setTimeout(() => document.getElementById('home').focus({preventScroll:true}), 400);
    return true;
  }
});
document.getElementById('office-portal').addEventListener('click', () => VirtualOfficeNavigation.enter());
document.getElementById('return-to-dashboard').addEventListener('click', () => VirtualOfficeNavigation.leave());
document.getElementById('brand-home').addEventListener('click', (event) => { event.preventDefault(); VirtualOfficeNavigation.leave(); });
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && VirtualOfficeNavigation.view === 'virtual') VirtualOfficeNavigation.leave();
});
const projectsDialog = document.getElementById('projects');
document.getElementById('close-projects').addEventListener('click', () => projectsDialog.close());

// Local sample tasks: deliberately no persistence or API until backend integration.
const taskInputs = [...document.querySelectorAll('.task-list input')];
function updateTaskProgress() {
  const completed = taskInputs.filter((input) => input.checked).length;
  document.getElementById('task-progress').textContent = `${completed}/${taskInputs.length}`;
}
taskInputs.forEach((input) => input.addEventListener('change', updateTaskProgress));
updateTaskProgress();
