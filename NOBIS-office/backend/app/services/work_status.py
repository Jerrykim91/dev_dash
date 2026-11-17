from typing import Protocol

class WorkStatusProvider(Protocol):
    def get_status(self, user_id: str) -> str: ...

class ManualWorkStatusProvider:
    def __init__(self, repository): self.repository = repository
    def get_status(self, user_id): return self.repository.status_for(user_id)
    def set_status(self, user_id, status, message): self.repository.update_status(user_id,status,message)

def participation_for(status: str) -> str:
    return 'spectator' if status == 'after_work' else 'normal'

class MockWorkStatusProvider(ManualWorkStatusProvider):
    """Explicit developer-controlled status provider; does not infer work activity."""
    source='mock'
    def set_test_status(self,user_id,status,message=''):
        self.set_status(user_id,status,message)
