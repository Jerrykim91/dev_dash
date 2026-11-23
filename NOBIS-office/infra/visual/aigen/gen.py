#!/usr/bin/env python3
"""설정 JSON(기본 v2/spec.json)의 각 에셋을 Codex 내장 image_gen(imagegen 스킬)으로 1장씩 생성해 raw/<id>.png로 저장한다.

사용: python3 gen.py [id ...] [--jobs 4] [--force] [--config v2/spec.json]
설정 파일 기준 상대 경로로 이미지·출력 폴더(rawDir, 기본 raw)를 해석한다.
"""
import argparse, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
_cfg_path = Path(sys.argv[sys.argv.index('--config') + 1]) if '--config' in sys.argv else HERE / 'v2' / 'spec.json'
_cfg_path = _cfg_path if _cfg_path.is_absolute() else (Path.cwd() / _cfg_path)
BASE = _cfg_path.resolve().parent
CFG = json.loads(_cfg_path.read_text())
RAW = BASE / CFG.get('rawDir', 'raw')


def build_prompt(a: dict) -> str:
    common = CFG['common'][a['type']].replace('{key}', a.get('key', '#00ff00'))
    lines = [common, f"Subject: {a['subject']}"]
    if a['type'] == 'prop' and not a.get('guide'):  # 가이드 모드에서는 방향을 블록아웃이 결정
        lines.append(CFG['orientation'][f"{a['fp'][0]}x{a['fp'][1]}"])
    if a.get('extra'):
        lines.append(a['extra'])
    lines.append(f"Canvas: {a.get('size', '1024x1024')}")
    return '\n'.join(lines)


def run(a: dict, force: bool) -> tuple[str, str, float]:
    out = RAW / f"{a['id']}.png"
    if out.exists() and not force:
        return a['id'], 'skip', 0.0
    spec = build_prompt(a)
    images = [str(BASE / CFG['styleRef'])] + [str(BASE / r) for r in a.get('refs', [])]
    if a.get('guide'):  # 기하 고정 모드: Image 1 = 블록아웃(편집 대상), Image 2 = 스타일 레퍼런스
        images = [str(BASE / a['guide'])] + images
        roles = ("Image 1 is the EDIT TARGET: a grey 3D blockout rendered in exact 2:1 dimetric projection. "
                 "Edit Image 1: repaint every block as the described object while keeping the camera angle, every edge direction, "
                 "the silhouette, proportions and position EXACTLY as in Image 1 (do not rotate, re-frame or add perspective). "
                 "Image 2 is a STYLE REFERENCE ONLY." + ((" " + a.get('refRole', "Image 3 is the CHARACTER IDENTITY reference (same hair, face, clothes, colors).")) if a.get('refs') else ""))
    else:
        roles = "The attached image (Image 1) is a STYLE REFERENCE ONLY." + ((" " + a['refRole']) if a.get('refs') and a.get('refRole') else "")
    if a.get('roles'):  # 자산별 역할 문구(파트 분리: 기본 몸 시트를 편집 대상으로 옷만 칠하기 등)
        roles = a['roles']
    missing = [i for i in images if not Path(i).exists()]
    if missing:  # 참고 이미지가 없으면 모델이 그냥 그려 버리거나 되묻는다 → 생성 전에 멈춘다
        return a['id'], f'FAILED (missing image: {missing[0]})', 0.0
    if out.exists():  # 다시 생성: 예전 파일을 남겨 두면 저장 실패를 성공으로 오판한다
        out.unlink()
    task = (
        "Use the imagegen skill in its default built-in image_gen mode (not the CLI).\n"
        f"Generate exactly ONE image from the spec below. {roles}\n"
        f"After generation, copy the generated PNG from $CODEX_HOME/generated_images/... to exactly: {out}\n"
        "Do not create or edit any other file. Reply only with the saved path.\n\n"
        f"--- SPEC ---\n{spec}\n"
    )
    t = time.time()
    log = RAW / f"{a['id']}.log"
    with log.open('w') as fh:
        subprocess.run(
            ['codex', '--no-daemon', '--dangerously-bypass-approvals-and-sandbox', 'exec',
             '--skip-git-repo-check', '-C', str(HERE), '-i', *images],
            input=task, text=True, stdout=fh, stderr=subprocess.STDOUT, timeout=900)
    if not out.exists():  # Codex가 다른 경로에 저장한 경우: 그 세션의 generated_images에서 회수
        import re, shutil
        m = re.search(r'session id: (\S+)', log.read_text(errors='ignore'))
        home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
        found = sorted((home / 'generated_images' / m.group(1)).glob('*.png'), key=lambda p: p.stat().st_mtime) if m else []
        if found:
            shutil.copy(found[-1], out)
            return a['id'], 'ok (recovered)', time.time() - t
    return a['id'], 'ok' if out.exists() else 'FAILED (see log)', time.time() - t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', nargs='*')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--print', action='store_true', help='프롬프트만 출력')
    ap.add_argument('--config', default=None, help='에셋 설정 JSON (기본 v2/spec.json, 옷 갈아입기 파트는 parts/spec.json)')
    args = ap.parse_args()
    assets = [a for a in CFG['assets'] if not args.ids or a['id'] in args.ids]
    if args.print:
        for a in assets:
            print(f"### {a['id']}\n{build_prompt(a)}\n")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(args.jobs) as ex:
        for aid, status, sec in ex.map(lambda a: run(a, args.force), assets):
            print(f"{aid:12s} {status:20s} {sec:6.0f}s", flush=True)


if __name__ == '__main__':
    sys.exit(main())
