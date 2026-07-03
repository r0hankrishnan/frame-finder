from fastapi.routing import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}