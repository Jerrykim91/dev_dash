'use strict';

const WidgetConfig = (() => {
  const catalog = Object.freeze({
    smart_status: Object.freeze({ label:'스마트 상태', zone:'side', size:'medium', visible:true }),
    next_schedule: Object.freeze({ label:'다음 일정', zone:'side', size:'small', visible:true }),
    daily_schedule: Object.freeze({ label:'오늘의 일정', zone:'bottom', size:'medium', visible:true }),
    todo: Object.freeze({ label:'오늘의 할 일', zone:'bottom', size:'medium', visible:true }),
    project_progress: Object.freeze({ label:'프로젝트 진행', zone:'bottom', size:'medium', visible:false }),
    github: Object.freeze({ label:'GitHub', zone:'bottom', size:'small', visible:false }),
    automation: Object.freeze({ label:'자동화', zone:'bottom', size:'small', visible:false }),
    weekly_weather: Object.freeze({ label:'주간 날씨', zone:'bottom', size:'medium', visible:false }),
    time_timer: Object.freeze({ label:'Time Timer', zone:'bottom', size:'medium', visible:false })
  });
  const keys = Object.keys(catalog), sizes = Object.freeze(['small','medium','large']);
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const defaults = { smartMode:'combined', items:keys.map((id,order) => ({ id,type:id,visible:catalog[id].visible,order,size:catalog[id].size })) };
  const count = (config) => config.items.reduce((total,item) => total + (item.visible ? item.id === 'smart_status' && config.smartMode === 'split' ? 3 : 1 : 0),0);
  function normalize(input) {
    if (!input || typeof input !== 'object' || !Array.isArray(input.items)) return clone(defaults);
    const smartMode = input.smartMode === 'split' ? 'split' : 'combined';
    const records = new Map();
    for (const item of input.items) {
      if (!item || typeof item !== 'object' || typeof item.id !== 'string' || !Object.hasOwn(catalog,item.id) || records.has(item.id)) continue;
      records.set(item.id, {
        id:item.id,type:item.id,visible:typeof item.visible === 'boolean' ? item.visible : false,
        order:typeof item.order === 'number' && Number.isFinite(item.order) ? item.order : keys.indexOf(item.id),
        size:sizes.includes(item.size) ? item.size : catalog[item.id].size
      });
    }
    const items=keys.map((id) => records.get(id) || {id,type:id,visible:false,order:keys.indexOf(id),size:catalog[id].size});
    items.sort((a,b) => a.order-b.order || keys.indexOf(a.id)-keys.indexOf(b.id));
    items.forEach((item,index) => { item.order=index; });
    const config={smartMode,items};
    // Repair corrupt stored data only. Interactive mutations reject limits instead.
    for (const item of [...items].reverse()) { if (count(config)<=8) break; item.visible=false; }
    for (const item of items) { if (count(config)>=2) break; item.visible=true; }
    return config;
  }
  function expand(config) {
    return config.items.filter((item) => item.visible).flatMap((item) => {
      if (item.id !== 'smart_status' || config.smartMode !== 'split') return [{...item,zone:catalog[item.id].zone}];
      return ['time','weather','work'].map((part,index) => ({...item,id:`smart_status.${part}`,type:part,order:item.order+index/10,zone:'side'}));
    });
  }
  return Object.freeze({ catalog,sizes,count,normalize,expand,get defaults(){return clone(defaults);} });
})();
