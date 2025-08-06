from backend.handlers.health import router as health_router
from backend.handlers.compress import router as compress_router

routers = [
    (health_router, "/api"),
    (compress_router, "/api"),
]
