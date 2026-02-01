from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs

# Async declarative base for models
Base = declarative_base(cls=AsyncAttrs)
