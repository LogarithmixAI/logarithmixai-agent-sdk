from functools import wraps
from flask import g

def agent_block_route(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 🔒 mark this request as blocked for agent
        g.agent_blocked = True
        return func(*args, **kwargs)
    
    return wrapper
    