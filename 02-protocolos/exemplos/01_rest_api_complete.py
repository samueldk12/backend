"""
Exemplo: REST API Completa com FastAPI

Execute: uvicorn 01_rest_api_complete:app --reload
Acesse: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
from datetime import datetime
import uvicorn

app = FastAPI(
    title="User Management API",
    description="REST API completa seguindo best practices",
    version="1.0.0"
)

# ============================================
# MODELS (Pydantic)
# ============================================

class UserBase(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Age must be between 0 and 150')
        return v


class UserCreate(UserBase):
    password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: datetime


# ============================================
# DATABASE (In-Memory)
# ============================================

users_db = {}
user_id_counter = 1


# ============================================
# ROUTES
# ============================================

@app.get(
    "/",
    summary="Root endpoint",
    description="Health check and API info"
)
def root():
    """
    Root endpoint

    Returns basic API information
    """
    return {
        "message": "User Management API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get(
    "/health",
    summary="Health check",
    tags=["Health"]
)
def health_check():
    """
    Health check endpoint

    Verifies that the API is running
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    tags=["Users"],
    responses={
        201: {"description": "User created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        409: {"description": "User already exists"}
    }
)
def create_user(user: UserCreate):
    """
    Create a new user

    - **name**: User's full name
    - **email**: Valid email address (must be unique)
    - **password**: Password (min 8 characters)
    - **age**: Optional age (0-150)
    """
    global user_id_counter

    # Check if email already exists
    for existing_user in users_db.values():
        if existing_user['email'] == user.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {user.email} already exists"
            )

    # Create user
    now = datetime.now()
    new_user = {
        "id": user_id_counter,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "created_at": now,
        "updated_at": now
    }

    users_db[user_id_counter] = new_user
    user_id_counter += 1

    return new_user


@app.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users",
    tags=["Users"]
)
def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max users to return"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)")
):
    """
    List all users with pagination and filtering

    - **skip**: Number of users to skip (for pagination)
    - **limit**: Maximum number of users to return (1-100)
    - **name**: Optional filter by name (case-insensitive partial match)
    """
    users = list(users_db.values())

    # Filter by name if provided
    if name:
        users = [u for u in users if name.lower() in u['name'].lower()]

    # Pagination
    return users[skip:skip + limit]


@app.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    tags=["Users"],
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"}
    }
)
def get_user(user_id: int):
    """
    Get a specific user by ID

    - **user_id**: The ID of the user to retrieve
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    return users_db[user_id]


@app.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user (full replacement)",
    tags=["Users"]
)
def update_user_full(user_id: int, user: UserBase):
    """
    Update user (full replacement)

    Replaces ALL user fields. Use PATCH for partial updates.
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Full replacement (preserving id and created_at)
    users_db[user_id].update({
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "updated_at": datetime.now()
    })

    return users_db[user_id]


@app.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user (partial)",
    tags=["Users"]
)
def update_user_partial(user_id: int, user: UserUpdate):
    """
    Update user (partial update)

    Updates only the fields provided. Omitted fields remain unchanged.
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Partial update (only update provided fields)
    update_data = user.dict(exclude_unset=True)
    users_db[user_id].update(update_data)
    users_db[user_id]['updated_at'] = datetime.now()

    return users_db[user_id]


@app.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    tags=["Users"]
)
def delete_user(user_id: int):
    """
    Delete a user

    - **user_id**: The ID of the user to delete

    Returns 204 No Content on success
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    del users_db[user_id]
    # 204 No Content - no body returned


# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(ValueError)
def value_error_handler(request, exc):
    return {
        "error": "Validation Error",
        "detail": str(exc),
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# EXAMPLES (Seed Data)
# ============================================

@app.on_event("startup")
def seed_data():
    """Seed some example data"""
    global user_id_counter

    example_users = [
        {"name": "Alice Silva", "email": "alice@example.com", "age": 28},
        {"name": "Bob Santos", "email": "bob@example.com", "age": 35},
        {"name": "Carol Oliveira", "email": "carol@example.com", "age": 42},
    ]

    now = datetime.now()
    for user in example_users:
        users_db[user_id_counter] = {
            "id": user_id_counter,
            **user,
            "created_at": now,
            "updated_at": now
        }
        user_id_counter += 1

    print(f"✅ Seeded {len(example_users)} users")


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 REST API Complete Example")
    print("=" * 60)
    print()
    print("📖 Swagger Docs: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print()
    print("🔍 Try these endpoints:")
    print("  GET    http://localhost:8000/users")
    print("  GET    http://localhost:8000/users/1")
    print("  POST   http://localhost:8000/users")
    print("  PATCH  http://localhost:8000/users/1")
    print("  DELETE http://localhost:8000/users/1")
    print()
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)


"""
TESTING WITH CURL:

# List all users
curl http://localhost:8000/users

# Get user by ID
curl http://localhost:8000/users/1

# Create user
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"João","email":"joao@example.com","password":"senha123","age":30}'

# Update user (partial)
curl -X PATCH http://localhost:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"age":31}'

# Delete user
curl -X DELETE http://localhost:8000/users/1

# Filter by name
curl "http://localhost:8000/users?name=Alice"

# Pagination
curl "http://localhost:8000/users?skip=0&limit=2"
"""
