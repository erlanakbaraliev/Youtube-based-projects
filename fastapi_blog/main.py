from contextlib import asynccontextmanager
from typing import Annotated

from database import Base, engine, get_db
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import Post, User
from routers import posts, users
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # when the application shuts down, dispose the engine (clean up its connections/resources)
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


@app.get("/posts", include_in_schema=False)
@app.get("/", include_in_schema=False)
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Post).options(selectinload(Post.author)))
    posts = result.scalars().all()

    return templates.TemplateResponse(request, "home.html", {"posts": posts})


# ----- Posts templates -----


@app.get("/posts/{post_id}", include_in_schema=False)
async def get_post_page(
    request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if post:
        return templates.TemplateResponse(request, "post.html", {"post": post})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# ----- User Posts templates -----


@app.get("/users/{user_id}/posts", include_in_schema=False)
async def get_user_posts_page(
    request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    result = await db.execute(
        select(Post).options(selectinload(Post.author)).where(Post.user_id == user_id)
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request, "user_posts.html", {"posts": posts, "user": user}
    )


# ----- Exception handlers (StarletteHTTPException, RequestValidationError) -----


@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request, exception: StarletteHTTPException
):
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (
        exception.detail
        if exception.detail
        else "An error occured. Please try again later."
    )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exception: RequestValidationError
):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
