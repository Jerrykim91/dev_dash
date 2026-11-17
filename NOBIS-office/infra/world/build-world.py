"""Compatibility command: the active world now publishes independent room definitions."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('build-rooms.py')),run_name='__main__')
