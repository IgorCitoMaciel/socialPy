from celery import Celery
from faker import Faker
from datetime import datetime, timedelta
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from . import models
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

# Configurar Celery
celery_app = Celery('tasks', broker='pyamqp://guest@localhost//')

# Configurar SQLAlchemy
SQLALCHEMY_DATABASE_URL = "sqlite:///./social_network.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def chunk_list(lst, chunk_size):
    """Divide uma lista em chunks de tamanho específico"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

@celery_app.task(name="generate_user_chunk")
def generate_user_chunk(start_idx, count):
    """Gera um chunk de usuários"""
    fake = Faker()
    db = get_db()
    
    users_data = [{
        "username": f"user_{i}_{fake.user_name()}",
        "email": f"user_{i}_{fake.email()}",
        "posts_count": 1000
    } for i in range(start_idx, start_idx + count)]
    
    db.bulk_insert_mappings(models.User, users_data)
    db.commit()
    
    # Retornar IDs dos usuários criados
    return [u.id for u in db.query(models.User.id).filter(
        models.User.username.like(f"user_{start_idx}%")
    ).all()]

@celery_app.task(name="generate_posts_for_users")
def generate_posts_for_users(user_ids):
    """Gera posts para um grupo de usuários"""
    fake = Faker()
    db = get_db()
    base_date = datetime.now() - timedelta(days=365)
    
    # Usar ThreadPoolExecutor para paralelizar a geração de dados
    def generate_user_posts(user_id):
        return [{
            "content": fake.text(max_nb_chars=200),
            "user_id": user_id,
            "likes": 0,
            "created_at": base_date + timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
        } for _ in range(1000)]  # 1000 posts por usuário
    
    # Usar múltiplas threads para geração de dados
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        all_posts = []
        for posts in executor.map(generate_user_posts, user_ids):
            all_posts.extend(posts)
            
            # Inserir em batches para não sobrecarregar a memória
            if len(all_posts) >= 10000:
                db.bulk_insert_mappings(models.Post, all_posts)
                db.commit()
                all_posts = []
        
        # Inserir posts restantes
        if all_posts:
            db.bulk_insert_mappings(models.Post, all_posts)
            db.commit()
    
    return len(user_ids) * 1000  # Retorna número de posts criados 