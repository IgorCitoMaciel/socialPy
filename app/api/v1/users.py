from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()

# Modelo Pydantic para validação dos dados do usuário
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

# Lista simulada de usuários (em um projeto real, usaríamos banco de dados)
users = []

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """
    Cria um novo usuário
    """
    # Verificar se email já existe
    if any(u["email"] == user.email for u in users):
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Criar novo usuário (em um sistema real, a senha seria criptografada)
    new_user = {
        "id": len(users),
        "name": user.name,
        "email": user.email,
        "password": user.password  # Nunca armazene senhas em texto puro em produção!
    }
    users.append(new_user)
    
    # Retorna o usuário sem a senha
    return UserResponse(id=new_user["id"], name=new_user["name"], email=new_user["email"])

@router.get("/", response_model=list[UserResponse])
async def get_users():
    """
    Retorna lista de usuários
    """
    # Retorna todos os usuários, excluindo as senhas
    return [UserResponse(id=u["id"], name=u["name"], email=u["email"]) for u in users]

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """
    Retorna um usuário específico pelo ID
    """
    if user_id >= len(users):
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user = users[user_id]
    return UserResponse(id=user["id"], name=user["name"], email=user["email"]) 