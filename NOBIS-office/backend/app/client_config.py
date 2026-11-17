"""Public runtime configuration; secrets and remote URL probing never leave this boundary."""
import ipaddress
import os
from urllib.parse import urlsplit

def valid_dashboard_url(value,production=False):
    if not value:return True
    try:
        u=urlsplit(value);host=(u.hostname or '').lower().rstrip('.');port=u.port
        if u.scheme not in ('http','https') or not host or u.username or u.password:return False
        if production:
            if host=='localhost' or host.endswith('.localhost'):return False
            try:
                address=ipaddress.ip_address(host)
                if address.is_loopback or address.is_unspecified:return False
            except ValueError:pass
        return True
    except (TypeError,ValueError):return False

def client_config():
    environment=os.getenv('APP_ENV','development')
    url=(os.getenv('DEVNEST_URL') or (os.getenv('DEVNEST_DEV_URL','http://127.0.0.1:8001/') if environment=='development' else '')).strip()
    if not valid_dashboard_url(url,environment!='development'):raise RuntimeError('DEVNEST_URL must be a valid non-loopback http(s) URL in production')
    return {'environment':environment,'default_url':url,'allow_local':environment=='development'}
