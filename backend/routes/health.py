from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
