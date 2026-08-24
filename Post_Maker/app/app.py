from fastapi import FastAPI, HTTPException
from app.schemas import PostCreate
from app.db import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

# When app runs, immediately create database and schemas
app = FastAPI(lifespan=lifespan)

posts = {
    1: {"title": "First Steps", "content": "Just started learning FastAPI, loving it so far!"},
    2: {"title": "Coffee Time", "content": "Coffee first, code second."},
    3: {"title": "Bug Hunt", "content": "Debugging is like being a detective in a crime movie."},
    4: {"title": "Dependency Bliss", "content": "uv makes Python dependency management so much less painful."},
    5: {"title": "Clean Code", "content": "Anyone else obsessed with clean architecture lately?"},
    6: {"title": "Shipped It", "content": "Shipped a small feature today, feels good."},
    7: {"title": "Async Deep Dive", "content": "Reading about async/await internals in Python."},
    8: {"title": "Refactor Time", "content": "Refactoring old code is oddly satisfying."},
    9: {"title": "Pydantic v2", "content": "Trying out Pydantic v2 for the first time."},
    10: {"title": "Weekend Build", "content": "Weekend project: building a post maker app."},
}

@app.get("/posts/")
async def get_posts(limit: int | None = None):
    items = list(posts.values())[:limit] if limit else list(posts.values())
    return items

@app.get("/posts/{id}")
async def get_post(id: int):
    if id not in posts:
        raise HTTPException(404, f"Item with id {id} not found")
    return posts[id]

@app.post("/posts/")
async def create_post(post: PostCreate):
    new_post = {"title": post.title, "content": post.content}
    posts[max(posts.keys()) + 1] = new_post
    return new_post

