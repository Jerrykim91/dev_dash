#!/usr/bin/env python3
"""Generate a fresh, private Compose environment; never overwrite an existing file."""
import argparse
import os
from pathlib import Path
import secrets
p=argparse.ArgumentParser();p.add_argument('--output',default='.env.production');p.add_argument('--development',action='store_true');p.add_argument('--devnest-url',default='');args=p.parse_args()
from urllib.parse import urlsplit
import ipaddress
url=urlsplit(args.devnest_url)
if args.devnest_url:
    try:
        host=url.hostname or '';port=url.port
        try:local=ipaddress.ip_address(host).is_loopback or ipaddress.ip_address(host).is_unspecified
        except ValueError:local=host.lower()=='localhost' or host.lower().endswith('.localhost')
        if any(c in args.devnest_url for c in '\r\n') or url.scheme not in ('http','https') or not host or url.username or url.password or (not args.development and local):raise ValueError()
    except ValueError:p.error('A valid external HTTP(S) DevNest URL is required in production')
text=f'''APP_ENV={'development' if args.development else 'production'}
DEV_AUTH_ENABLED={'true' if args.development else 'false'}
DEV_ADMIN_KEY=
CHANNEL_CAPACITY=15
POSTGRES_DB=nobis
POSTGRES_USER=postgres
POSTGRES_PASSWORD={secrets.token_hex(32)}
NOBIS_DB_USER=nobis
NOBIS_DB_PASSWORD={secrets.token_hex(32)}
DOCKER_PLATFORM=linux/arm64
HTTP_BIND=127.0.0.1
HTTP_PORT=8080
ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
DEV_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DEV_HTTP_PORT=5173
DEVNEST_URL={args.devnest_url}
DEVNEST_DEV_URL=http://127.0.0.1:8001/
'''
path=Path(args.output)
try:
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:stream.write(text)
except FileExistsError:p.error('File already exists; no configuration was overwritten')
print('Private environment created: '+str(path))
