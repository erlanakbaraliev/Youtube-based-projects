from typing import Annotated

from database import Base, engine, get_db
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import Post, User
from schemas import PostCreate, PostResponse, UserCreate, UserResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")


# ----- Home template -----


@app.get("/posts", include_in_schema=False)
@app.get("/", include_in_schema=False)
def home(request: Request, db: Annotated[Session, Depends(get_db)]):
    posts = db.execute(select(Post)).scalars().all()
    print(posts[0].author.username)
    return templates.TemplateResponse(request, "home.html", {"posts": posts})


# ----- Users api -----


@app.get(
    "/api/users/", response_model=list[UserResponse], status_code=status.HTTP_200_OK
)
def get_users(db: Annotated[Session, Depends(get_db)]):
    usernames = db.execute(select(User))
    return usernames.scalars().all()


@app.post("/api/users/", response_model=UserCreate, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    existing_user = db.execute(
        select(User).where(User.username == user.username)
    ).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username {user.username} already exists",
        )

    existing_email = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email {user.email} already exists.",
        )

    new_user = User(username=user.username, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.get(
    "/api/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK
)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    return user


@app.get(
    "/api/users/{user_id}/posts",
    response_model=list[PostResponse],
    status_code=status.HTTP_200_OK,
)
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    posts = db.execute(select(Post).where(Post.user_id == user_id)).scalars().all()

    return posts


# ----- User Posts templates -----


@app.get("/users/{user_id}/posts", include_in_schema=False)
def get_user_posts_page(
    request: Request, user_id: int, db: Annotated[Session, Depends(get_db)]
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    posts = db.execute(select(Post).where(Post.user_id == user_id)).scalars().all()

    return templates.TemplateResponse(
        request, "user_posts.html", {"posts": posts, "user": user}
    )


# ===== Posts api =====


@app.get("/api/posts/", response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):
    posts = db.execute(select(Post)).scalars().all()
    return posts


@app.post("/api/posts/", response_model=PostCreate, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):
    user = db.get(User, post.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_post = Post(title=post.title, content=post.content, user_id=post.user_id)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post


# ----- Posts templates -----


@app.get("/posts/{post_id}", include_in_schema=False)
def get_post_page(
    request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]
):
    post = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()

    if post:
        return templates.TemplateResponse(request, "post.html", {"post": post})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# ----- Exception handlers (StarletteHTTPException, RequestValidationError) -----


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occured. Please try again later."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code, content={"detail": message}
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
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )

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
