from typing import Optional, List, TypeVar, Generic, Type
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.db.models import Base
from core.db.utils import get_db

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class DatabaseOperations(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic database operations class."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(
        self, 
        db: AsyncSession, 
        obj_in: CreateSchemaType,
        user_id: Optional[int] = None
    ) -> ModelType:
        """Create a new record."""
        try:
            obj_data = obj_in.model_dump()
            db_obj = self.model(**obj_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            
            # Log the creation
            if hasattr(self.model, '__tablename__'):
                await self._log_operation(
                    db=db,
                    action="create",
                    table_name=self.model.__tablename__,
                    record_id=db_obj.id,
                    user_id=user_id,
                    changes=str(obj_data)
                )
            
            return db_obj
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create record: {str(e)}"
            )

    async def get(
        self, 
        db: AsyncSession, 
        id: int
    ) -> Optional[ModelType]:
        """Get a record by ID."""
        try:
            query = select(self.model).where(self.model.id == id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve record: {str(e)}"
            )

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        try:
            query = select(self.model).offset(skip).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve records: {str(e)}"
            )

    async def update(
        self,
        db: AsyncSession,
        id: int,
        obj_in: UpdateSchemaType,
        user_id: Optional[int] = None
    ) -> Optional[ModelType]:
        """Update a record."""
        try:
            # Get current state for audit log
            db_obj = await self.get(db, id)
            if not db_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Record not found"
                )
            
            old_data = {
                key: getattr(db_obj, key) 
                for key in obj_in.model_dump().keys()
            }
            
            # Update the object
            update_data = obj_in.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_obj, field, value)
            
            await db.commit()
            await db.refresh(db_obj)
            
            # Log the update
            if hasattr(self.model, '__tablename__'):
                await self._log_operation(
                    db=db,
                    action="update",
                    table_name=self.model.__tablename__,
                    record_id=id,
                    user_id=user_id,
                    changes=f"Old: {old_data}, New: {update_data}"
                )
            
            return db_obj
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update record: {str(e)}"
            )

    async def delete(
        self, 
        db: AsyncSession, 
        id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """Delete a record."""
        try:
            # Get current state for audit log
            db_obj = await self.get(db, id)
            if not db_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Record not found"
                )
            
            await db.delete(db_obj)
            await db.commit()
            
            # Log the deletion
            if hasattr(self.model, '__tablename__'):
                await self._log_operation(
                    db=db,
                    action="delete",
                    table_name=self.model.__tablename__,
                    record_id=id,
                    user_id=user_id,
                    changes=None
                )
            
            return True
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete record: {str(e)}"
            )

    async def _log_operation(
        self,
        db: AsyncSession,
        action: str,
        table_name: str,
        record_id: int,
        user_id: Optional[int] = None,
        changes: Optional[str] = None
    ) -> None:
        """Log database operations to audit log."""
        from core.db.models import AuditLog
        
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                table_name=table_name,
                record_id=record_id,
                changes=changes,
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            await db.commit()
        except Exception as e:
            # Log the error but don't raise it to avoid disrupting the main operation
            print(f"Failed to create audit log: {str(e)}")
            await db.rollback() 