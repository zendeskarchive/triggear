from enum import Enum


class Routes(Enum):
    HEALTH = ('/health', 'health')
    GITHUB = ('/github', 'github')
    REGISTER = ('/register', 'register')
    STATUS = ('/status', 'status')
    COMMENT = ('/comment', 'comment')
    MISSING = ('/missing/{eventType}', 'missing')
    DEREGISTER = ('/deregister', 'deregister')
    CLEAR = ('/clear', 'clear')
    DEPLOYMENT = ('/deployment', 'deployment')
    DEPLOYMENT_STATUS = ('/deployment_status', 'deployment_status')

    def __init__(self, route: str, route_name: str) -> None:
        self.route: str = route
        self.route_id: str = route_name
