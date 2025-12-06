from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from app.database import get_db
from app.models.user import User
from app.services.auth import auth_service
from app.services.email import email_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: Optional[str] = None
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    email_verified: bool = False

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Convert None to False for email_verified before validation
        if hasattr(obj, 'email_verified') and obj.email_verified is None:
            obj.email_verified = False
        return super().model_validate(obj, **kwargs)


class RegisterResponse(BaseModel):
    message: str
    email: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# Dependency to get current user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    user = await auth_service.get_current_user_from_token(token, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user


# Routes
@router.post("/register", response_model=RegisterResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user and send verification email"""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user (username will be auto-generated from email)
    user = await auth_service.create_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
    )

    # Send verification email
    verification_url = f"{settings.frontend_url}/verify-email?token={user.verification_token}"

    email_body = f"""Chào mừng bạn đến với Kho Sách!
Welcome to Kho Sach!

---

Vui lòng xác minh địa chỉ email của bạn bằng cách nhấp vào liên kết dưới đây:
Please verify your email address by clicking the link below:

{verification_url}

Liên kết này sẽ hết hạn sau 24 giờ.
This link will expire in 24 hours.

Nếu bạn không tạo tài khoản, vui lòng bỏ qua email này.
If you did not create an account, please ignore this email.

Trân trọng,
Best regards,
Kho Sách Team
"""

    try:
        await email_service.send_email(
            to_email=user.email,
            subject="Xác minh email - Kho Sách / Verify your email",
            body=email_body
        )
        logger.info(f"Verification email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        # Don't fail registration if email fails - user can resend

    return RegisterResponse(
        message="Registration successful. Please check your email to verify your account.",
        email=user.email
    )


@router.post("/verify-email")
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify user email with token"""
    user = await auth_service.verify_email(db, data.token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    return {"message": "Email verified successfully", "email": user.email}


@router.post("/resend-verification")
async def resend_verification(
    data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resend verification email"""
    user = await auth_service.resend_verification(db, data.email)

    if not user:
        # Don't reveal if email exists or is already verified
        return {"message": "If the email exists and is not verified, a new verification email has been sent."}

    # Send verification email
    verification_url = f"{settings.frontend_url}/verify-email?token={user.verification_token}"

    email_body = f"""Chào mừng bạn đến với Kho Sách!
Welcome to Kho Sach!

---

Vui lòng xác minh địa chỉ email của bạn bằng cách nhấp vào liên kết dưới đây:
Please verify your email address by clicking the link below:

{verification_url}

Liên kết này sẽ hết hạn sau 24 giờ.
This link will expire in 24 hours.

Nếu bạn không tạo tài khoản, vui lòng bỏ qua email này.
If you did not create an account, please ignore this email.

Trân trọng,
Best regards,
Kho Sách Team
"""

    try:
        await email_service.send_email(
            to_email=user.email,
            subject="Xác minh email - Kho Sách / Verify your email",
            body=email_body
        )
        logger.info(f"Verification email resent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to resend verification email: {e}")

    return {"message": "If the email exists and is not verified, a new verification email has been sent."}


@router.get("/check-verification-status")
async def check_verification_status(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if an email is registered and verified (for UX purposes only)"""
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email doesn't exist
        return {
            "exists": False,
            "verified": False,
            "needs_verification": False
        }

    return {
        "exists": True,
        "verified": user.email_verified,
        "needs_verification": not user.email_verified
    }


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login and get access token - uses email as username"""
    # OAuth2PasswordRequestForm uses 'username' field, but we use it for email
    # First, get the user to check verification status before full authentication
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # If user doesn't exist, return generic error (don't reveal if email exists)
    if not user:
        logger.info(f"Login attempt for non-existent email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Login attempt for user: {user.email}, verified: {user.email_verified}, active: {user.is_active}")

    # Check password
    if not auth_service.verify_password(form_data.password, user.hashed_password):
        logger.info(f"Invalid password for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is active
    if not user.is_active:
        logger.info(f"Inactive account login attempt: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )

    # Check if email is verified (after password check to avoid revealing unverified accounts)
    if not user.email_verified:
        logger.info(f"Unverified email login attempt: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email for the verification link."
        )

    # Create tokens - sub must be a string per JWT spec
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"Successful login for user: {user.email}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    # Ensure email_verified is not None
    if current_user.email_verified is None:
        current_user.email_verified = False
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    user = await auth_service.get_current_user_from_token(refresh_token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Create new tokens - sub must be a string per JWT spec
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    new_refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset - sends reset email"""
    user = await auth_service.create_password_reset_token(db, data.email)

    # Don't reveal if email exists or not for security
    if user:
        # Send reset email
        reset_url = f"{settings.frontend_url}/reset-password?token={user.reset_token}"

        email_body = f"""Đặt lại mật khẩu / Password Reset
---

Bạn đã yêu cầu đặt lại mật khẩu cho tài khoản của mình.
You have requested to reset your password.

Vui lòng nhấp vào liên kết dưới đây để đặt lại mật khẩu:
Please click the link below to reset your password:

{reset_url}

Liên kết này sẽ hết hạn sau 1 giờ.
This link will expire in 1 hour.

Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.
If you did not request a password reset, please ignore this email.

Trân trọng,
Best regards,
Kho Sách Team
"""

        try:
            await email_service.send_email(
                to_email=user.email,
                subject="Đặt lại mật khẩu - Kho Sách / Password Reset",
                body=email_body
            )
            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")

    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using token"""
    user = await auth_service.reset_password(db, data.token, data.new_password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    return {"message": "Password reset successfully", "email": user.email}


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change password for authenticated user"""
    success = await auth_service.change_password(
        db, current_user, data.old_password, data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    return {"message": "Password changed successfully"}
