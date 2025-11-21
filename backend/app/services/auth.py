from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.config import settings
from app.models.user import User
from app.services.cache import cache_service

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service with Redis caching for performance"""

    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire = timedelta(minutes=settings.access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=settings.refresh_token_expire_days)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')

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
            user_id_str = payload.get("sub")

            if user_id_str is None:
                return None

            # Convert string to int (sub is stored as string per JWT spec)
            user_id = int(user_id_str)

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
                    "username": user.username,  # Can be None
                    "full_name": user.full_name,
                    "kindle_email": user.kindle_email,  # Can be None
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
        password: str,
        full_name: Optional[str] = None,
        username: Optional[str] = None,
        is_admin: bool = False,
    ) -> User:
        """Create a new user with email verification token"""
        hashed_password = self.get_password_hash(password)

        # Generate username from email if not provided
        if not username:
            username = email.split('@')[0]

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            is_admin=is_admin,
            is_active=True,
            email_verified=False,
            verification_token=verification_token,
            verification_token_expires=token_expires,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    def generate_verification_token(self) -> tuple[str, datetime]:
        """Generate a new verification token and expiration"""
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        return token, expires

    async def verify_email(self, db: AsyncSession, token: str) -> Optional[User]:
        """Verify user email with token"""
        result = await db.execute(
            select(User).where(User.verification_token == token)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Check if token is expired
        if user.verification_token_expires and user.verification_token_expires < datetime.now(timezone.utc):
            return None

        # Mark email as verified
        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        await db.commit()
        await db.refresh(user)

        # Invalidate cache
        await self.invalidate_user_cache(user.id)

        return user

    async def resend_verification(self, db: AsyncSession, email: str) -> Optional[User]:
        """Generate new verification token for a user"""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if user.email_verified:
            return None  # Already verified

        # Generate new token
        token, expires = self.generate_verification_token()
        user.verification_token = token
        user.verification_token_expires = expires
        await db.commit()
        await db.refresh(user)

        return user

    async def invalidate_user_cache(self, user_id: int):
        """Invalidate user cache when user data changes"""
        await cache_service.delete(f"user:{user_id}")


# Singleton instance
auth_service = AuthService()
