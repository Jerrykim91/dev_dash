"""Real Chrome smoke checks using only the Python standard library.
Run: python3 tests/browser_check.py (Chrome must be installed).
Screenshots are written to a temporary directory printed on success.
"""
import base64
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class CDP:
    def __init__(self, url):
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        self.sock = socket.create_connection((parts.hostname, parts.port), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET {parts.path} HTTP/1.1\r\nHost: {parts.netloc}\r\n'
                           f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        self.stream = self.sock.makefile('rb')
        assert b'101' in self.stream.readline(), 'WebSocket upgrade failed'
        while self.stream.readline() != b'\r\n':
            pass
        self.seq = 0
        self.errors = []

    def read(self, length):
        data = b''
        while len(data) < length:
            chunk = self.stream.read(length - len(data))
            if not chunk:
                raise RuntimeError('Chrome disconnected')
            data += chunk
        return data

    def call(self, method, **params):
        self.seq += 1
        data = json.dumps(dict(id=self.seq, method=method, params=params)).encode()
        mask = os.urandom(4)
        size = len(data)
        header = bytes([0x81, 0x80 | size]) if size < 126 else bytes([0x81, 0xfe]) + struct.pack('!H', size)
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
        while True:
            first, second = self.read(2)
            length = second & 127
            if length == 126:
                length = struct.unpack('!H', self.read(2))[0]
            elif length == 127:
                length = struct.unpack('!Q', self.read(8))[0]
            payload = self.read(length)
            if first & 15 != 1:
                raise RuntimeError(f'Unexpected WebSocket opcode {first & 15}')
            message = json.loads(payload)
            if message.get('method') == 'Runtime.exceptionThrown':
                self.errors.append(message['params'])
            if message.get('method') == 'Runtime.consoleAPICalled' and message['params']['type'] == 'error':
                self.errors.append(message['params'])
            if message.get('method') == 'Log.entryAdded' and message['params']['entry']['level'] == 'error':
                self.errors.append(message['params'])
            if message.get('id') == self.seq:
                assert 'error' not in message, message
                return message.get('result', {})

    def js(self, code):
        result = self.call('Runtime.evaluate', expression=code, awaitPromise=True, returnByValue=True)
        assert 'exceptionDetails' not in result, result
        return result['result'].get('value')


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'frontend'), **kwargs)

    def log_message(self, *_):
        pass


