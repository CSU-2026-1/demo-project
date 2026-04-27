from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from dependency_injector.wiring import Provide, inject

from containers.container import Container
from schemas.auth import AuthenticatedUser, Token, UserCreate, UserRead
from security import get_current_user
from services.auth import AuthService, DuplicateUserError, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@inject
async def register(
    payload: UserCreate,
    service: AuthService = Depends(Provide[Container.auth_service]),
) -> UserRead:
    try:
        return await service.register(payload)
    except DuplicateUserError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        )


@router.post("/register-admin", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@inject
async def register_admin(
    payload: UserCreate,
    service: AuthService = Depends(Provide[Container.auth_service]),
) -> UserRead:
    try:
        return await service.register_admin(payload)
    except DuplicateUserError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        )


@router.post("/token", response_model=Token)
@inject
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(Provide[Container.auth_service]),
) -> Token:
    try:
        return await service.authenticate(form.username, form.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=AuthenticatedUser)
async def me(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    return current_user
