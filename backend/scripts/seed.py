import asyncio
import uuid
import sys
import os
from datetime import date, datetime, timezone


# Agrega la carpeta 'backend' al path para poder importar 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.core.database import engine, AsyncSessionGlobal
from app.models.base import GlobalBase, Base
from app.models.tenant import Tenant
from app.models.user import User
from app.core.auth import hash_password
from app.models.it import ITAsset, ITTicket, SaaSLicense
from app.models.finance import ExpenseClaim, TimeLog
from app.models.training import Course, CourseEnrollment, FundaeValidation
from app.models.admin import AuditLog



async def seed_tenant_and_users():
    print("Iniciando DB seeding...")
    
    # 1. Crear tablas globales
    async with engine.begin() as conn:
        await conn.run_sync(GlobalBase.metadata.create_all)
        print("Tablas globales creadas/verificadas.")

    # 2. Crear Tenant acme_corp
    async with AsyncSessionGlobal() as db:
        res = await db.execute(select(Tenant).where(Tenant.schema_name == 'acme_corp'))
        tenant = res.scalar_one_or_none()
        
        if not tenant:
            tenant = Tenant(
                id='tenant_acme_1', 
                name='Acme Corp', 
                schema_name='acme_corp', 
                is_active=True, 
                primary_color='#0ea5e9'
            )
            db.add(tenant)
            await db.commit()
            print("Tenant 'acme_corp' creado.")
        else:
            print("Tenant 'acme_corp' ya existe.")

    # 3. Crear tablas del tenant y usuarios
    tenant_schema = "tenant_acme_corp"
    
    # En PostgreSQL hay que asegurarse que el esquema exista
    from app.core.config import settings
    from sqlalchemy import text
    if "sqlite" not in settings.SQLALCHEMY_DATABASE_URI:
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {tenant_schema}"))
    
    # Para SQLite (local) o PostgreSQL configurado
    tenant_engine = engine.execution_options(schema_translate_map={None: tenant_schema})
    
    async with tenant_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print(f"Tablas para tenant {tenant_schema} creadas/verificadas.")

    AsyncSessionTenant = async_sessionmaker(bind=tenant_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionTenant() as db:
        # 1. Administrador general
        res = await db.execute(select(User).where(User.email == 'admin@successcore.com'))
        admin = res.scalar_one_or_none()
        if not admin:
            admin = User(
                id=uuid.uuid4().hex,
                email='admin@successcore.com',
                full_name='Admin General',
                department='IT',
                role='hr_admin',
                is_active=True,
                hashed_password=hash_password('admin')
            )
            db.add(admin)
            print("Usuario 'admin@successcore.com' creado.")
            
        # 2. Administrador secundario (Lauren)
        res = await db.execute(select(User).where(User.email == 'lauren.deleanu@gmail.com'))
        lauren = res.scalar_one_or_none()
        if not lauren:
            lauren = User(
                id=uuid.uuid4().hex,
                email='lauren.deleanu@gmail.com',
                full_name='Lauren Deleanu',
                department='Dirección',
                role='hr_admin',
                is_active=True,
                hashed_password=hash_password('admin')
            )
            db.add(lauren)
            print("Usuario 'lauren.deleanu@gmail.com' creado.")
            
        await db.flush()  # Para asegurar que obtenemos los IDs generados

        # 3. Seed IT Assets
        res = await db.execute(select(ITAsset))
        if not res.scalars().first():
            asset_1 = ITAsset(
                id=uuid.uuid4().hex,
                name="MacBook Pro 16\"",
                serial_number="SN-ACME-MBP2026",
                category="laptop",
                status="assigned",
                assigned_to_id=lauren.id,
                purchase_date=date(2026, 1, 15),
                cost=2499.00
            )
            asset_2 = ITAsset(
                id=uuid.uuid4().hex,
                name="Dell UltraSharp 27\"",
                serial_number="SN-ACME-DEL27",
                category="monitor",
                status="available",
                purchase_date=date(2026, 2, 10),
                cost=399.00
            )
            db.add_all([asset_1, asset_2])
            print("Activos de IT de prueba creados.")

        # 4. Seed IT Tickets
        res = await db.execute(select(ITTicket))
        if not res.scalars().first():
            ticket_1 = ITTicket(
                id=uuid.uuid4().hex,
                title="Acceso a VPN denegado",
                description="No puedo conectarme al servidor de producción con mis credenciales de Auth0.",
                category="accounts",
                priority="high",
                status="open",
                requester_id=lauren.id,
                assignee_id=admin.id
            )
            ticket_2 = ITTicket(
                id=uuid.uuid4().hex,
                title="Monitor secundario adicional",
                description="Solicitud de segundo monitor de 27 pulgadas para el equipo de desarrollo.",
                category="hardware",
                priority="low",
                status="closed",
                requester_id=lauren.id,
                assignee_id=admin.id
            )
            db.add_all([ticket_1, ticket_2])
            print("Tickets de IT de prueba creados.")

        # 5. Seed SaaS Licenses
        res = await db.execute(select(SaaSLicense))
        if not res.scalars().first():
            lic_1 = SaaSLicense(
                id=uuid.uuid4().hex,
                software_name="Slack Business+",
                seat_cost=12.50,
                assigned_to_id=lauren.id,
                status="active",
                renewal_date=date(2026, 12, 31)
            )
            lic_2 = SaaSLicense(
                id=uuid.uuid4().hex,
                software_name="Google Workspace Enterprise",
                seat_cost=18.00,
                assigned_to_id=lauren.id,
                status="active",
                renewal_date=date(2026, 12, 31)
            )
            db.add_all([lic_1, lic_2])
            print("Licencias SaaS de prueba creadas.")

        # 6. Seed Expense Claims
        res = await db.execute(select(ExpenseClaim))
        if not res.scalars().first():
            claim_1 = ExpenseClaim(
                id=uuid.uuid4().hex,
                user_id=lauren.id,
                merchant="Restaurante El Retiro",
                date=date(2026, 5, 10),
                total_amount=75.50,
                tax_amount=7.55,
                status="approved",
                category="meals",
                receipt_url="https://example.com/receipts/meals1.jpg",
                approved_by_id=admin.id,
                comments="Almuerzo de negocios con clientes de Acme Corp."
            )
            claim_2 = ExpenseClaim(
                id=uuid.uuid4().hex,
                user_id=lauren.id,
                merchant="JetBrains s.r.o.",
                date=date(2026, 5, 20),
                total_amount=249.00,
                tax_amount=52.29,
                status="pending",
                category="software",
                receipt_url="https://example.com/receipts/jetbrains.pdf",
                comments="Suscripción anual para IDE WebStorm."
            )
            db.add_all([claim_1, claim_2])
            print("Notas de gastos de prueba creadas.")

        # 7. Seed Courses
        res = await db.execute(select(Course))
        course_1 = None
        if not res.scalars().first():
            course_1 = Course(
                id=uuid.uuid4().hex,
                title="Introducción a la Ciberseguridad",
                description="Curso básico sobre seguridad de la información, phishing y protección de datos.",
                is_scorm=True,
                scorm_version="1.2",
                min_duration_hours=4.0,
                is_fundae_eligible=True
            )
            course_2 = Course(
                id=uuid.uuid4().hex,
                title="Prevención de Riesgos Laborales (PRL)",
                description="Curso obligatorio sobre salud e higiene en el puesto de trabajo.",
                is_scorm=False,
                min_duration_hours=2.0,
                is_fundae_eligible=True
            )
            db.add_all([course_1, course_2])
            print("Cursos de prueba creados.")
        else:
            res = await db.execute(select(Course).where(Course.title == "Introducción a la Ciberseguridad"))
            course_1 = res.scalar_one_or_none()

        # 8. Seed Course Enrollments and FUNDAE Validations
        res = await db.execute(select(CourseEnrollment))
        if not res.scalars().first() and course_1:
            enroll = CourseEnrollment(
                id=uuid.uuid4().hex,
                user_id=lauren.id,
                course_id=course_1.id,
                status="completed",
                progress_percentage=100.00,
                score=8.50,
                time_spent_seconds=15000,  # ~4.1 horas (cumple > 4h)
                completed_at=datetime.now(timezone.utc)
            )
            db.add(enroll)
            await db.flush()

            val = FundaeValidation(
                id=uuid.uuid4().hex,
                enrollment_id=enroll.id,
                duration_valid=True,
                progress_valid=True,
                test_valid=True,
                survey_valid=True,
                overall_eligible=True
            )
            db.add(val)
            print("Matrículas y validaciones FUNDAE de prueba creadas.")

        # 9. Seed Audit Logs
        res_audit = await db.execute(select(AuditLog))
        if not res_audit.scalars().first():
            res_admin = await db.execute(select(User).where(User.email == 'admin@successcore.com'))
            admin_user = res_admin.scalar_one_or_none()
            admin_id = admin_user.id if admin_user else "admin_system"
            
            db.add_all([
                AuditLog(
                    id=uuid.uuid4().hex,
                    user_id=admin_id,
                    action="MODULE_TOGGLE",
                    details="Activado modulo de IT Management.",
                    ip_address="192.168.1.50"
                ),
                AuditLog(
                    id=uuid.uuid4().hex,
                    user_id=admin_id,
                    action="ROLE_CHANGED",
                    details="Cambiado rol de Lucas Martin a employee.",
                    ip_address="192.168.1.50"
                ),
                AuditLog(
                    id=uuid.uuid4().hex,
                    user_id=admin_id,
                    action="COURSE_ASSIGNED",
                    details="Asignado curso 'Introduccion a la Ciberseguridad' en lote a 3 participantes.",
                    ip_address="192.168.1.50"
                )
            ])
            print("Audit Logs mock creados.")

        await db.commit()
        print("Seeding completado.")



if __name__ == "__main__":
    asyncio.run(seed_tenant_and_users())
