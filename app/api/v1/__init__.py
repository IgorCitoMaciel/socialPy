from fastapi import APIRouter
from .users import router as users_router

router = APIRouter()

# Incluindo as rotas de usuários
router.include_router(users_router, prefix="/users", tags=["users"]) 