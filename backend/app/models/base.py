from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from app.core.config import settings
import uuid

# En PostgreSQL, los modelos multi-tenant (por esquema) usarán Base, y en tiempo de conexión, 
# se hará el schema_translate_map de None -> "tenant_x".
# Los modelos globales (compartidos) usarán GlobalBase apuntando al esquema "public".

is_sqlite = "sqlite" in settings.SQLALCHEMY_DATABASE_URI
global_schema = None if is_sqlite else "public"

class Base(DeclarativeBase):
    pass

class GlobalBase(DeclarativeBase):
    metadata = MetaData(schema=global_schema)
