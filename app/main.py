from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from . import models, database
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from sqlalchemy import create_engine, text
import random
from faker import Faker

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
    
    # Incrementar contador de posts do usuário usando update()
    db.execute(
        models.User.__table__.update()
        .where(models.User.id == post.user_id)
        .values(posts_count=models.User.posts_count + 1)
    )
    
    db.commit()
    db.refresh(db_post)
    return db_post

@app.post("/posts/{post_id}/like")
def like_post(post_id: int, db: Session = Depends(database.get_db)):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Usar update() em vez de atribuição direta
    db.execute(
        models.Post.__table__.update()
        .where(models.Post.id == post_id)
        .values(likes=models.Post.likes + 1)
    )
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

def chunk_list(lst, n):
    """Divide uma lista em n chunks aproximadamente iguais"""
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]

def generate_posts_batch(args):
    user_ids, fake, base_date = args
    all_posts = []
    for user_id in user_ids:
        posts = [{
            "content": fake.text(max_nb_chars=200),
            "user_id": user_id,
            "likes": 0,
            "created_at": base_date + timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
        } for _ in range(1000)]  # 1000 posts por usuário
        all_posts.extend(posts)
    return all_posts

@app.post("/generate-test-data")
def generate_test_data(db: Session = Depends(database.get_db)):
    NUM_USERS = 1000
    POSTS_PER_USER = 1000
    TOTAL_POSTS = NUM_USERS * POSTS_PER_USER
    BATCH_SIZE = 10000
    
    print(f"Iniciando geração de {TOTAL_POSTS} posts...")
    fake = Faker()
    
    # Otimizar SQLite para inserção em massa
    db.execute(text("PRAGMA journal_mode = MEMORY"))
    db.execute(text("PRAGMA synchronous = OFF"))
    db.execute(text("PRAGMA cache_size = 1000000"))
    db.execute(text("PRAGMA temp_store = MEMORY"))
    
    try:
        # 1. Criar usuários em batch
        print(f"Gerando {NUM_USERS} usuários...")
        users_data = [{
            "username": f"user_{i}_{fake.user_name()}",
            "email": f"user_{i}_{fake.email()}",
            "posts_count": POSTS_PER_USER
        } for i in range(NUM_USERS)]
        
        db.bulk_insert_mappings(models.User, users_data)
        db.commit()
        
        # 2. Gerar e inserir posts em batches
        base_date = datetime.now() - timedelta(days=365)
        total_posts = 0
        posts_batch = []
        
        # Obter todos os IDs de usuários de uma vez
        user_ids = [u.id for u in db.query(models.User.id).all()]
        
        # Gerar posts em lotes
        while total_posts < TOTAL_POSTS:
            # Calcular quantos posts ainda precisamos gerar
            remaining_posts = min(BATCH_SIZE, TOTAL_POSTS - total_posts)
            
            # Determinar para quais usuários vamos gerar posts neste lote
            current_user_id = user_ids[total_posts // POSTS_PER_USER]
            
            # Gerar posts para este lote
            batch = [{
                "content": fake.text(max_nb_chars=200),
                "user_id": current_user_id,
                "likes": 0,
                "created_at": base_date + timedelta(
                    days=random.randint(0, 365),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            } for _ in range(remaining_posts)]
            
            # Inserir o lote
            db.bulk_insert_mappings(models.Post, batch)
            db.commit()
            
            total_posts += len(batch)
            print(f"Progresso: {total_posts}/{TOTAL_POSTS} posts ({(total_posts/TOTAL_POSTS)*100:.1f}%)")
        
        # Restaurar configurações do SQLite
        db.execute(text("PRAGMA journal_mode = DELETE"))
        db.execute(text("PRAGMA synchronous = FULL"))
        
        print("Geração de dados concluída!")
        return {
            "message": f"Test data generated successfully: {NUM_USERS} users with {POSTS_PER_USER} posts each",
            "total_posts": total_posts
        }
    except Exception as e:
        db.rollback()
        # Restaurar configurações do SQLite mesmo em caso de erro
        db.execute(text("PRAGMA journal_mode = DELETE"))
        db.execute(text("PRAGMA synchronous = FULL"))
        raise HTTPException(status_code=500, detail=str(e)) 