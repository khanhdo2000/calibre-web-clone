from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.config import settings
from app.models.user import User
from app.services.cache import cache_service

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service with Redis caching for performance"""

    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire = timedelta(minutes=settings.access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=settings.refresh_token_expire_days)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def create_access_token(self, data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + self.access_token_expire
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + self.refresh_token_expire
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    async def get_current_user_from_token(
        self, token: str, db: AsyncSession
    ) -> Optional[User]:
        """
        Validate token and get user.
        Uses Redis cache to avoid DB hits for every request.
        """
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: int = payload.get("sub")

            if user_id is None:
                return None

            # Check cache first (if enabled)
            if settings.enable_auth_cache:
                cache_key = f"user:{user_id}"
                cached_user = await cache_service.get(cache_key)

                if cached_user:
                    logger.debug(f"User {user_id} loaded from cache")
                    # Reconstruct user object (simplified, in production use proper serialization)
                    return User(**cached_user)

            # Load from database
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user and settings.enable_auth_cache:
                # Cache user data
                user_dict = {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_admin": user.is_admin,
                }
                await cache_service.set(
                    f"user:{user_id}",
                    user_dict,
                    ttl=settings.auth_cache_ttl
                )
                logger.debug(f"User {user_id} cached")

            return user

        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting user from token: {e}")
            return None

    async def authenticate_user(
        self, db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """Authenticate user by email and password"""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    async def create_user(
        self,
        db: AsyncSession,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> User:
        """Create a new user"""
        hashed_password = self.get_password_hash(password)

        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            is_admin=is_admin,
            is_active=True,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    async def invalidate_user_cache(self, user_id: int):
        """Invalidate user cache when user data changes"""
        await cache_service.delete(f"user:{user_id}")


# Singleton instance
auth_service = AuthService()
