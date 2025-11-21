"""API routes for category management"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
import logging

from app.database import get_db
from app.models.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryList
from app.services.category_service import CategoryService
from app.services.calibre_db import calibre_db
from app.routes.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/categories", tags=["categories"])
logger = logging.getLogger(__name__)

# Initialize category service
category_service = CategoryService(calibre_db)


# Pydantic model for reordering
class CategoryOrder(BaseModel):
    id: int
    display_order: int


class CategoryReorderRequest(BaseModel):
    categories: List[CategoryOrder]


@router.get("/", response_model=CategoryList)
async def get_categories(
    include_book_count: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories with their associated tags and book counts.

    - **include_book_count**: Whether to include the count of books in each category (default: true)
    """
    try:
        categories = await category_service.get_all_categories(db, include_book_count=include_book_count)
        return CategoryList(categories=categories, total=len(categories))
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    include_book_count: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific category by ID.

    - **category_id**: The category ID
    - **include_book_count**: Whether to include the count of books in the category (default: true)
    """
    try:
        category = await category_service.get_category_by_id(db, category_id, include_book_count=include_book_count)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new category. Requires authentication.

    - **name**: Category name (unique, required)
    - **description**: Category description (optional)
    - **tag_ids**: List of tag IDs to include in this category (optional)
    """
    try:
        # Only admin users can create categories
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only administrators can create categories")

        category = await category_service.create_category(db, category_data)
        return category
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing category. Requires authentication.

    - **category_id**: The category ID
    - **name**: New category name (optional)
    - **description**: New category description (optional)
    - **tag_ids**: New list of tag IDs (optional, replaces existing tags)
    """
    try:
        # Only admin users can update categories
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only administrators can update categories")

        category = await category_service.update_category(db, category_id, category_data)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a category. Requires authentication.

    - **category_id**: The category ID
    """
    try:
        # Only admin users can delete categories
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only administrators can delete categories")

        success = await category_service.delete_category(db, category_id)
        if not success:
            raise HTTPException(status_code=404, detail="Category not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{category_id}/tags", response_model=List[int])
async def get_category_tag_ids(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the list of tag IDs associated with a category.

    - **category_id**: The category ID
    """
    try:
        # Verify category exists
        category = await category_service.get_category_by_id(db, category_id, include_book_count=False)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        tag_ids = await category_service.get_category_tag_ids(db, category_id)
        return tag_ids
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tag IDs for category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reorder", status_code=200)
async def reorder_categories(
    reorder_data: CategoryReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Batch update the display order of categories. Requires admin authentication.

    - **categories**: List of category IDs with their new display_order values
    """
    try:
        # Only admin users can reorder categories
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only administrators can reorder categories")

        success = await category_service.reorder_categories(db, reorder_data.categories)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to reorder categories")

        return {"message": "Categories reordered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
