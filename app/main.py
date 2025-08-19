from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from . import models, database
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware

# Criar as tabelas
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Social Network API")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas Pydantic
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    posts: int = 0

class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True

class PostCreate(BaseModel):
    user_id: int
    content: str

class PostResponse(BaseModel):
    id: int
    user_id: int
    content: str
    likes: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserWithPosts(BaseModel):
    id: int
    username: str
    email: str
    posts_count: int
    posts: List[PostResponse]

    class Config:
        from_attributes = True

# Endpoints
@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(database.get_db)):
    db_user = models.User(username=user.username, email=user.email, posts_count=0)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    return db_user

@app.post("/posts/", response_model=PostResponse)
def create_post(post: PostCreate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == post.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_post = models.Post(content=post.content, user_id=post.user_id)
    db.add(db_post)
    
    # Incrementar contador de posts do usuário
    user.posts_count += 1
    
    db.commit()
    db.refresh(db_post)
    return db_post

@app.post("/posts/{post_id}/like")
def like_post(post_id: int, db: Session = Depends(database.get_db)):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.likes += 1
    db.commit()
    return {"message": "Post liked successfully"}

@app.get("/feed/", response_model=List[PostResponse])
def get_feed(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), 
             db: Session = Depends(database.get_db)):
    posts = db.query(models.Post)\
        .order_by(models.Post.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return posts

@app.get("/users/", response_model=List[UserWithPosts])
def list_users_with_posts(skip: int = Query(0, ge=0), 
                         limit: int = Query(10, ge=1, le=100),
                         posts_limit: int = Query(5, ge=1, le=20),
                         db: Session = Depends(database.get_db)):
    users = db.query(models.User)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    # Para cada usuário, limitar o número de posts retornados
    for user in users:
        user.posts = user.posts[:posts_limit]
    
    return users

# Endpoint para gerar dados de teste
@app.post("/generate-test-data")
def generate_test_data(db: Session = Depends(database.get_db)):
    from faker import Faker
    import random
    from datetime import timedelta
    
    fake = Faker()
    
    # Criar 1000 usuários
    users = []
    for i in range(1000):
        user = models.User(
            username=f"user_{i}_{fake.user_name()}",
            email=f"user_{i}_{fake.email()}",
            posts_count=1000
        )
        db.add(user)
        users.append(user)
    
    db.commit()
    
    # Criar 1000 posts para cada usuário
    base_date = datetime.now() - timedelta(days=365)
    for user in users:
        for j in range(1000):
            post = models.Post(
                content=fake.text(max_nb_chars=200),
                user_id=user.id,
                likes=random.randint(0, 1000),
                created_at=base_date + timedelta(
                    days=random.randint(0, 365),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            )
            db.add(post)
        
        # Commit a cada 1000 posts para evitar sobrecarga de memória
        db.commit()
    
    return {"message": "Test data generated successfully"} 