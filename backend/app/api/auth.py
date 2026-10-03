from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenOut, UserOut
from app.schemas.common import ApiResponse, ErrorResponse, ERROR_RESPONSES, ok
from app.services import audit_service, user_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=ApiResponse[UserOut],
    status_code=201,
    summary="Register an investor account",
    description="Creates a user. Passwords are bcrypt-hashed. `full_name` is accepted as an alias of `name`.",
    responses={409: {"model": ErrorResponse, "description": "EMAIL_ALREADY_REGISTERED"}, 422: ERROR_RESPONSES[422]},
)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = user_service.create_user(db, body)
    audit_service.log_action(db, user_id=user.id, action="USER_REGISTERED", resource_type="user", resource_id=user.id)
    return ok(UserOut.model_validate(user), "Account created")


@router.post(
    "/login",
    response_model=ApiResponse[TokenOut],
    summary="Log in",
    description="Returns a JWT bearer token. Send it as `Authorization: Bearer <token>`.",
    responses={401: {"model": ErrorResponse, "description": "INVALID_CREDENTIALS"}, 422: ERROR_RESPONSES[422]},
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = user_service.authenticate(db, body.email, body.password)
    token, expires_in = create_access_token(user.id)
    audit_service.log_action(db, user_id=user.id, action="USER_LOGIN", resource_type="user", resource_id=user.id)
    return ok(TokenOut(access_token=token, expires_in=expires_in), "Login successful")


@router.get(
    "/me",
    response_model=ApiResponse[UserOut],
    summary="Current user",
    description="Returns the authenticated user's profile.",
    responses={401: ERROR_RESPONSES[401]},
)
def me(user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(user))
