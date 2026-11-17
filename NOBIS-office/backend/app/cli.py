"""Operator-only CLI, never exposed as an HTTP bootstrap endpoint."""
import argparse
import getpass
import json
import os
from pathlib import Path
import sqlite3
import time
from .repository import Repository
from .social import SocialService,SocialError,hash_password
from .home import HomeService
from .collectibles.service import CollectibleService,CollectibleError
from .community.service import CommunityService,CommunityError

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--database',default=os.getenv('DATABASE_URL') or os.getenv('DATABASE_PATH','data/nobis.sqlite3'))
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('migrate')
    sub.add_parser('list-users')
    clean=sub.add_parser('cleanup-media');clean.add_argument('--grace-hours',type=int,default=24)
    tickets=sub.add_parser('grant-tickets');tickets.add_argument('--actor-id',required=True);tickets.add_argument('--user-id',required=True);tickets.add_argument('--tickets',type=int,required=True);tickets.add_argument('--request-id',required=True)
    wallet=sub.add_parser('ticket-history');wallet.add_argument('--user-id',required=True)
    transfer=sub.add_parser('import-sqlite');transfer.add_argument('--source',required=True)
    boot=sub.add_parser('bootstrap-admin');boot.add_argument('--user-id',required=True)
    create=sub.add_parser('create-user');create.add_argument('--nickname',required=True);create.add_argument('--password-env')
    pwd=sub.add_parser('set-password');pwd.add_argument('--user-id',required=True);pwd.add_argument('--password-env')
    backup=sub.add_parser('backup');backup.add_argument('--output',required=True)
    restore=sub.add_parser('restore');restore.add_argument('--source',required=True);restore.add_argument('--replace',action='store_true')
    args=p.parse_args(argv);repo=Repository(args.database)
    if repo.kind=='postgresql' and args.command in ('backup','restore'):
        p.error('PostgreSQL 백업/복원은 pg_dump/pg_restore를 사용하세요. README의 postgres 서비스 명령을 확인하세요.')
    if args.command=='restore':
        source=Path(args.source).resolve();target=Path(args.database).resolve()
        if source==target or not source.is_file():p.error('복원 원본 경로를 확인하세요.')
        if target.exists() and not args.replace:p.error('기존 DB 복원은 서버를 종료하고 --replace를 지정하세요.')
        with sqlite3.connect(f'file:{source}?mode=ro',uri=True) as src:
            if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok':p.error('손상된 DB입니다.')
            if not src.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone():p.error('NOBIS DB가 아닙니다.')
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                with sqlite3.connect(target) as current,sqlite3.connect(str(target)+f'.pre-restore-{time.time_ns()}.bak') as prior:current.backup(prior)
            with sqlite3.connect(target) as dst:src.backup(dst)
        print(json.dumps({'restored':str(target)}));return
    repo.initialize(runtime_cleanup=False);svc=SocialService(repo);svc.initialize();home=HomeService(repo,0);home.initialize();collectibles=CollectibleService(repo,home,svc);collectibles.initialize()
    try:
        if args.command=='migrate':print(json.dumps({'schema_version':10,'database':repo.kind}))
        elif args.command=='cleanup-media':
            if args.grace_hours<1:p.error('최소 보관 유예는 1시간입니다.')
            print(json.dumps(CommunityService(repo,svc,None).cleanup_media(args.grace_hours)))
        elif args.command=='ticket-history':
            if not repo.user_exists(args.user_id):p.error('존재하는 사용자 ID가 필요합니다.')
            print(json.dumps({'state':collectibles.status(args.user_id),'history':collectibles.history(args.user_id)},ensure_ascii=False))
        elif args.command=='grant-tickets':
            import uuid
            uuid.UUID(args.request_id)
            if not 1<=args.tickets<=1000:p.error('무료 지급은 1~1000장입니다.')
            print(json.dumps(collectibles.grant(args.actor_id,args.user_id,args.tickets,args.request_id)))
        elif args.command=='import-sqlite':
            from .db_transfer import import_sqlite
            try:result=import_sqlite(repo,args.source)
            except ValueError as exc:p.exit(1,str(exc)+'\n')
            print(json.dumps(result))
        elif args.command=='list-users':
            with repo.connect() as c:rows=[dict(r) for r in c.execute('SELECT u.id AS user_id,u.nickname,u.disabled,u.account_origin,r.role FROM users u JOIN user_roles r ON r.user_id=u.id ORDER BY u.nickname,u.id')]
            print(json.dumps(rows,ensure_ascii=False))
        elif args.command=='bootstrap-admin':svc.bootstrap(args.user_id);print(json.dumps({'user_id':args.user_id,'role':'super_admin'}))
        elif args.command=='create-user':
            nickname=args.nickname.strip()
            if not nickname or len(nickname)>20:p.error('닉네임은 1~20자여야 합니다.')
            password=os.environ.get(args.password_env,'') if args.password_env else getpass.getpass('Password (12+ characters): ')
            if len(password)<12 or len(password)>200:p.error('비밀번호는 12~200자여야 합니다.')
            _,u=repo.create_user(nickname,origin='operator')
            with repo.connect() as c:
                c.execute('UPDATE users SET password_hash=? WHERE id=?',(hash_password(password),u['id']));svc.audit(c,None,'operator_user_created',u['id'])
            print(json.dumps({'user_id':u['id'],'nickname':u['nickname']},ensure_ascii=False))
        elif args.command=='set-password':
            if not repo.user_exists(args.user_id):p.error('기존 사용자 ID가 필요합니다.')
            password=os.environ.get(args.password_env,'') if args.password_env else getpass.getpass('New password (12+ characters): ')
            if len(password)<12 or len(password)>200:p.error('비밀번호는 12~200자여야 합니다.')
            with repo.connect() as c:
                c.execute('UPDATE users SET password_hash=? WHERE id=?',(hash_password(password),args.user_id))
                c.execute('DELETE FROM sessions WHERE user_id=?',(args.user_id,))
                svc.audit(c,None,'operator_password_changed',args.user_id)
            print(json.dumps({'user_id':args.user_id,'password_updated':True,'sessions_revoked':True}))
        elif args.command=='backup':
            output=Path(args.output)
            if output.exists():p.error('기존 백업을 덮어쓰지 않습니다.')
            output.parent.mkdir(parents=True,exist_ok=True)
            with repo.connect() as src,sqlite3.connect(output) as dst:src.backup(dst)
            print(json.dumps({'backup':str(output)}))
    except (SocialError,CollectibleError,CommunityError) as exc:p.exit(1,exc.message+'\n')
if __name__=='__main__':main()
