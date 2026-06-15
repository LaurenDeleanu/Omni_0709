from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from app.core.config import settings
import uuid

# En PostgreSQL, los modelos multi-tenant (por esquema) usarán Base, y en tiempo de conexión, 
# se hará el schema_translate_map de None -> "tenant_x".
# Los modelos globales (compartidos) usarán GlobalBase apuntando al esquema "public".

is_sqlite = "sqlite" in settings.SQLALCHEMY_DATABASE_URI
global_schema = None if is_sqlite else "public"

from sqlalchemy import Column, String
from sqlalchemy.orm import declared_attr

class Base(DeclarativeBase):
    @declared_attr
    def tenant_id(cls):
        return Column(String(50), nullable=False, index=True)

class GlobalBase(DeclarativeBase):
    metadata = MetaData(schema=global_schema)
