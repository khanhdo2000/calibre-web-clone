"""Service for managing categories that group tags together"""
import logging
from typing import List, Optional
from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.category import Category, category_tags, CategoryCreate, CategoryUpdate, CategoryResponse, TagInfo
from app.services.calibre_db import CalibreDatabase
from app.services.calibre_db_models import Tags, Books
from app.services.cache import cache_service

logger = logging.getLogger(__name__)


class CategoryService:
    """Service for category CRUD operations"""

    def __init__(self, calibre_db: CalibreDatabase):
        self.calibre_db = calibre_db

    async def get_all_categories(self, db: AsyncSession, include_book_count: bool = True) -> List[CategoryResponse]:
        """Get all categories with their tags and optional book counts"""
        # Try to get from cache
        cache_key = cache_service.cache_key("categories:all", include_book_count=include_book_count)
        cached_result = await cache_service.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for categories list")
            return [CategoryResponse(**cat) for cat in cached_result]

        try:
            # Get all categories ordered by display_order, then name
            result = await db.execute(
                select(Category).order_by(Category.display_order, Category.name)
            )
            categories = result.scalars().all()

            category_responses = []

            for category in categories:
                # Get tag IDs for this category
                tag_result = await db.execute(
                    select(category_tags.c.tag_id)
                    .where(category_tags.c.category_id == category.id)
                )
                tag_ids = [row[0] for row in tag_result.all()]

                # Get tag details from Calibre DB
                tags = []
                book_count = 0

                if tag_ids:
                    calibre_session = self.calibre_db.Session()
                    try:
                        # Get tag information
                        calibre_tags = calibre_session.query(Tags).filter(Tags.id.in_(tag_ids)).all()
                        tags = [TagInfo(id=t.id, name=t.name) for t in calibre_tags]

                        # Get book count if requested
                        if include_book_count:
                            # Count distinct books that have ANY of these tags
                            book_count = calibre_session.query(func.count(func.distinct(Books.id)))\
                                .join(Books.tags)\
                                .filter(Tags.id.in_(tag_ids))\
                                .scalar() or 0
                    finally:
                        calibre_session.close()

                category_responses.append(
                    CategoryResponse(
                        id=category.id,
                        name=category.name,
                        description=category.description,
                        display_order=getattr(category, 'display_order', 0),
                        created_at=category.created_at,
                        updated_at=category.updated_at,
                        tags=tags,
                        book_count=book_count if include_book_count else None
                    )
                )

            # Store in cache (TTL: 10 minutes for category lists)
            cache_data = [cat.model_dump() for cat in category_responses]
            await cache_service.set(cache_key, cache_data, ttl=600)
            logger.debug(f"Stored categories list in cache")

            return category_responses

        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            raise

    async def get_category_by_id(self, db: AsyncSession, category_id: int, include_book_count: bool = True) -> Optional[CategoryResponse]:
        """Get a single category by ID"""
        # Try to get from cache
        cache_key = cache_service.cache_key("category:detail", id=category_id, include_book_count=include_book_count)
        cached_result = await cache_service.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for category {category_id}")
            return CategoryResponse(**cached_result)

        try:
            result = await db.execute(
                select(Category).where(Category.id == category_id)
            )
            category = result.scalar_one_or_none()

            if not category:
                return None

            # Get tag IDs for this category
            tag_result = await db.execute(
                select(category_tags.c.tag_id)
                .where(category_tags.c.category_id == category.id)
            )
            tag_ids = [row[0] for row in tag_result.all()]

            # Get tag details from Calibre DB
            tags = []
            book_count = 0

            if tag_ids:
                calibre_session = self.calibre_db.Session()
                try:
                    calibre_tags = calibre_session.query(Tags).filter(Tags.id.in_(tag_ids)).all()
                    tags = [TagInfo(id=t.id, name=t.name) for t in calibre_tags]

                    if include_book_count:
                        book_count = calibre_session.query(func.count(func.distinct(Books.id)))\
                            .join(Books.tags)\
                            .filter(Tags.id.in_(tag_ids))\
                            .scalar() or 0
                finally:
                    calibre_session.close()

            response = CategoryResponse(
                id=category.id,
                name=category.name,
                description=category.description,
                display_order=getattr(category, 'display_order', 0),
                created_at=category.created_at,
                updated_at=category.updated_at,
                tags=tags,
                book_count=book_count if include_book_count else None
            )

            # Store in cache (TTL: 15 minutes for category detail)
            await cache_service.set(cache_key, response.model_dump(), ttl=900)
            logger.debug(f"Stored category {category_id} in cache")

            return response

        except Exception as e:
            logger.error(f"Error getting category {category_id}: {e}")
            raise

    async def create_category(self, db: AsyncSession, category_data: CategoryCreate) -> CategoryResponse:
        """Create a new category with associated tags"""
        try:
            # Validate tag IDs exist in Calibre DB
            if category_data.tag_ids:
                calibre_session = self.calibre_db.Session()
                try:
                    existing_tags = calibre_session.query(Tags.id).filter(Tags.id.in_(category_data.tag_ids)).all()
                    existing_tag_ids = {t.id for t in existing_tags}
                    invalid_ids = set(category_data.tag_ids) - existing_tag_ids
                    if invalid_ids:
                        raise ValueError(f"Invalid tag IDs: {invalid_ids}")
                finally:
                    calibre_session.close()

            # Get max display_order for new category
            try:
                max_order_result = await db.execute(
                    select(func.max(Category.display_order))
                )
                max_order = max_order_result.scalar() or 0
            except Exception:
                # Column might not exist yet
                max_order = 0

            # Create category
            category_dict = {
                'name': category_data.name,
                'description': category_data.description,
            }

            # Only add display_order if column exists
            if hasattr(Category, 'display_order'):
                category_dict['display_order'] = category_data.display_order if category_data.display_order is not None else max_order + 10

            category = Category(**category_dict)
            db.add(category)
            await db.flush()  # Get the ID

            # Add tag associations
            if category_data.tag_ids:
                for tag_id in category_data.tag_ids:
                    await db.execute(
                        category_tags.insert().values(
                            category_id=category.id,
                            tag_id=tag_id
                        )
                    )

            await db.commit()
            await db.refresh(category)

            # Invalidate cache
            await self._invalidate_category_cache()

            return await self.get_category_by_id(db, category.id)

        except IntegrityError as e:
            await db.rollback()
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                raise ValueError(f"Category with name '{category_data.name}' already exists")
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating category: {e}")
            raise

    async def update_category(self, db: AsyncSession, category_id: int, category_data: CategoryUpdate) -> Optional[CategoryResponse]:
        """Update a category and its tag associations"""
        try:
            result = await db.execute(
                select(Category).where(Category.id == category_id)
            )
            category = result.scalar_one_or_none()

            if not category:
                return None

            # Update basic fields
            if category_data.name is not None:
                category.name = category_data.name
            if category_data.description is not None:
                category.description = category_data.description
            if category_data.display_order is not None and hasattr(category, 'display_order'):
                category.display_order = category_data.display_order

            # Update tag associations if provided
            if category_data.tag_ids is not None:
                # Validate tag IDs exist in Calibre DB
                if category_data.tag_ids:
                    calibre_session = self.calibre_db.Session()
                    try:
                        existing_tags = calibre_session.query(Tags.id).filter(Tags.id.in_(category_data.tag_ids)).all()
                        existing_tag_ids = {t.id for t in existing_tags}
                        invalid_ids = set(category_data.tag_ids) - existing_tag_ids
                        if invalid_ids:
                            raise ValueError(f"Invalid tag IDs: {invalid_ids}")
                    finally:
                        calibre_session.close()

                # Remove existing tag associations
                await db.execute(
                    delete(category_tags).where(category_tags.c.category_id == category_id)
                )

                # Add new tag associations
                for tag_id in category_data.tag_ids:
                    await db.execute(
                        category_tags.insert().values(
                            category_id=category_id,
                            tag_id=tag_id
                        )
                    )

            await db.commit()
            await db.refresh(category)

            # Invalidate cache
            await self._invalidate_category_cache(category_id)

            return await self.get_category_by_id(db, category_id)

        except IntegrityError as e:
            await db.rollback()
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                raise ValueError(f"Category with name '{category_data.name}' already exists")
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating category {category_id}: {e}")
            raise

    async def delete_category(self, db: AsyncSession, category_id: int) -> bool:
        """Delete a category and its tag associations"""
        try:
            result = await db.execute(
                select(Category).where(Category.id == category_id)
            )
            category = result.scalar_one_or_none()

            if not category:
                return False

            # Delete tag associations (should cascade due to FK, but being explicit)
            await db.execute(
                delete(category_tags).where(category_tags.c.category_id == category_id)
            )

            # Delete category
            await db.delete(category)
            await db.commit()

            # Invalidate cache
            await self._invalidate_category_cache(category_id)

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting category {category_id}: {e}")
            raise

    async def get_category_tag_ids(self, db: AsyncSession, category_id: int) -> List[int]:
        """Get list of tag IDs for a category"""
        try:
            result = await db.execute(
                select(category_tags.c.tag_id)
                .where(category_tags.c.category_id == category_id)
            )
            return [row[0] for row in result.all()]

        except Exception as e:
            logger.error(f"Error getting tag IDs for category {category_id}: {e}")
            raise

    async def reorder_categories(self, db: AsyncSession, category_orders: List[dict]) -> bool:
        """Batch update display_order for multiple categories"""
        try:
            for item in category_orders:
                category_id = item.id if hasattr(item, 'id') else item['id']
                display_order = item.display_order if hasattr(item, 'display_order') else item['display_order']

                result = await db.execute(
                    select(Category).where(Category.id == category_id)
                )
                category = result.scalar_one_or_none()

                if category:
                    category.display_order = display_order

            await db.commit()

            # Invalidate cache for all categories since order changed
            await self._invalidate_category_cache()

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error reordering categories: {e}")
            raise

    async def _invalidate_category_cache(self, category_id: Optional[int] = None):
        """Invalidate category cache"""
        try:
            # Always invalidate category list cache
            await cache_service.delete_pattern("categories:all*")

            # If specific category ID provided, invalidate its detail cache
            if category_id:
                await cache_service.delete_pattern(f"category:detail*id={category_id}*")

            logger.debug(f"Invalidated category cache" + (f" for ID {category_id}" if category_id else ""))
        except Exception as e:
            logger.error(f"Error invalidating category cache: {e}")