def main():
    chrome = os.environ.get('CHROME_BIN') or shutil.which('google-chrome') or '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    assert Path(chrome).is_file(), 'Set CHROME_BIN to your Chrome executable'
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    artifacts = Path(tempfile.mkdtemp(prefix='devnest-phase3-'))
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix='devnest-chrome-') as profile:
            with (artifacts / 'chrome.log').open('w') as log:
                process = subprocess.Popen([chrome, '--headless', '--disable-gpu', '--no-first-run',
                    '--no-default-browser-check', '--disable-background-networking',
                    '--remote-debugging-port=0', f'--user-data-dir={profile}', 'about:blank'], stdout=log, stderr=log)
                active = Path(profile) / 'DevToolsActivePort'
                for _ in range(150):
                    if active.exists():
                        break
                    assert process.poll() is None, (artifacts / 'chrome.log').read_text()
                    time.sleep(.1)
                port = active.read_text().splitlines()[0]
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list') as response:
                    page = next(p for p in json.load(response) if p['type'] == 'page')
                cdp = CDP(page['webSocketDebuggerUrl'])
                for domain in ('Runtime', 'Log', 'Page'):
                    cdp.call(f'{domain}.enable')
                def load():
                    cdp.call('Page.navigate', url=f'http://127.0.0.1:{server.server_port}/')
                    for _ in range(100):
                        if cdp.js("document.readyState==='complete' && typeof OfficeSettings!=='undefined' && typeof officeEditing!=='undefined' && !!document.getElementById('open-settings')"):
                            break
                        time.sleep(.1)
                    cdp.js("""
                      window.assert=(value,message)=>{if(!value) throw Error(message)};
                      window.byId=id=>document.getElementById(id);
                      window.visible=id=>!byId(id).hidden && getComputedStyle(byId(id)).display!=='none';
                      window.change=(id,value)=>{byId(id).value=String(value);byId(id).dispatchEvent(new Event('input',{bubbles:true}));byId(id).dispatchEvent(new Event('change',{bubbles:true}));};
                      window.near=(a,b)=>Math.abs(a-b)<.05;
                    """)
                    for _ in range(100):
                        if cdp.js("[...document.querySelectorAll('.scene img')].every(i=>i.complete && i.naturalWidth>0)"):
                            break
                        time.sleep(.05)
                    assert cdp.js("[...document.querySelectorAll('.scene img')].every(i=>i.complete && i.naturalWidth>0)"), 'Images failed'
                def click_control(id):
                    point=cdp.js("(()=>{const e=byId("+json.dumps(id)+");e.scrollIntoView({block:'nearest'});const r=e.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;const hit=document.elementFromPoint(x,y);assert(hit===e || e.contains(hit),'Blocked click: '+e.id+' by '+(hit?.id||hit?.tagName));return {x,y}})()")
                    cdp.call('Input.dispatchMouseEvent',type='mousePressed',x=point['x'],y=point['y'],button='left',buttons=1,clickCount=1)
                    cdp.call('Input.dispatchMouseEvent',type='mouseReleased',x=point['x'],y=point['y'],button='left',buttons=0,clickCount=1)
                def screenshot(name):
                    cdp.js("Promise.all([...document.querySelectorAll('#status-widget-slot,#bottom-widget-slot')].flatMap(n=>n.getAnimations({subtree:true})).map(a=>a.finished.catch(()=>{})))")
                    cdp.js("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
                    shot=cdp.call('Page.captureScreenshot',format='png')
                    (artifacts/f'{name}.png').write_bytes(base64.b64decode(shot['data']))
                cdp.call('Emulation.setDeviceMetricsOverride',width=1920,height=1080,deviceScaleFactor=1,mobile=False)
                load()
                cdp.js("assert(byId('office-settings').dataset.tabsReady==='true','Independent tab initialization');assert(OfficeSettings.current.animation.catRoaming && byId('cat-roaming').checked,'Roaming default')")
                cdp.js("assert(CatRoaming.walkTo(45,64,700) && visible('cat-walking') && CatRoaming.snapshot.phase==='walking','Deterministic cat walk start');assert(byId('cat-walk-animation').naturalWidth===2048 && byId('cat-walk-animation').getAnimations().length===1,'Four-frame cat walk strip');assert(near(byId('cat-walking').getBoundingClientRect().width/byId('cat-layer').getBoundingClientRect().width,1.12),'Walking cat scale correction');assert(near(byId('cat-walk-animation').getBoundingClientRect().width/byId('cat-walking').getBoundingClientRect().width,4),'Walk strip not clipped to one frame')")
                screenshot('cat-roaming')
                time.sleep(.8)
                cdp.js("assert(CatRoaming.snapshot.phase==='resting' && near(CatRoaming.snapshot.current.x,45) && !visible('cat-walking'),'Cat walk finish');OfficeSettings.update(s=>{s.animation.catRoaming=false});assert(!CatRoaming.snapshot.enabled && CatRoaming.snapshot.phase==='stopped' && ['0px','0px 0px'].includes(byId('cat-layer').style.translate),'Cat roam disable/reset')")
                cdp.js("assert(OfficeSettings.current.environment.lighting && byId('scene').dataset.lighting==='on' && byId('lighting-toggle').getAttribute('aria-pressed')==='true' && byId('lighting-enabled').checked,'Lighting default');byId('lighting-toggle').click();assert(!OfficeSettings.current.environment.lighting && byId('scene').dataset.lighting==='off' && byId('lighting-enabled').checked===false,'Lighting off sync');assert(JSON.parse(localStorage.getItem('devnest.settings')).environment.lighting===false,'Lighting persistence write')")
                screenshot('lighting-off')
                load()
                cdp.js("assert(!OfficeSettings.current.environment.lighting && byId('scene').dataset.lighting==='off' && byId('lighting-toggle').title.startsWith('실내 조명 켜기'),'Lighting reload');byId('lighting-toggle').click();assert(OfficeSettings.current.environment.lighting && byId('scene').dataset.lighting==='on','Lighting on restore')")
                cdp.js("""
                  assert(TimeOfDay.periodForHour(5)==='dawn' && TimeOfDay.periodForHour(6)==='dawn','Dawn boundary');
                  assert(TimeOfDay.periodForHour(7)==='morning' && TimeOfDay.periodForHour(10)==='morning','Morning boundary');
                  assert(TimeOfDay.periodForHour(11)==='noon' && TimeOfDay.periodForHour(15)==='noon','Noon boundary');
                  assert(TimeOfDay.periodForHour(16)==='sunset' && TimeOfDay.periodForHour(18)==='sunset','Sunset boundary');
                  assert(TimeOfDay.periodForHour(19)==='evening' && TimeOfDay.periodForHour(21)==='evening','Evening boundary');
                  assert(TimeOfDay.periodForHour(22)==='night' && TimeOfDay.periodForHour(4)==='night','Night boundary');
                """)
                time_grades=[]
                cdp.js("window.timeBackgroundLayer=document.querySelector('.background')")
                for period in ('dawn','morning','noon','sunset','evening','night'):
                    cdp.js(f"OfficeSettings.update(s=>{{s.environment.timePeriod='{period}'}});assert(byId('scene').dataset.time==='{period}' && byId('time-period').value==='{period}','Time grade {period}');assert(document.querySelector('.background').src.endsWith('/assets/backgrounds/office_{period}.png'),'Time asset {period}')")
                    cdp.js("new Promise((resolve,reject)=>{const image=document.querySelector('.background');if(image.complete&&image.naturalWidth)return resolve();image.addEventListener('load',resolve,{once:true});image.addEventListener('error',reject,{once:true})})")
                    cdp.js("assert(document.querySelector('.background').naturalWidth===1672 && document.querySelector('.background').naturalHeight===941,'Time asset dimensions')")
                    time_grades.append(cdp.js("document.querySelector('.background').src+'|'+getComputedStyle(document.querySelector('.ambient-lighting')).backgroundImage"))
                    screenshot(f'time-{period}')
                assert len(set(time_grades))==6,'Time assets are not distinct'
                cdp.js("assert(document.querySelector('.background')===window.timeBackgroundLayer,'Time change replaced background layer')")
                weather_assets=[]
                for weather in ('clear','cloudy','rain','snow'):
                    suffix='' if weather=='rain' else f'_{weather}'
                    cdp.js(f"OfficeSettings.update(s=>{{s.environment.timePeriod='noon';s.environment.weatherType='{weather}'}});assert(byId('scene').dataset.weather==='{weather}' && byId('weather-type').value==='{weather}','Weather {weather}');assert(document.querySelector('.background').src.endsWith('/assets/backgrounds/office_noon{suffix}.png'),'Weather asset {weather}')")
                    cdp.js("new Promise((resolve,reject)=>{const image=document.querySelector('.background');if(image.complete&&image.naturalWidth)return resolve();image.addEventListener('load',resolve,{once:true});image.addEventListener('error',reject,{once:true})})")
                    cdp.js("assert(document.querySelector('.background').naturalWidth===1672 && document.querySelector('.background').naturalHeight===941,'Weather asset dimensions')")
                    weather_assets.append(cdp.js("document.querySelector('.background').src"))
                    screenshot(f'weather-{weather}')
                assert len(set(weather_assets))==4,'Weather assets are not distinct'
                cdp.js("assert(byId('weather-summary').textContent.includes('눈') && byId('weather-icon').dataset.weather==='snow','Weather widget sync');assert(document.querySelector('.weather-card').scrollHeight<=document.querySelector('.weather-card').clientHeight+1,'Weather card overflow');OfficeSettings.update(s=>{s.environment.weatherType='rain'})")
                cdp.js("OfficeSettings.update(s=>{s.environment.timePeriod='auto'});assert(byId('scene').dataset.time===TimeOfDay.periodForHour(new Date().getHours()) && byId('time-period-status').textContent.includes('자동 적용 중'),'Automatic time grade')")
                cdp.js("assert(!document.querySelector('.header nav') && document.querySelectorAll('.nav-link').length===0,'Legacy header navigation remains');assert(byId('header-office-state').options.length===6,'Header state options');change('header-office-state','overtime');assert(OfficeState.actual==='overtime' && OfficeSettings.current.actualState==='overtime' && JSON.parse(localStorage.getItem('devnest.settings')).actualState==='overtime','Header state selection not saved');change('header-office-state','working');assert(OfficeState.actual==='working' && byId('actual-state').value==='working','Header and settings state sync')")
                cdp.js("window.normalClockSize=parseFloat(getComputedStyle(byId('clock')).fontSize);change('header-office-state','overtime');assert(getComputedStyle(byId('clock')).color==='rgb(255, 107, 116)' && parseFloat(getComputedStyle(byId('clock')).fontSize)>normalClockSize,'Overtime clock emphasis');change('header-office-state','working')")
                cdp.js("change('alarm-time','23:59');change('alarm-message','테스트 업무 알람');byId('alarm-enabled').click();assert(ProductivityTools.state.alarm.enabled && JSON.parse(localStorage.getItem(ProductivityTools.storageKey)).alarm.message==='테스트 업무 알람','Alarm persistence');ProductivityTools.triggerAlarm('알람 테스트','테스트 업무 알람');assert(!byId('alarm-toast').hidden && byId('alarm-toast-message').textContent==='테스트 업무 알람','Alarm display');byId('alarm-dismiss').click();assert(byId('alarm-toast').hidden,'Alarm dismiss');byId('alarm-enabled').click()")
                cdp.js("assert(ReadingShelf.books.length===0 && document.querySelectorAll('#reading-bookshelf .reading-book.is-empty').length===48,'Empty reading shelf');assert(byId('scene-reading-count').textContent==='0','Scene reading count');const entry=byId('reading-shelf-entry');entry.focus();assert(!entry.hasAttribute('title') && getComputedStyle(entry).outlineStyle==='none' && getComputedStyle(byId('scene-reading-preview')).display==='none' && getComputedStyle(document.querySelector('.scene-reading-badge')).display==='none','Reading shelf hotspot is visible')")
                click_control('reading-shelf-entry')
                cdp.js("assert(byId('reading-shelf-dialog').open,'Reading shelf did not open');byId('reading-title').value='클린 코드';byId('reading-author').value='로버트 C. 마틴';byId('reading-finished-at').value='2026-11-04';byId('reading-rating').value='5';byId('reading-color').value='mint';byId('reading-note').value='다시 읽고 싶은 개발 책';byId('reading-book-form').requestSubmit();assert(ReadingShelf.books.length===1 && byId('reading-count').textContent==='1권 완독','Reading book add');assert(document.querySelector('#reading-bookshelf .book-mint span').textContent==='클린 코드' && byId('scene-reading-count').textContent==='1','Reading spine render');assert(JSON.parse(localStorage.getItem(ReadingShelf.storageKey))[0].title==='클린 코드','Reading persistence write')")
                screenshot('reading-shelf')
                cdp.js("byId('reading-shelf-dialog').close()")
                load()
                cdp.js("assert(ReadingShelf.books.length===1 && byId('scene-reading-count').textContent==='1','Reading reload');ReadingShelf.open();document.querySelector('#reading-bookshelf [data-book-id]').click();assert(byId('reading-title').value==='클린 코드' && byId('delete-reading-book').disabled===false,'Reading edit selection');const id=ReadingShelf.books[0].id;assert(ReadingShelf.remove(id) && ReadingShelf.books.length===0,'Reading delete');byId('reading-shelf-dialog').close()")
                cdp.js("window.virtualSettings=JSON.stringify(OfficeSettings.current);window.virtualActual=OfficeState.actual;window.virtualDeveloper=byId('developer');assert(VirtualOfficeNavigation.view==='dashboard' && VirtualOfficeNavigation.connection==='offline','Virtual initial state');assert(parseFloat(getComputedStyle(byId('virtual-office')).transitionDuration)===.4,'Virtual transition duration')")
                click_control('office-portal')
                cdp.js("assert(VirtualOfficeNavigation.view==='virtual' && document.querySelector('.app').dataset.view==='virtual','Portal virtual entry');assert(byId('virtual-office').getAttribute('aria-hidden')==='false' && getComputedStyle(byId('virtual-office')).visibility==='visible','Virtual view visible');assert(getComputedStyle(byId('home')).pointerEvents==='none','Dashboard input state');assert(OfficeState.actual===virtualActual && JSON.stringify(OfficeSettings.current)===virtualSettings,'Portal entry changed dashboard state');assert(byId('virtual-connection-status').textContent.includes('접속 안 됨'),'Fake server connection')")
                # Headless Chrome can defer a stepped transition by one or two frames.
                # The authored duration remains 0.4s; allow scheduling headroom here.
                time.sleep(.65)
                cdp.js("assert(parseFloat(getComputedStyle(byId('home')).opacity)===0 && byId('home').getAttribute('aria-hidden')==='true','Dashboard transition did not finish')")
                screenshot('virtual-office')
                click_control('return-to-dashboard')
                time.sleep(.65)
                cdp.js("assert(VirtualOfficeNavigation.view==='dashboard' && getComputedStyle(byId('home')).visibility==='visible','Dashboard return');assert(byId('developer')===virtualDeveloper && OfficeState.actual===virtualActual && JSON.stringify(OfficeSettings.current)===virtualSettings,'Return recreated or changed dashboard')")
                click_control('office-portal')
                cdp.js("assert(VirtualOfficeNavigation.view==='virtual','Portal virtual entry')")
                time.sleep(.65)
                click_control('brand-home')
                time.sleep(.65)
                cdp.js("assert(VirtualOfficeNavigation.view==='dashboard' && OfficeState.actual===virtualActual && JSON.stringify(OfficeSettings.current)===virtualSettings,'Brand return changed state')")
                for viewport in ((1920,1080),(1024,768),(768,1024),(390,844),(320,568)):
                    cdp.call('Emulation.setDeviceMetricsOverride',width=viewport[0],height=viewport[1],deviceScaleFactor=1,mobile=False)
                    closed_main_width=cdp.js("document.querySelector('.main-grid').getBoundingClientRect().width")
                    click_control('open-settings')
                    if viewport[0] > 900:
                        cdp.js("""
                          (()=>{const content=document.querySelector('.main-grid').getBoundingClientRect(), sidebar=byId('office-settings').getBoundingClientRect();
                          assert(content.right<=sidebar.left,'Desktop settings overlaps dashboard');
                          assert(sidebar.right<=innerWidth && sidebar.top>=0,'Desktop sidebar out of viewport');})();
                        """)
                        assert cdp.js("document.querySelector('.main-grid').getBoundingClientRect().width") < closed_main_width, 'Dashboard did not shrink'
                    else:
                        cdp.js("""
                          (()=>{const header=document.querySelector('.header').getBoundingClientRect(), sidebar=byId('office-settings').getBoundingClientRect(), content=document.querySelector('.main-grid').getBoundingClientRect();
                          assert(header.bottom<=sidebar.top && sidebar.bottom<=content.top,'Mobile settings overlaps content');
                          assert(sidebar.left>=0 && sidebar.right<=innerWidth,'Mobile settings out of viewport');})();
                        """)
                    for tab in ('state','animation','integrations','widgets','office'):
                        click_control('settings-tab-'+tab)
                        cdp.js("assert(!byId('settings-panel-"+tab+"').hidden,'Pointer tab selection')")
                    click_control('settings-tab-state')
                    click_control('end-preview')
                    cdp.js("byId('preview-holiday-card').closest('details').open=true")
                    click_control('preview-holiday-card')
                    cdp.js("assert(OfficeState.current==='holiday','Pointer holiday preview')")
                    click_control('settings-tab-office')
                    click_control('position-edit')
                    cdp.js("assert(officeEditing,'Pointer editing')")
                    click_control('position-edit')
                    click_control('close-settings')
                cdp.call('Emulation.setDeviceMetricsOverride',width=1920,height=1080,deviceScaleFactor=1,mobile=False)
                cdp.js("""
                  byId('open-settings').click();byId('settings-tab-integrations').click();
                  change('profile-display-name','효원');change('profile-email','hyowon@example.com');change('profile-timezone','Asia/Seoul');
                  change('fastapi-base-url','http://raspberrypi.local:8000');change('google-calendar-id','primary');change('github-username','hyowon');change('weather-location','서울');
                  const secretValues={googleApiKey:'google-session-secret',githubToken:'github-session-secret',weatherApiKey:'weather-session-secret',customApiKey:'custom-session-secret'};
                  for(const [name,value] of Object.entries(secretValues)){const input=document.querySelector(`[data-session-secret="${name}"]`);input.value=value;input.dispatchEvent(new Event('input',{bubbles:true}));}
                  assert(IntegrationSecrets.count===4 && IntegrationSecrets.has('githubToken'),'Session secrets input');
                  const stored=localStorage.getItem('devnest.settings');
                  assert(!Object.values(secretValues).some(value=>stored.includes(value)),'Secret leaked to localStorage');
                  assert(OfficeSettings.current.profile.email==='hyowon@example.com' && OfficeSettings.current.integrations.fastApi.baseUrl==='http://raspberrypi.local:8000','Integration metadata');
                """)
                screenshot('settings-integrations')
                cdp.js("byId('close-settings').click()")
                load()
                cdp.js("""
                  assert(OfficeSettings.current.profile.displayName==='효원' && OfficeSettings.current.profile.email==='hyowon@example.com','Profile reload');
                  assert(OfficeSettings.current.integrations.github.username==='hyowon' && OfficeSettings.current.integrations.weather.location==='서울','Integration reload');
                  assert(IntegrationSecrets.count===0 && [...document.querySelectorAll('[data-session-secret]')].every(input=>input.value===''),'Session secrets survived reload');
                """)
                cdp.js("""
                  assert(!byId('office-settings').open,'Settings must start closed');
                  assert(!document.querySelector('.dev-panel'),'Developer panel must be removed');
                  assert(document.querySelectorAll('#status-widget-slot>[data-widget-card]').length===2 && WidgetSystem.visibleCount===4,'Default widget cards');
                  const canvas=document.createElement('canvas');canvas.width=2048;canvas.height=640;
                  const ctx=canvas.getContext('2d');ctx.drawImage(byId('developer-animation'),0,0);
                  assert(ctx.getImageData(0,0,1,1).data[3]===0,'Transparent sprite');
                  window.bg=document.querySelector('.background');window.bgSource=bg.src;
                  assert(near(OfficeSettings.current.office.developer.x,43),'Default center conversion');
                  window.pause=document.createElement('style');pause.textContent='.rain-pane::before{animation-play-state:paused !important}';document.head.append(pause);
                """)
                clip=cdp.js("(()=>{const r=byId('developer').getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,scale:1};})()")
                hashes=[]
                for _ in range(8):
                    time.sleep(.18)
                    shot=cdp.call('Page.captureScreenshot',format='png',clip=clip)
                    hashes.append(hashlib.sha256(base64.b64decode(shot['data'])).hexdigest())
                assert len(set(hashes))>1,'Sprite frames not moving'
                cat_clip=cdp.js("(()=>{const r=byId('cat-layer').getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,scale:1};})()")
                cat_hashes=[]
                for _ in range(5):
                    time.sleep(.65)
                    shot=cdp.call('Page.captureScreenshot',format='png',clip=cat_clip)
                    cat_hashes.append(hashlib.sha256(base64.b64decode(shot['data'])).hexdigest())
                assert len(set(cat_hashes))>1,'Sleeping cat frames not moving'
                cdp.js("pause.remove();byId('open-settings').click()")
                screenshot('desk-camera')
                cdp.js("""
                  assert(OfficeSettings.current.screen.fit==='desk','Default desk camera');
                  const camera=byId('scene').getBoundingClientRect(),frame=document.querySelector('.office-panel').getBoundingClientRect();
                  assert((frame.bottom-camera.top)/camera.height<.71,'Desk legs still in view');
                  const positions=JSON.stringify(OfficeSettings.current.office);
                  byId('position-edit').click();
                  assert(byId('scene').getBoundingClientRect().height<=frame.height,'Edit full view');
                  byId('position-edit').click();
                  assert(JSON.stringify(OfficeSettings.current.office)===positions,'Camera changed saved positions');
                """)
                cdp.js("""
                  (()=>{
                  assert([...document.querySelectorAll('.scene img')].every(i=>!i.src.endsWith('.gif')),'Old composite GIF is still loaded');
                  assert(document.querySelectorAll('.actor').length===13,'Three core objects, six plants and four desk props');
                  for(const id of ['desk-books','desk-lantern','desk-pencils','desk-mug']){
                    const image=byId(id).querySelector('img');
                    assert(image.complete && image.naturalWidth>0 && image.naturalHeight>0,'Desk prop image '+id);
                  }
                  assert(byId('laptop').querySelector('img').src.endsWith('laptop_silver.png'),'Silver laptop source');
                  change('animation-mode','static');
                  assert(visible('developer-idle') && visible('cat-idle') && !visible('typing-viewport') && !visible('cat-viewport'),'Static PNG mode');
                  assert(!visible('developer-blink'),'Static blink disabled');
                  change('animation-mode','animated');
                  byId('hand-enabled').click();assert(!visible('typing-viewport') && visible('cat-viewport'),'Independent hands toggle');byId('hand-enabled').click();
                  byId('cat-enabled').click();assert(!visible('cat-viewport') && visible('typing-viewport'),'Independent sleep toggle');byId('cat-enabled').click();
                  byId('blink-enabled').click();assert(!visible('developer-blink'),'Blink toggle');byId('blink-enabled').click();
                  const blink=byId('developer-blink').getAnimations()[0];
                  assert(blink,'Blink animation missing');
                  window.actorBefore=byId('developer').getBoundingClientRect().toJSON();
                  blink.currentTime=blink.effect.getTiming().duration*.95;
                  assert(getComputedStyle(byId('developer-blink')).opacity==='1','Closed eye frame');
                  const actorAfter=byId('developer').getBoundingClientRect();
                  assert(near(actorBefore.x,actorAfter.x)&&near(actorBefore.y,actorAfter.y)&&near(actorBefore.width,actorAfter.width),'Blink moved wrapper');
                  blink.currentTime=0;
                  // Pixel proof: no head/body changes between typing frames.
                  const c=document.createElement('canvas');c.width=2048;c.height=640;
                  const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(byId('developer-animation'),0,0);
                  const first=ctx.getImageData(0,0,512,640).data;
                  for(let f=1;f<4;f++){
                    const next=ctx.getImageData(f*512,0,512,640).data;
                    for(let y=0;y<640;y++)for(let x=0;x<512;x++){
                      if(y>=536&&y<630&&((x>=274&&x<384)||(x>=404&&x<510)))continue;
                      const o=(y*512+x)*4;
                      for(let k=0;k<4;k++)assert(first[o+k]===next[o+k],'Head/body pixels changed');
                    }
                  }
                  c.width=512;ctx.drawImage(byId('developer-blink'),0,0);const closed=ctx.getImageData(0,0,512,640).data;
                  for(let y=0;y<640;y++)for(let x=0;x<512;x++){
                    if(y>=348&&y<414&&((x>=300&&x<336)||(x>=404&&x<440)))continue;
                    const o=(y*512+x)*4;
                    for(let k=0;k<4;k++)assert(first[o+k]===closed[o+k],'Blink changed outside eye regions');
                  }
                  })();
                """)

                cdp.js("""
                  (()=>{
                    const positions=JSON.stringify(OfficeSettings.current.office);
                    assert(AnimationEngine.snapshot.scene==='working','Engine scene mapping');
                    for(const state of ['idle','typing','blink','away']) {
                      change('test-developer-action',state);
                      document.querySelector('[data-action-test="developer"]').click();
                      const result=AnimationEngine.snapshot.actors.developer;
                      assert(result.requested===state && result.state===state,'Developer state '+state);
                      assert(visible('typing-viewport')===(state==='typing'),'Typing cleanup '+state);
                      assert(visible('developer-blink')===(state==='blink'),'Blink cleanup '+state);
                      assert(visible('developer')===(state!=='away'),'Away state');
                    }
                    AnimationEngine.testActor('developer','typing');
                    const typing=byId('developer-animation').getAnimations()[0];
                    for(const state of ['sleep','breathing','tail']) {
                      change('test-cat-action',state);document.querySelector('[data-action-test="cat"]').click();
                      const result=AnimationEngine.snapshot.actors.cat;
                      assert(result.requested===state,'Cat requested state');
                      assert(result.state===(state==='tail'?'sleep':state),'Cat effective state');
                      assert(result.supported===(state!=='tail'),'Cat unsupported distinction');
                      assert(visible('cat-viewport')===(state==='breathing'),'Cat channel cleanup');
                      assert(byId('developer-animation').getAnimations()[0]===typing,'Cat reset developer animation');
                    }
                    for(const state of ['open','closed']) {
                      change('test-laptop-action',state);document.querySelector('[data-action-test="laptop"]').click();
                      const result=AnimationEngine.snapshot.actors.laptop;
                      assert(result.requested===state && result.state===state,'Laptop real lid state');
                      assert(result.supported && !result.fallback,'Real closed asset support');
                      assert(byId('laptop').classList.contains('is-off')===(state==='closed'),'Power off fallback');
                    }
                    assert(byId('animation-test-status').textContent.includes('자산 없음'),'Missing asset feedback');
                    assert(AnimationEngine.testActor('cat','missing')===false,'Invalid action accepted');
                    assert(AnimationEngine.testActor('missing','idle')===false && AnimationEngine.testActor('toString','idle')===false,'Invalid actor accepted');
                    assert(getComputedStyle(byId('developer-animation')).animationIterationCount==='infinite','Typing loop');
                    assert(getComputedStyle(byId('cat-animation')).animationIterationCount==='infinite','Cat loop');
                    for(let n=0;n<20;n++){
                      AnimationEngine.testActor('developer',n%2?'typing':'blink');
                      assert(byId('developer-animation').getAnimations().length<=1,'Stacked typing animations');
                      assert(byId('developer-blink').getAnimations().length<=1,'Stacked blink animations');
                    }
                    byId('end-action-tests').click();assert(!AnimationEngine.snapshot.testing,'Test termination');
                    assert(AnimationEngine.snapshot.actors.cat.requested==='breathing','Automatic cat restore');
                    for(const speed of [.5,1,1.5]) {
                      change('animation-speed',speed);
                      assert(near(parseFloat(getComputedStyle(byId('developer-animation')).animationDuration),.96/speed),'Engine typing speed');
                      assert(near(parseFloat(getComputedStyle(byId('cat-animation')).animationDuration),2.4/speed),'Engine cat speed');
                    }
                    change('animation-speed',1);
                    AnimationEngine.testActor('developer','idle');
                    document.querySelector('button[data-status="meeting"]').click();
                    assert(!AnimationEngine.snapshot.testing && AnimationEngine.snapshot.actors.developer.state==='away','Scene transition clears action test');
                    assert(AnimationEngine.snapshot.actors.laptop.requested==='closed','Meeting laptop closed');
                    assert(AnimationEngine.snapshot.actors.cat.state==='breathing','Cat independent of meeting');
                    byId('end-preview').click();
                    // Simulate the visibility API event to verify all owned channels stop.
                    Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
                    document.dispatchEvent(new Event('visibilitychange'));
                    assert(AnimationEngine.snapshot.reason==='page-hidden','Background suspension');
                    assert(Object.values(AnimationEngine.snapshot.playing).every(v=>!v),'Background still playing');
                    assert([...document.querySelectorAll('.actor .typing-strip,.blink-overlay')].every(i=>i.getAnimations().length===0),'Background channels retained');
                    assert(byId('scene').classList.contains('weather-disabled') && clockTimer===null,'Background rain or clock active');
                    delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));
                    assert(AnimationEngine.snapshot.playing.typing && AnimationEngine.snapshot.playing.breathing,'Visibility resume');
                    assert(JSON.stringify(OfficeSettings.current.office)===positions,'Engine modified placement');
                    const saved=JSON.parse(localStorage.getItem('devnest.settings'));
                    assert(saved.animation.testActions.cat==='tail' && saved.animation.testActions.laptop==='closed','Action selections not persisted');
                  })();
                """)
                cdp.js("""
                  assert(byId('office-settings').open,'Settings button');change('placement-scope','common');
                  change('developer-x',50);change('developer-y',78);change('developer-scale',1.1);
                  change('cat-x',78);change('cat-y',72);change('cat-scale',.8);
                  change('laptop-x',60);change('laptop-y',70);change('laptop-scale-slider',1.1);
                  change('developer-zIndex',8);change('cat-zIndex',10);change('laptop-zIndex',9);
                  assert(getComputedStyle(byId('developer')).zIndex==='8','Developer Z');
                  assert(getComputedStyle(byId('cat-layer')).zIndex==='10','Cat Z');
                  assert(getComputedStyle(byId('laptop')).zIndex==='9','Laptop Z');
                  assert(near(Number(byId('laptop-scale').value),1.1),'Laptop scale slider sync');
                  window.checkPosition=()=>{
                    const bounds=byId('scene').getBoundingClientRect();
                    for(const name of Object.keys(ActorAssets)){
                      const actor=byId(ActorAssets[name].id),r=actor.getBoundingClientRect(),p=OfficeSettings.current.office[name];
                      if(actor.hidden)continue;
                      assert(near((r.left+r.width/2-bounds.left)/bounds.width*100,p.x),'X center '+name);
                      assert(near((r.bottom-bounds.top)/bounds.height*100,p.y),'Y bottom '+name);
                      assert(r.left>=bounds.left-.1 && r.right<=bounds.right+.1 && r.top>=bounds.top-.1 && r.bottom<=bounds.bottom+.1,'Actor bounds '+name);
                    }
                  };
                  checkPosition();
                  window.savedPositions=JSON.stringify(OfficeSettings.current.office);
                  const states=['before_work','working','overtime','meeting','after_work','holiday'];
                  for(const actual of states)for(const preview of states){
                    setOfficeState(actual);
                    document.querySelector(`button[data-status="${preview}"]`).click();
                    assert(OfficeState.actual===actual && OfficeState.current===preview,'Preview must not change actual');
                    assert(byId('work-heading').textContent===OfficeState.actualScene.label,'Actual status widget');
                    assert(visible('developer')===['working','overtime'].includes(preview),'State developer visibility');
                    assert(visible('cat-layer') && visible('laptop'),'Independent cat/laptop layers');
                    assert(!visible('meeting-bubble'),'Legacy meeting bubble hidden');
                    const bubbleExpected=['before_work','working','overtime','meeting'].includes(preview);
                    assert(visible('work-bubble')===bubbleExpected,'State speech bubble visibility');
                    if(bubbleExpected){
                      const position=OfficeSettings.current.speechPositions[preview];
                      assert(byId('work-bubble').textContent===OfficeSettings.current.stateMessages[preview],'State speech bubble text');
                      assert(byId('work-bubble').classList.contains('is-unanchored'),'Speech position mode');
                      assert(byId('work-bubble').style.left===position.x+'%' && byId('work-bubble').style.top===position.y+'%','Speech saved position');
                    }
                    assert(visible('laptop-closed')===['before_work','meeting','after_work','holiday'].includes(preview),'Closed laptop scene');
                    assert(visible('meeting-away-sign')===(preview==='meeting'),'Away meeting sign');
                    if(preview==='meeting')assert(near(parseFloat(byId('cat-layer').style.left),51),'Meeting cat position');
                    assert(visible('closed-sign')===(preview==='holiday'),'Holiday scene');
                    assert(JSON.stringify(OfficeSettings.current.office)===savedPositions,'State reset position');
                    assert(bg===document.querySelector('.background') && bg.src===bgSource,'Background replaced');
                    byId('end-preview').click();assert(OfficeState.current===actual && !OfficeState.isPreview,'Restore actual');
                  }
                  setOfficeState('working');
                  assert(setOfficeState('invalid')===false && setOfficeState('toString')===false,'Invalid states');
                  change('animation-speed',2);
                  assert(near(parseFloat(getComputedStyle(byId('developer-animation')).animationDuration),.48),'Real sprite speed');
                  assert(near(parseFloat(getComputedStyle(document.querySelector('.rain-pane'),'::before').animationDuration),.35),'Rain speed');
                  byId('weather-enabled').click();
                  assert(byId('scene').classList.contains('weather-disabled'),'Weather toggle');byId('weather-enabled').click();
                  byId('animation-enabled').click();assert(!visible('typing-viewport') && visible('developer-idle'),'Animation disabled');byId('animation-enabled').click();
                  change('animation-speed',1);
                  change('placement-scope','common');byId('position-edit').click();assert(officeEditing,'Editing toggle');checkPosition();
                  change('selected-actor','cat');assert(byId('cat-layer').classList.contains('is-selected'),'Individual selection');
                  assert(byId('selected-actor').options.length===13,'Character, laptop, plants and desk prop edit targets');
                """)
                # Real mouse drag via Chrome input, not direct calls to handlers.
                def drag_actor(name,dx,dy,touch=False):
                    cdp.js(f"change('selected-actor',byId('{name}').dataset.actor)")
                    point=cdp.js(f"(()=>{{const r=byId('{name}').getBoundingClientRect();return {{x:r.left+r.width/2,y:r.top+r.height/2}}}})()")
                    if touch:
                        cdp.call('Emulation.setTouchEmulationEnabled',enabled=True,maxTouchPoints=1)
                        cdp.call('Input.dispatchTouchEvent',type='touchStart',touchPoints=[dict(x=point['x'],y=point['y'],id=0)])
                        cdp.call('Input.dispatchTouchEvent',type='touchMove',touchPoints=[dict(x=point['x']+dx,y=point['y']+dy,id=0)])
                        cdp.call('Input.dispatchTouchEvent',type='touchEnd',touchPoints=[])
                    else:
                        cdp.call('Input.dispatchMouseEvent',type='mousePressed',x=point['x'],y=point['y'],button='left',buttons=1,clickCount=1)
                        cdp.call('Input.dispatchMouseEvent',type='mouseMoved',x=point['x']+dx,y=point['y']+dy,button='left',buttons=1)
                        cdp.call('Input.dispatchMouseEvent',type='mouseReleased',x=point['x']+dx,y=point['y']+dy,button='left',buttons=0,clickCount=1)
                    time.sleep(.1)
                before=cdp.js('OfficeSettings.current.office.developer.x')
                drag_actor('developer',60,15)
                assert cdp.js('OfficeSettings.current.office.developer.x')>before+1,'Mouse drag failed'
                cdp.js("checkPosition();assert(near(Number(byId('developer-x').value),OfficeSettings.current.office.developer.x),'Drag input sync')")
                before=cdp.js('OfficeSettings.current.office.cat.x')
                drag_actor('cat-layer',-35,12,touch=True)
                assert cdp.js('OfficeSettings.current.office.cat.x')<before-1,'Touch drag failed'
                cdp.js("checkPosition();assert(near(JSON.parse(localStorage.getItem('devnest.settings')).office.cat.x,OfficeSettings.current.office.cat.x),'Touch drag saved')")
                before=cdp.js('OfficeSettings.current.office.laptop.x')
                cat_before=cdp.js('OfficeSettings.current.office.cat.x')
                drag_actor('laptop',35,5)
                assert cdp.js('OfficeSettings.current.office.laptop.x')>before+1,'Laptop drag failed'
                assert cdp.js('OfficeSettings.current.office.cat.x')==cat_before,'Laptop moved cat'
                cdp.js("checkPosition();assert(near(Number(byId('laptop-x').value),OfficeSettings.current.office.laptop.x),'Laptop position sync')")
                plant_before=cdp.js('OfficeSettings.current.office.plantDeskLeft.x')
                drag_actor('plant-desk-left',25,0)
                assert cdp.js('OfficeSettings.current.office.plantDeskLeft.x')>plant_before,'Plant drag failed'
                cdp.js("assert(byId('plant-control-target').value==='plantDeskLeft','Plant control selection sync');checkPosition();byId('plant-visible').click();assert(byId('plant-desk-left').classList.contains('configured-hidden') && !byId('plant-desk-left').hidden,'Hidden plant remains editable');byId('position-edit').click();assert(byId('plant-desk-left').hidden,'Plant visibility');byId('plant-visible').click();assert(!byId('plant-desk-left').hidden,'Plant visibility restore');byId('position-edit').click()")
                prop_before=cdp.js('OfficeSettings.current.office.deskMug.x')
                plant_before=cdp.js('OfficeSettings.current.office.plantDeskLeft.x')
                drag_actor('desk-mug',-25,0)
                assert cdp.js('OfficeSettings.current.office.deskMug.x')<prop_before,'Desk prop drag failed'
                assert cdp.js('OfficeSettings.current.office.plantDeskLeft.x')==plant_before,'Desk prop moved plant'
                cdp.js("assert(byId('plant-control-target').value==='deskMug','Desk prop control selection sync');assert(byId('plant-settings-legend').textContent.includes('책상 소품'),'Desk prop legend');checkPosition();byId('plant-visible').click();assert(byId('desk-mug').classList.contains('configured-hidden') && !byId('desk-mug').hidden,'Hidden desk prop remains editable');byId('position-edit').click();assert(byId('desk-mug').hidden,'Desk prop visibility');byId('plant-visible').click();assert(!byId('desk-mug').hidden,'Desk prop visibility restore');byId('position-edit').click()")
                drag_actor('developer',-1400,-900)
                cdp.js("checkPosition();byId('developer').focus()")
                before=cdp.js('OfficeSettings.current.office.developer.x')
                cdp.call('Input.dispatchKeyEvent',type='keyDown',key='ArrowRight',code='ArrowRight')
                cdp.call('Input.dispatchKeyEvent',type='keyUp',key='ArrowRight',code='ArrowRight')
                assert cdp.js('OfficeSettings.current.office.developer.x')>before,'Keyboard positioning failed'
                cdp.js("byId('position-edit').click();change('developer-x',50);change('developer-y',78);change('developer-scale',1);change('cat-x',75.5);change('cat-y',65);change('cat-scale',1)")
                expected=cdp.js('OfficeSettings.current.office')
                load()
                assert cdp.js('OfficeSettings.current.office')==expected,'Reload lost positions and depth'
                cdp.js("assert(!AnimationEngine.snapshot.testing,'Test activation persisted');assert(OfficeSettings.current.animation.testActions.cat==='tail','Saved action selection lost')")
                cdp.js("byId('open-settings').click();change('placement-scope','common');byId('developer-visible').click();assert(!visible('developer'),'Visibility setting');byId('developer-visible').click();byId('close-settings').click()")
                for width,height in ((1920,1080),(1366,768),(1024,768),(900,700),(768,1024),(600,800),(390,844),(320,568)):
                    cdp.call('Emulation.setDeviceMetricsOverride',width=width,height=height,deviceScaleFactor=1,mobile=False)
                    cdp.js("""
                      assert(document.documentElement.scrollWidth<=innerWidth,'Horizontal overflow');
                      var scene=byId('scene').getBoundingClientRect(),r=byId('developer').getBoundingClientRect();
                      assert(scene.width>0 && near(scene.width/scene.height,1672/941),'Scene ratio');
                      assert(near((r.left+r.width/2-scene.left)/scene.width*100,OfficeSettings.current.office.developer.x),'Responsive X');
                      assert(near((r.bottom-scene.top)/scene.height*100,OfficeSettings.current.office.developer.y),'Responsive Y');
                      if(innerWidth>=1024)assert(document.documentElement.scrollHeight<=innerHeight,'Desktop page scroll');
                    """)
                    screenshot(f'dashboard-{width}')
                    cdp.js("""
                      var speechFrame=document.querySelector('.office-panel').getBoundingClientRect(),speechBounds=byId('work-bubble').getBoundingClientRect();
                      assert(speechBounds.left>=speechFrame.left && speechBounds.right<=speechFrame.right && speechBounds.top>=speechFrame.top && speechBounds.bottom<=speechFrame.bottom,'Speech outside frame');
                    """)
                cdp.call('Emulation.setDeviceMetricsOverride',width=1920,height=1080,deviceScaleFactor=1,mobile=False)
                cdp.js("byId('open-settings').click();change('placement-scope','common');assert(!byId('office-fit') && !byId('screen-heading'),'Screen settings not removed');byId('position-edit').click()")
                before=cdp.js('OfficeSettings.current.office.developer.x')
                drag_actor('developer',50,0)
                assert cdp.js('OfficeSettings.current.office.developer.x')>before,'Desk editing coordinates failed'
                screenshot('settings-position-edit')
                cdp.js("""
                  setOfficeState('meeting');OfficeState.preview('holiday');byId('close-settings').click();
                  assert(!officeEditing && !OfficeState.isPreview && OfficeState.current==='meeting','Close restores state');
                  setOfficeState('working');byId('open-settings').click();change('placement-scope','common');byId('reset-positions').click();
                  assert(JSON.stringify(OfficeSettings.current.office)===JSON.stringify(OfficeSettings.defaults.office),'Reset positions');
                """)
                cdp.call('Emulation.setEmulatedMedia',features=[dict(name='prefers-reduced-motion',value='reduce')])
                time.sleep(.1)
                cdp.js("assert(!visible('typing-viewport') && visible('developer-idle'),'Reduced sprite');assert(!visible('developer-blink'),'Reduced blink');assert(!visible('cat-viewport') && visible('cat-idle'),'Reduced cat');assert(byId('scene').classList.contains('weather-disabled'),'Reduced rain')")
                cdp.call('Emulation.setEmulatedMedia',features=[dict(name='prefers-reduced-motion',value='no-preference')])
                time.sleep(.1)
                cdp.js("assert(visible('typing-viewport'),'Motion restore');byId('close-settings').click()")
                cdp.js("localStorage.setItem('devnest.settings',JSON.stringify({office:{developer:{x:-90,y:999,scale:-1},cat:{x:70,y:80,scale:1}},animation:{speed:99,enabled:'yes'},screen:{fit:'cover'}}))")
                load()
                cdp.js("assert(OfficeSettings.current.office.developer.x===43 && OfficeSettings.current.animation.speed===1,'Invalid field defaults');assert(OfficeSettings.current.office.cat.x===70,'Valid field preserved');assert(OfficeSettings.current.screen.fit==='desk' && document.querySelector('.office-panel').dataset.fit==='desk','Legacy camera not normalized');localStorage.setItem('devnest.settings','{broken')")
                load()
                cdp.js("assert(OfficeSettings.current.office.developer.x===43,'Malformed JSON defaults');localStorage.removeItem('devnest.settings');localStorage.setItem('devnest.officeSettings',JSON.stringify({characterX:20,characterY:70,characterSize:20}))")
                load()
                cdp.js("assert(near(OfficeSettings.current.office.developer.x,30),'Legacy left-to-center migration');assert(near(OfficeSettings.current.office.developer.scale,20/27),'Legacy scale migration');OfficeSettings.update(s=>{s.animation.catRoaming=false})")
                # Per-state placement remains isolated from the common layout and actual status.
                cdp.js("""
                  (()=>{
                    setOfficeState('working');byId('open-settings').click();
                    const base=JSON.stringify(OfficeSettings.current.office);
                    change('placement-scope','holiday');change('cat-x',72);change('cat-y',64);change('cat-scale',1.2);
                    change('laptop-x',55);change('laptop-scale',.9);
                    assert(OfficeState.actual==='working' && OfficeState.current==='holiday','Profile selection actual state');
                    assert(JSON.stringify(OfficeSettings.current.office)===base,'Profile overwrote common');
                    assert(OfficeSettings.getLayout('holiday').cat.x===72 && byId('cat-layer').style.left==='72%','Holiday placement live');
                    change('placement-scope','before_work');change('cat-x',30);
                    assert(visible('laptop-closed') && !visible('laptop-open'),'Before work lid closed');
                    change('placement-scope','after_work');assert(visible('laptop-closed'),'After work lid closed');
                    change('placement-scope','holiday');assert(byId('cat-layer').style.left==='72%','Holiday profile restored');
                    change('holiday-title','쉬어 가는 날');change('holiday-message','오늘은 휴무입니다.\\n내일 만나요!');change('holiday-scale',1.8);
                    assert(byId('closed-title').textContent==='쉬어 가는 날' && byId('closed-message').textContent.includes('내일'),'Holiday text');
                    assert(byId('closed-sign').getBoundingClientRect().width>=400,'Holiday card enlarged');
                    window.profileExpected=OfficeSettings.current;
                    byId('close-settings').click();assert(OfficeState.current==='working' && !OfficeState.isPreview,'Profile preview restore');
                    assert(byId('cat-layer').style.left===OfficeSettings.current.office.cat.x+'%','Restored actual layout');
                  })();
                """)
                cdp.js("byId('open-settings').click();change('placement-scope','holiday');change('holiday-scale',1);window.smallBoard=byId('closed-sign').getBoundingClientRect().width;change('holiday-scale',2.2);assert(byId('closed-sign').getBoundingClientRect().width>smallBoard*1.5,'Board width growth');assert(document.querySelectorAll('.shutter-pane').length===8,'Shutter panes')")
                screenshot('holiday-shutters')
                cdp.js("change('placement-scope','after_work')")
                screenshot('after-work-shutters')
                cdp.js("change('holiday-scale',1.8);byId('close-settings').click()")
                cdp.js("byId('open-settings').click();change('placement-scope','overtime');assert(OfficeState.current==='overtime','Overtime preview');assert(!byId('developer').hidden && visible('laptop-open'),'Overtime actors');assert(getComputedStyle(document.querySelector('.dark-circles')).display==='block','Overtime circles');assert(byId('work-bubble').textContent.includes('커밋'),'Overtime speech');assert(near(parseFloat(getComputedStyle(byId('developer-animation')).animationDuration),.96*.65/OfficeSettings.current.animation.speed) && AnimationEngine.snapshot.typingRate===.65,'Overtime typing boost');change('cat-x',61);assert(OfficeSettings.current.stateLayouts.overtime.cat.x===61,'Overtime profile');byId('close-settings').click();assert(getComputedStyle(document.querySelector('.dark-circles')).display==='none','Circles reset');setOfficeState('overtime');assert(OfficeSettings.current.actualState==='overtime','Overtime state saved')")
                screenshot('overtime-state')
                cdp.js("""
                  byId('open-settings').click();byId('settings-tab-state').click();
                  const workingMessage=document.querySelector('[data-state-message=working]');
                  workingMessage.value='집중해서 작업하고 있어요!';workingMessage.dispatchEvent(new Event('input',{bubbles:true}));
                  const overtimeMessage=document.querySelector('[data-state-message=overtime]');
                  overtimeMessage.value='조금만 더 하고 퇴근할게요!';overtimeMessage.dispatchEvent(new Event('input',{bubbles:true}));
                  document.querySelector('[data-status=working]').click();
                  assert(byId('work-bubble').textContent==='집중해서 작업하고 있어요!' && byId('work-bubble').classList.contains('is-unanchored'),'Working state message');
                  change('speech-position-state','working');change('speech-position-x',72);change('speech-position-y',24);
                  assert(byId('work-bubble').style.left==='72%' && byId('work-bubble').style.top==='24%','Speech position live');
                  assert(OfficeSettings.current.speechPositions.working.x===72 && OfficeSettings.current.speechPositions.working.y===24,'Speech position stored');
                  document.querySelector('[data-status=overtime]').click();
                  assert(byId('work-bubble').textContent==='조금만 더 하고 퇴근할게요!','Overtime state message');
                  change('meeting-mode','away');change('meeting-away-message-input','회의실 다녀오는 중!');document.querySelector('[data-status=meeting]').click();
                  assert(visible('meeting-away-sign') && byId('meeting-away-message').textContent==='회의실 다녀오는 중!','Away meeting sign text');
                  assert(visible('work-bubble') && byId('work-bubble').classList.contains('is-unanchored'),'Away meeting state bubble');
                  assert(visible('laptop-closed') && byId('developer').hidden,'Away meeting objects');assert(near(parseFloat(byId('cat-layer').style.left),51) && near(OfficeSettings.getLayout('meeting').cat.scale,1.45),'Away meeting cat composition');
                  document.querySelector('[data-status=after_work]').click();assert(!visible('work-bubble'),'After work bubble hidden');
                  document.querySelector('[data-status=holiday]').click();assert(!visible('work-bubble'),'Holiday bubble hidden');
                  document.querySelector('[data-status=meeting]').click();assert(visible('work-bubble') && visible('meeting-away-sign'),'Away meeting restored');
                """)
                screenshot('meeting-away')
                cdp.js("assert(byId('meeting-mode').options.length===2 && ![...byId('meeting-mode').options].some(o=>o.value==='video'),'Removed standard video meeting');document.querySelector('[data-status=meeting]').click();change('executive-sign-title-input','대표님 전략 회의');change('executive-sign-message-input','잠시 집중 회의 중입니다');change('executive-sign-scale',1.4);change('meeting-mode','executive');assert(visible('executive-sign') && !visible('meeting-away-sign') && visible('video-meeting'),'Executive video meeting scene');assert(byId('video-meeting').classList.contains('is-executive') && byId('executive-sign-title').textContent==='대표님 전략 회의' && byId('executive-sign-message').textContent==='잠시 집중 회의 중입니다' && byId('executive-sign').style.getPropertyValue('--executive-scale')==='1.4' && byId('scene-status').textContent.includes('대표님'),'Executive meeting sign settings');assert(byId('developer').hidden && visible('laptop-closed'),'Executive meeting actors')")
                screenshot('executive-meeting')
                cdp.js("byId('end-preview').click();byId('close-settings').click()")
                cdp.js("""
                  byId('open-settings').click();byId('settings-tab-state').click();change('meeting-mode','executive');
                  document.querySelector('[data-status="meeting"]').click();
                  assert(OfficeState.current==='meeting' && visible('video-meeting'),'Executive meeting preview');
                  assert(byId('meeting-bubble').hidden && getComputedStyle(byId('developer')).visibility==='hidden' && getComputedStyle(byId('cat-layer')).visibility==='hidden','Executive meeting hides office actors');
                  assert(!document.querySelector('.meeting-info'),'Meeting info panel must be omitted');
                  const office=document.querySelector('.office-panel').getBoundingClientRect(), video=byId('video-meeting').getBoundingClientRect(), controls=document.querySelector('.video-controls').getBoundingClientRect();
                  assert(video.left>=office.left && video.right<=office.right && video.top>=office.top && video.bottom<=office.bottom,'Video meeting outside office panel');
                  assert(controls.top>=video.top && controls.bottom<=video.bottom && document.querySelector('.video-meeting-header').getBoundingClientRect().top>=video.top,'Video header or controls clipped');
                  const mic=document.querySelector('[data-video-control="microphone"]');mic.click();assert(mic.getAttribute('aria-pressed')==='true','Video control toggle');
                """)
                screenshot('executive-video-meeting')
                cdp.js("byId('close-settings').click();assert(OfficeState.current==='overtime' && OfficeSettings.current.meeting.mode==='executive','Meeting mode saved')")
                profile_expected=cdp.js('OfficeSettings.current')
                load()
                assert cdp.js('OfficeSettings.current.stateLayouts')==profile_expected['stateLayouts'],'State profiles reload'
                assert cdp.js('OfficeSettings.current.holidayCard')==profile_expected['holidayCard'],'Holiday settings reload'
                assert cdp.js("OfficeSettings.current.stateMessages.working==='집중해서 작업하고 있어요!' && OfficeSettings.current.stateMessages.overtime==='조금만 더 하고 퇴근할게요!'"),'State messages reload'
                assert cdp.js("OfficeSettings.current.speechPositions.working.x===72 && OfficeSettings.current.speechPositions.working.y===24"),'Speech positions reload'
                assert cdp.js("OfficeState.actual==='overtime' && OfficeState.current==='overtime' && getComputedStyle(document.querySelector('.dark-circles')).display==='block'"),'Overtime actual reload'
                assert cdp.js("OfficeSettings.current.meeting.mode==='executive' && OfficeSettings.current.meeting.executiveSign.title==='대표님 전략 회의' && OfficeSettings.current.meeting.executiveSign.scale===1.4"),'Meeting sign reload'
                cdp.js("""
                  (()=>{
                    setOfficeState('holiday');assert(byId('cat-layer').style.left==='72%' && visible('laptop-closed'),'Saved holiday actual scene');
                    byId('open-settings').click();byId('position-edit').click();
                    assert(officeEditing,'Profile drag edit');
                  })();
                """)
                before=cdp.js("OfficeSettings.getLayout('holiday').cat.x")
                drag_actor('cat-layer',-35,0,touch=True)
                assert cdp.js("OfficeSettings.getLayout('holiday').cat.x")<before,'Profile touch drag'
                cdp.js("""
                  (()=>{
                    assert(OfficeSettings.current.office.cat.x!==OfficeSettings.getLayout('holiday').cat.x,'Profile drag leaked');
                    byId('position-edit').click();byId('copy-common-layout').click();
                    assert(JSON.stringify(OfficeSettings.getLayout('holiday'))===JSON.stringify(OfficeSettings.current.office),'Copy common');
                    byId('inherit-common-layout').click();assert(!OfficeSettings.current.stateLayouts.holiday,'Inherit common');
                    const normalized=OfficeSettings.normalize({stateLayouts:{holiday:{cat:{x:'bad'}},fake:{}},holidayCard:{title:1,message:[],scale:99},meeting:{mode:'invalid'},environment:{lighting:'invalid',background:'day'}});
                    assert(!normalized.stateLayouts.fake && normalized.stateLayouts.holiday.cat.x===OfficeSettings.defaults.office.cat.x,'Invalid profile defaults');
                    assert(normalized.holidayCard.title==='CLOSED' && normalized.holidayCard.scale===1.5,'Invalid card defaults');
                    assert(normalized.meeting.mode==='away' && normalized.meeting.awayMessage==='회의실 다녀오는 중!' && normalized.meeting.executiveSign.title==='대표님 회의','Invalid meeting defaults');
                    assert(normalized.environment.lighting && normalized.environment.background==='night','Invalid environment defaults');
                    byId('close-settings').click();setOfficeState('working');
                    OfficeSettings.update(s=>{s.office=OfficeSettings.defaults.office;s.stateLayouts={};s.holidayCard=OfficeSettings.defaults.holidayCard});
                  })();
                """)
                # Failed writes remain usable and produce an explicit UI status.
                cdp.js("Storage.prototype.setItem=function(){throw new DOMException('quota','QuotaExceededError')};OfficeSettings.update(s=>{s.office.developer.x=55});assert(byId('settings-save-status').textContent.includes('저장하지'),'Storage failure feedback');assert(OfficeSettings.current.office.developer.x===55,'Failed storage live update')")
                load()
                cdp.js("byId('open-settings').click();change('placement-scope','common');byId('reset-positions').click()")
                screenshot('settings')
                cdp.js("byId('close-settings').click();assert(!document.querySelector('.header nav'),'Removed header navigation');const task=document.querySelector('.task-list input');task.click();assert(byId('task-progress').textContent==='1/3','Task interaction')")
                cdp.call('Emulation.setDeviceMetricsOverride',width=1920,height=1080,deviceScaleFactor=1,mobile=False)
                cdp.js("""
                  (()=>{
                    window.displayedWidgets=()=>[...document.querySelectorAll('#status-widget-slot>[data-widget-card],#bottom-widget-slot>[data-widget-card]')];
                    window.checkWidgetCount=()=>assert(displayedWidgets().length===WidgetSystem.visibleCount,'Actual card count mismatch');
                    window.widgetOffice=JSON.stringify(OfficeSettings.current.office);
                    window.widgetAnimation=JSON.stringify(OfficeSettings.current.animation);
                    window.officeBox=document.querySelector('.office-panel').getBoundingClientRect().toJSON();
                    window.characterBox=byId('developer').getBoundingClientRect().toJSON();
                    window.widgetTyping=byId('developer-animation').getAnimations()[0];
                    window.checkedTasks=[...document.querySelectorAll('.task-list input')].map(i=>i.checked).join();
                    assert(WidgetSystem.visibleCount===4,'Default count');checkWidgetCount();
                    for(const id of ['project_progress','github','automation','weekly_weather'])assert(WidgetSystem.setVisible(id,true),'Enable widget '+id);
                    assert(WidgetSystem.visibleCount===8,'Maximum 8');checkWidgetCount();
                    assert(WidgetSystem.setSmartMode('split')===false,'Split should exceed maximum');
                    assert(WidgetSystem.config.smartMode==='combined' && WidgetSystem.visibleCount===8,'Rejected split changed state');
                    assert(byId('widget-feedback').textContent.includes('10'),'Upper limit feedback');
                    assert(WidgetSystem.setVisible('unknown',true)===false,'Unknown widget accepted');
                    for(const item of [...WidgetSystem.config.items])if(!['smart_status','next_schedule'].includes(item.id))assert(WidgetSystem.setVisible(item.id,false),'Hide to minimum');
                    assert(WidgetSystem.visibleCount===2,'Minimum fixture');
                    assert(WidgetSystem.setVisible('next_schedule',false)===false,'Below minimum allowed');
                    assert(byId('widget-feedback').textContent.includes('최소'),'Minimum feedback');checkWidgetCount();
                    assert(WidgetSystem.setSmartMode('split'),'Split smart');
                    assert(WidgetSystem.visibleCount===4,'Split count');
                    assert(displayedWidgets().filter(n=>n.dataset.widgetCard.startsWith('smart_status.')).length===3,'Three separate smart cards');
                    assert(!displayedWidgets().some(n=>n.dataset.widgetCard==='smart_status'),'Duplicate integrated card');
                    assert(WidgetSystem.setVisible('next_schedule',false),'Smart split only');
                    assert(WidgetSystem.visibleCount===3,'Smart-only split counts three');
                    assert(WidgetSystem.setSmartMode('combined')===false,'Combine below minimum allowed');
                    assert(WidgetSystem.setVisible('smart_status',false)===false,'Empty dashboard allowed');
                    assert(WidgetSystem.setVisible('todo',true),'Add todo');assert(WidgetSystem.setSmartMode('combined'),'Combine smart');
                    assert(WidgetSystem.visibleCount===2,'Combined minimum');checkWidgetCount();
                    assert(document.querySelectorAll('#work-heading').length===1 && document.querySelectorAll('#weather-heading').length===1,'Duplicate IDs after smart modes');
                    assert([...document.querySelectorAll('.task-list input')].map(i=>i.checked).join()===checkedTasks,'Task inputs reset while reparenting');
                    WidgetSystem.setVisible('daily_schedule',true);
                    WidgetSystem.moveTo('todo',0);WidgetSystem.moveTo('daily_schedule',1);
                    assert([...byId('bottom-widget-slot').querySelectorAll(':scope>[data-widget-card]')].map(n=>n.dataset.widgetCard).join()==='todo,daily_schedule','Bottom card order');
                    const row=document.querySelector('[data-widget-row="daily_schedule"]');
                    row.querySelector('[data-widget-up]').click();assert(WidgetSystem.config.items[0].id==='daily_schedule','Up button');
                    row.querySelector('[data-widget-handle]').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));
                    assert(WidgetSystem.config.items[1].id==='daily_schedule','Keyboard sort');
                    const transfer=new DataTransfer(),handle=row.querySelector('[data-widget-handle]');
                    handle.dispatchEvent(new DragEvent('dragstart',{bubbles:true,dataTransfer:transfer}));
                    document.querySelector('[data-widget-row="todo"]').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));
                    handle.dispatchEvent(new DragEvent('dragend',{bubbles:true,dataTransfer:transfer}));
                    assert(WidgetSystem.config.items[0].id==='daily_schedule','Drag and drop sort');
                    const widths=[];
                    for(const size of ['small','medium','large']){assert(WidgetSystem.setSize('daily_schedule',size),'Size update');widths.push(byId('schedule').getBoundingClientRect().width);}
                    assert(widths[0]<widths[1] && widths[1]<widths[2],'Three distinct widget sizes');
                    assert(JSON.stringify(OfficeSettings.current.office)===widgetOffice && JSON.stringify(OfficeSettings.current.animation)===widgetAnimation,'Widget changes modified office settings');
                    const box=document.querySelector('.office-panel').getBoundingClientRect();
                    assert(near(box.width,officeBox.width)&&near(box.height,officeBox.height)&&near(box.x,officeBox.x)&&near(box.y,officeBox.y),'Widget changes resized office');
                    assert(byId('developer-animation').getAnimations()[0]===widgetTyping,'Widget render restarted office animation');
                    WidgetSystem.reset();assert(WidgetSystem.setVisible('time_timer',true),'Enable Time Timer');
                    assert(!byId('time-timer-widget').hidden && byId('time-timer-widget').dataset.widgetCard==='time_timer','Time Timer widget render');
                    change('time-timer-duration','300');byId('time-timer-toggle').click();assert(ProductivityTools.state.timer.running && byId('time-timer-display').textContent<='05:00','Time Timer start');byId('time-timer-toggle').click();assert(!ProductivityTools.state.timer.running,'Time Timer pause');byId('time-timer-reset').click();assert(byId('time-timer-display').textContent==='05:00','Time Timer reset');
                    WidgetSystem.setVisible('todo',false);WidgetSystem.focusWidget('todo');
                    assert(byId('office-settings').open && byId('widget-feedback').textContent.includes('숨겨져'),'Disabled widget navigation');
                    WidgetSystem.reset();byId('close-settings').click();
                  })();
                """)
                cdp.js("WidgetSystem.setVisible('time_timer',true)")
                screenshot('time-timer-widget')
                cdp.js("WidgetSystem.reset()")
                for count in range(2,9):
                    cdp.js(f"""
                      OfficeSettings.update(s=>{{s.widgets=WidgetConfig.defaults;s.widgets.items.forEach((item,index)=>{{item.visible=index<{count}}});}});
                      checkWidgetCount();assert(WidgetSystem.visibleCount==={count},'Widget count sweep');
                    """)
                    screenshot(f'widgets-{count}')
                    cdp.js("""
                      (()=>{
                        assert(document.documentElement.scrollHeight<=innerHeight,'Widgets expanded page');
                        for(const card of displayedWidgets()){
                          const rect=card.getBoundingClientRect();
                          assert(rect.width>0 && rect.height>0 && rect.top>=0 && rect.bottom<=innerHeight,'Widget outside desktop');
                        }
                        const rect=document.querySelector('.office-panel').getBoundingClientRect();
                        assert(near(rect.width,officeBox.width)&&near(rect.height,officeBox.height),'Office size changed with count');
                      })();
                    """)
                # Split mode at exactly eight visible physical cards.
                cdp.js("OfficeSettings.update(s=>{s.widgets=WidgetConfig.defaults;s.widgets.smartMode='split';s.widgets.items.forEach((item,index)=>{item.visible=index<6});});checkWidgetCount();assert(WidgetSystem.visibleCount===8,'Split eight cards')")
                screenshot('widgets-split-eight')
                widget_saved=cdp.js('OfficeSettings.current.widgets')
                load()
                assert cdp.js('OfficeSettings.current.widgets')==widget_saved,'Widget reload persistence'
                cdp.js("checkWidgetCount=()=>{if([...document.querySelectorAll('#status-widget-slot>[data-widget-card],#bottom-widget-slot>[data-widget-card]')].length!==WidgetSystem.visibleCount)throw Error('Card count')};checkWidgetCount();assert(WidgetSystem.visibleCount===8,'Saved split count')")
                # Normalization keeps office data, drops unknown and duplicate IDs, repairs bounds.
                cdp.js("""
                  (()=>{
                    const office=JSON.stringify(OfficeSettings.current.office);
                    OfficeSettings.update(s=>{s.widgets={smartMode:'nonsense',items:[{id:'unknown',visible:true},{id:'todo',visible:true,size:'bad',order:'bad'},{id:'todo',visible:true},{id:{x:1},visible:true}]}});
                    assert(WidgetSystem.visibleCount>=2&&WidgetSystem.visibleCount<=8,'Invalid config bounds');
                    assert(WidgetSystem.config.items.length===9&&new Set(WidgetSystem.config.items.map(i=>i.id)).size===9,'Unsafe widget IDs');
                    assert(JSON.stringify(OfficeSettings.current.office)===office,'Repair modified office');
                    OfficeSettings.update(s=>{s.widgets={smartMode:'split',items:WidgetConfig.defaults.items.map(item=>({...item,visible:true}))}});
                    assert(WidgetSystem.visibleCount===8,'Corrupt split over-limit repair');
                    WidgetSystem.reset();
                    OfficeSettings.update(s=>{s.widgets.items.find(i=>i.id==='todo').visible=false;});
                    WidgetSystem.focusWidget('todo');byId('close-settings').click();WidgetSystem.reset();
                    OfficeState.preview('meeting');assert(byId('work-heading').textContent===OfficeState.actualScene.label,'Widget actual work state');OfficeState.endPreview();
                  })();
                """)
                cdp.call('Emulation.setEmulatedMedia',features=[dict(name='prefers-reduced-motion',value='reduce')])
                cdp.js("WidgetSystem.setVisible('github',true);assert([...document.querySelectorAll('.widget-enter')].every(n=>getComputedStyle(n).animationName==='none'),'Reduced widget animation')")
                cdp.call('Emulation.setEmulatedMedia',features=[dict(name='prefers-reduced-motion',value='no-preference')])
                cdp.js("WidgetSystem.reset()")
                cdp.js("""
                  byId('open-settings').click();
                  window.beforeTabs=JSON.stringify(OfficeSettings.current);
                  for(const tab of document.querySelectorAll('[data-settings-tab]')) {
                    tab.click();
                    assert(tab.getAttribute('aria-selected')==='true','Selected tab');
                    assert(!byId(tab.getAttribute('aria-controls')).hidden,'Visible tab panel');
                    assert(document.querySelectorAll('#office-settings [role=tabpanel]:not([hidden])').length===1,'Single tab panel');
                  }
                  byId('settings-tab-office').click();byId('settings-tab-office').focus();
                  byId('settings-tab-office').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
                  assert(document.activeElement.id==='settings-tab-state','Tab arrow navigation');
                  document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'End',bubbles:true}));
                  assert(document.activeElement.id==='settings-tab-widgets','Tab End');
                  assert(JSON.stringify(OfficeSettings.current)===beforeTabs,'Tabs changed saved settings');
                  change('selected-actor','cat');assert(!document.querySelector('[data-actor-settings="cat"]').hidden && document.querySelector('[data-actor-settings="developer"]').hidden,'Selected actor controls');
                  change('selected-actor','deskMug');assert(!document.querySelector('[data-actor-settings="decor"]').hidden && byId('plant-control-target').value==='deskMug','Selected decor controls');
                  assert(document.querySelectorAll('.placement-steps li').length===3 && !document.querySelector('[data-actor-settings="decor"] .precision-controls').open,'Simple placement flow');
                  byId('settings-tab-office').click();
                """)
                screenshot('settings-tabs')
                cdp.js("byId('close-settings').click()")
                for width,height in ((1024,768),(390,844)):
                    cdp.call('Emulation.setDeviceMetricsOverride',width=width,height=height,deviceScaleFactor=1,mobile=False)
                    screenshot(f'widgets-responsive-{width}')
                    cdp.js("assert(document.documentElement.scrollWidth<=innerWidth,'Widget horizontal overflow')")
                    if width==390:
                        cdp.js("ReadingShelf.open();const dialog=byId('reading-shelf-dialog'),rect=dialog.getBoundingClientRect();assert(rect.left>=0&&rect.right<=innerWidth&&rect.top>=0&&rect.bottom<=innerHeight,'Reading dialog outside mobile viewport');assert(document.querySelector('.reading-shelf-scroll').scrollWidth>document.querySelector('.reading-shelf-scroll').clientWidth,'Reading shelf should scroll internally on mobile');dialog.close()")
                        cdp.js("window.scrollTo(0,240)")
                        cdp.js("new Promise(r=>requestAnimationFrame(r))")
                        cdp.js("assert(document.querySelector('.header').getBoundingClientRect().top>=0 && document.querySelector('.header').getBoundingClientRect().top<=12,'Mobile header not fixed');window.scrollTo(0,0)")
                cdp.call('Runtime.evaluate',expression='void 0')
                assert not cdp.errors,json.dumps(cdp.errors,ensure_ascii=False)
                print('PASS: compact header with legacy navigation removed and persisted manual work-state dropdown; integration/privacy settings persistence with session-only non-persisted secrets; automatic six-period time-of-day background and lighting grades, manual preview and persistence; editable and persisted per-state speech messages; hidden orange-character Virtual Office hotspot with visible portal removed; responsive 320/390/600/768/900/1024/1366/1920 layouts; dashboard/Virtual Office portal entry, 0.4s transition, back/brand return, offline status and preserved dashboard DOM/settings/work state; live bottom-center X/Y/scale; three core sprites, six independent plant layers and four independent desk prop layers; size-corrected four-frame cat walk, bounded roaming, arrival, disable and anchor reset; persisted lighting master, quick button and settings sync; overtime clock emphasis and 1.5x typing boost; away and executive-only meeting modes with editable persisted executive sign; local alarm and Time Timer widget; real mouse/touch drag and bounds; plant/desk-prop selection, visibility and storage; keyboard; reload persistence; legacy migration; malformed/invalid/quota handling; 36 preview/actual transitions; per-state placement isolation/copy/inheritance/reload/touch, persistent overtime state and dark circles, editable enlarged holiday notice; full-window shutters; fixed desk camera and edit resizing; silver/static mode, persistent Z-index, independent hands/blink/sleep, pixel-stable body, developer/cat frame movement and speed; reduced motion; independent engine states/cleanup/loops, unsupported-action fallbacks, action selection persistence, visibility suspension/resume; widget min/max 2-8, smart split/merge, buttons/keyboard/drag sorting, sizes, persistence/repair, office preservation and no console/resource errors.')
                print(f'Screenshots and browser log: {artifacts}')
                # Let Chrome stop its profile writers before deleting the temporary profile.
                try:
                    cdp.call('Browser.close')
                except (OSError, RuntimeError):
                    pass
                process.wait(timeout=10)
                cdp.stream.close()
                cdp.sock.close()
                process=None
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=10)
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
