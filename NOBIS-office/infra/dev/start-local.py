"""Start missing local NOBIS services and leave existing servers alone."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def ready(url, backend=False):
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            body = response.read()
        if backend:
            data = json.loads(body)
            return data.get('status') == 'ok' and 'max_players' in data
        return b'nobis' in body.lower()
    except (OSError, ValueError, urllib.error.URLError):
        return False


def main():
    env = dict(os.environ)
    runtime = ROOT / '.tools/node/bin'
    if (runtime / 'node').is_file():
        env['PATH'] = str(runtime) + os.pathsep + env.get('PATH', '')
    npm = shutil.which('npm', path=env.get('PATH'))
    if not npm:
        raise RuntimeError('Node.js/npm 설치 경로를 확인하세요.')
    target = env.get('API_TARGET') or 'http://127.0.0.1:18000'
    env['API_TARGET'] = target
    port = int(env.get('NOBIS_FRONTEND_PORT', '15173'))
    frontend_url = f'http://127.0.0.1:{port}'
    children = []

    def start(command, cwd, address, backend=False):
        child = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True)
        children.append(child)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError('서버 실행이 종료됐습니다. 위의 오류를 확인하세요.')
            if ready(address, backend):
                return
            time.sleep(.2)
        raise RuntimeError('서버 시작 시간을 초과했습니다. 위의 오류를 확인하세요.')

    try:
        if not ready(target + '/health', True):
            if target.rstrip('/') not in ('http://127.0.0.1:18000', 'http://localhost:18000'):
                raise RuntimeError('설정된 API_TARGET 서버가 응답하지 않습니다: ' + target)
            env.update(APP_ENV='development', DEV_AUTH_ENABLED='true')
            env.setdefault('DATABASE_PATH', str(ROOT / 'backend/data/nobis.sqlite3'))
            start([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                   '--port', '18000'], ROOT / 'backend', target + '/health', True)
        else:
            print('기존 NOBIS 백엔드에 연결합니다.', flush=True)
        if not ready(frontend_url):
            start([npm, '--prefix', 'frontend', 'run', 'dev', '--', '--host', '127.0.0.1',
                   '--port', str(port), '--strictPort'], ROOT, frontend_url)
        else:
            print('기존 NOBIS 프런트엔드를 사용합니다.', flush=True)
        print(f'\nNOBIS Office: {frontend_url}\n이 창은 켜 두세요. 종료: Ctrl+C', flush=True)
        while children:
            if any(child.poll() is not None for child in children):
                raise RuntimeError('서버가 종료됐습니다. 위의 오류를 확인하세요.')
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
