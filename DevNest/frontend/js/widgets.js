'use strict';

const WidgetSystem = (() => {
  const byId=(id)=>document.getElementById(id);
  const side=byId('status-widget-slot'),bottom=byId('bottom-widget-slot'),parking=byId('widget-parking');
  const editor=byId('widget-editor'),rows=new Map(),catalog=WidgetConfig.catalog;
  const cards=new Map([
    ['smart_status.weather',document.querySelector('.weather-card')],
    ['smart_status.work',document.querySelector('.work-card')],
    ['next_schedule',document.querySelector('.next-card')],
    ['daily_schedule',byId('schedule')],['todo',byId('tasks')],['time_timer',byId('time-timer-widget')]
  ]);
  function section(className,html) {
    const node=document.createElement('section');node.className=className;node.innerHTML=html;return node;
  }
  cards.set('smart_status.time',section('status-card time-card pixel-panel',
    '<span class="widget-icon" aria-hidden="true">◷</span><div><span class="eyebrow">LOCAL TIME</span><h2><time data-widget-time>--:--</time></h2><p data-widget-date></p></div>'));
  cards.set('smart_status',section('smart-status pixel-panel',
    '<header class="widget-heading"><h2>✦ 스마트 상태</h2><span class="sample-label">날씨는 예시</span></header><div class="smart-parts"></div>'));
  function contentCard(id,title,icon,content,label='예시') {
    const card=section('widget pixel-panel',`<header class="widget-heading"><h2><span aria-hidden="true">${icon}</span>${title}</h2><span class="sample-label">${label}</span></header><div class="widget-body" tabindex="0" aria-label="${title} 내용">${content}</div>`);
    card.setAttribute('aria-label',title);cards.set(id,card);
  }
  contentCard('project_progress','프로젝트 진행','▱','<p class="project-summary">DevNest <strong>75%</strong></p><progress max="100" value="75" aria-label="DevNest 예시 진행률 75%"></progress><p>픽셀 오피스 · 위젯 설정</p><button type="button" data-widget-project>프로젝트 보기</button>');
  contentCard('github','GitHub','◇','<p class="connection-state">연결 안 됨</p><p>저장소를 연결하면 이슈와 PR을 이곳에서 확인할 수 있어요.</p>','연동 전');
  contentCard('automation','자동화','⚙','<p class="connection-state">자동화 연동 준비 중</p><p>아직 연결된 실행 기록이 없습니다.</p>','연동 전');
  contentCard('weekly_weather','주간 날씨','☂','<ul class="weekly-forecast">'+[['월','☂','8°'],['화','☂','9°'],['수','☁','11°'],['목','☀','13°'],['금','☀','12°'],['토','☁','10°'],['일','☂','9°']].map(([day,icon,temp])=>`<li><span>${day}</span><span aria-hidden="true">${icon}</span><strong>${temp}</strong></li>`).join('')+'</ul><p>실제 예보 연동 전 · 예시 데이터</p>');
  cards.forEach((card)=>{card.classList.add('dashboard-widget');if(!card.hasAttribute('tabindex'))card.tabIndex=-1;});
  const smartBody=cards.get('smart_status').querySelector('.smart-parts');
  const parts=['time','weather','work'].map((part)=>cards.get(`smart_status.${part}`));
  const emptySide=document.createElement('p'),emptyBottom=document.createElement('p');
  emptySide.className=emptyBottom.className='widget-empty';
  emptySide.textContent='표시할 상태 위젯이 없습니다. ⚙ 설정에서 선택하세요.';
  emptyBottom.textContent='선택한 위젯은 오른쪽에 표시됩니다. ⚙ 설정에서 하단 위젯을 추가할 수 있어요.';
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  let signature='',previousIds=new Set(),dragged=null;
  function message(text){byId('widget-feedback').textContent=text;}
  function current(){return OfficeSettings.current.widgets;}
  function commit(config,text) {
    const count=WidgetConfig.count(config);
    if(count<2 || count>8){
      message(`실제 카드 ${count}개가 됩니다. 최소 2개·최대 8개로 선택해 주세요.`);
      renderEditor(current());return false;
    }
    OfficeSettings.update((settings)=>{settings.widgets=config;});
    message(text || '위젯 구성을 적용했습니다.');return true;
  }
  function setVisible(id,visible){
    if(!Object.hasOwn(catalog,id)||typeof visible!=='boolean')return false;
    const config=current();config.items.find(item=>item.id===id).visible=visible;
    return commit(config);
  }
  function setSmartMode(mode){
    if(!['combined','split'].includes(mode))return false;
    const config=current();config.smartMode=mode;return commit(config,'스마트 상태 표시 방식을 변경했습니다.');
  }
  function setSize(id,size){
    if(!Object.hasOwn(catalog,id)||!WidgetConfig.sizes.includes(size))return false;
    const config=current();config.items.find(item=>item.id===id).size=size;return commit(config);
  }
  function moveTo(id,index){
    if(!Object.hasOwn(catalog,id)||!Number.isInteger(index)||index<0||index>=Object.keys(catalog).length)return false;
    const config=current(),from=config.items.findIndex(item=>item.id===id);
    const [item]=config.items.splice(from,1);config.items.splice(index,0,item);
    config.items.forEach((item,order)=>{item.order=order;});
    return commit(config,`${catalog[id].label} 순서를 변경했습니다.`);
  }
  function move(id,delta){
    if(!Object.hasOwn(catalog,id)||![-1,1].includes(delta))return false;
    return moveTo(id,current().items.findIndex(item=>item.id===id)+delta);
  }
  function renderEditor(config){
    const focused=document.activeElement,restore=editor.contains(focused);
    for(const [index,item] of config.items.entries()){
      const row=rows.get(item.id);
      row.querySelector('[data-widget-toggle]').checked=item.visible;
      row.querySelector('[data-widget-size]').value=item.size;
      row.querySelector('[data-widget-up]').disabled=index===0;
      row.querySelector('[data-widget-down]').disabled=index===config.items.length-1;
      row.setAttribute('aria-posinset',String(index+1));row.setAttribute('aria-setsize',String(config.items.length));
      editor.append(row);
    }
    byId('smart-status-mode').value=config.smartMode;
    byId('widget-count').textContent=`${WidgetConfig.count(config)}/8개`;
    if(restore && focused.isConnected){
      const target=focused.disabled?focused.closest('[data-widget-row]').querySelector('[data-widget-handle]'):focused;
      target.focus({preventScroll:true});
    }
  }
  for(const [id,definition] of Object.entries(catalog)){
    const row=document.createElement('li');row.dataset.widgetRow=id;
    row.innerHTML=`<div class="widget-edit-top"><button type="button" data-widget-handle draggable="true" aria-label="${definition.label} 순서 이동 · 위아래 방향키 지원">⠿</button><label><input type="checkbox" data-widget-toggle> ${definition.label}<small class="widget-zone-label">${definition.zone==='side'?'오른쪽':'하단'}</small></label><button type="button" data-widget-up aria-label="${definition.label} 위로">↑</button><button type="button" data-widget-down aria-label="${definition.label} 아래로">↓</button></div><label class="widget-size-setting">크기<select data-widget-size aria-label="${definition.label} 크기"><option value="small">small · 작게</option><option value="medium">medium · 보통</option><option value="large">large · 넓게</option></select></label>`;
    row.querySelector('[data-widget-toggle]').addEventListener('change',(event)=>setVisible(id,event.target.checked));
    row.querySelector('[data-widget-size]').addEventListener('change',(event)=>setSize(id,event.target.value));
    row.querySelector('[data-widget-up]').addEventListener('click',()=>move(id,-1));
    row.querySelector('[data-widget-down]').addEventListener('click',()=>move(id,1));
    const handle=row.querySelector('[data-widget-handle]');
    handle.addEventListener('keydown',(event)=>{if(['ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();move(id,event.key==='ArrowUp'?-1:1);}});
    handle.addEventListener('dragstart',(event)=>{dragged=id;event.dataTransfer.setData('text/plain',id);event.dataTransfer.effectAllowed='move';row.classList.add('widget-dragging');});
    handle.addEventListener('dragend',()=>{dragged=null;row.classList.remove('widget-dragging');});
    row.addEventListener('dragover',(event)=>{if(dragged){event.preventDefault();event.dataTransfer.dropEffect='move';}});
    row.addEventListener('drop',(event)=>{
      event.preventDefault();const source=dragged;
      if(source && Object.hasOwn(catalog,source))moveTo(source,current().items.findIndex(item=>item.id===id));
      dragged=null;rows.forEach(row=>row.classList.remove('widget-dragging'));
    });
    rows.set(id,row);editor.append(row);
  }
  byId('smart-status-mode').addEventListener('change',(event)=>setSmartMode(event.target.value));
  byId('reset-widgets').addEventListener('click',()=>commit(WidgetConfig.defaults,'기본 위젯 구성을 복원했습니다.'));
  cards.get('project_progress').querySelector('[data-widget-project]').addEventListener('click',()=>{if(!byId('projects').open)byId('projects').showModal();});
  function render(config,error){
    byId('widget-storage-warning').textContent=error;
    const nextSignature=JSON.stringify(config);
    if(nextSignature===signature)return;
    const first=!signature;signature=nextSignature;
    const expanded=WidgetConfig.expand(config),nextIds=new Set(expanded.map(item=>item.id));
    // Reparent existing cards, preserving all IDs, task input state and event listeners.
    cards.forEach((card)=>{card.hidden=true;card.removeAttribute('data-widget-card');card.classList.remove('widget-enter');parking.append(card);});
    side.replaceChildren();bottom.replaceChildren();
    const weights=[];
    for(const item of expanded){
      const card=cards.get(item.id);card.hidden=false;card.dataset.widgetCard=item.id;card.dataset.size=item.size;
      if(item.id==='smart_status'){
        for(const part of parts){part.hidden=false;smartBody.append(part);}
      }
      if(item.zone==='side'){
        side.append(card);
        const weight=({small:1,medium:1.3,large:1.7})[item.size]*(item.id==='smart_status'?2:1);
        weights.push(`minmax(${item.id==='smart_status'?170:110}px,${weight}fr)`);
      }else bottom.append(card);
      if(!first&&!previousIds.has(item.id)&&!motion.matches)card.classList.add('widget-enter');
    }
    side.style.gridTemplateRows=weights.length?weights.join(' '):'1fr';
    bottom.dataset.dense=String(expanded.filter(item=>item.zone==='bottom').length>2);
    if(!side.childElementCount)side.append(emptySide);
    if(!bottom.childElementCount)bottom.append(emptyBottom);
    if(!first&&!motion.matches){for(const slot of [side,bottom]){slot.getAnimations().forEach(a=>a.cancel());slot.animate([{opacity:.85},{opacity:1}],{duration:140});}}
    previousIds=nextIds;
    renderEditor(config);updateClock();
  }
  OfficeSettings.subscribe((settings,error)=>render(settings.widgets,error));
  motion.addEventListener('change',()=>{if(motion.matches){[side,bottom,...cards.values()].forEach(node=>node.getAnimations().forEach(animation=>animation.cancel()));}});
  return Object.freeze({
    setVisible,setSmartMode,setSize,move,moveTo,
    get config(){return current();},get visibleCount(){return WidgetConfig.count(current());},
    reset(){return commit(WidgetConfig.defaults);},
    focusWidget(id){
      if(!cards.has(id))return false;
      const card=cards.get(id);
      if(!card.hidden&&!card.closest('#widget-parking')){card.scrollIntoView({block:'nearest',behavior:'instant'});card.focus({preventScroll:true});return true;}
      byId('open-settings').click();const row=rows.get(id);row.scrollIntoView({block:'center',behavior:'instant'});row.querySelector('input').focus({preventScroll:true});
      message(`${catalog[id].label} 위젯이 숨겨져 있습니다. 표시를 켜면 해당 메뉴에서 볼 수 있어요.`);return false;
    }
  });
})();
