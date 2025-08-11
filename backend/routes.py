from backend.handlers.health import router as health_router
from backend.handlers.compress import router as compress_router
from backend.handlers.system import router as system_router

routers = [
    (health_router, "/api"),
    (compress_router, "/api"),
    (system_router, "/api"),
]
