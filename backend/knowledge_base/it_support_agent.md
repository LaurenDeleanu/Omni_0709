# Knowledge Base: IT Support Agent (Soporte y Activos)

## 1. Gestión de Tickets de IT
- **Creación**: Los empleados pueden solicitar ayuda a través del IT Support Agent. El agente creará un ticket usando `create_it_ticket`.
- **Prioridades**:
  - `P1 (Crítico)`: Caída del sistema general, pérdida de acceso a servicios core (Email, VPN, ERP), robo de portátil. SLA: 1 hora.
  - `P2 (Alta)`: Problema que bloquea a un usuario sin un workaround viable (ej. monitor roto, teclado dañado). SLA: 4 horas.
  - `P3 (Normal)`: Peticiones de software, consultas generales. SLA: 24-48 horas.

## 2. Asignación de Hardware (Activos)
- **Onboarding**: A cada nuevo empleado de oficina se le asigna: 1 Portátil (MacBook Air o ThinkPad según rol), 1 Monitor 27", 1 Teclado y Ratón inalámbricos.
- **Renovación**: El hardware se renueva cada 3 años (36 meses) para portátiles y cada 5 años para monitores.
- **Pérdida/Robo**: Si un empleado pierde su dispositivo, debe abrir un ticket urgente (P1). El agente debe indicar que el departamento de IT procederá al bloqueo remoto del dispositivo vía MDM.

## 3. Acceso a Software y Licencias
- Todo el software adicional fuera del paquete base (Office 365 / Google Workspace) requiere aprobación del mánager si tiene coste (ej. licencias de diseño como Adobe CC, herramientas de desarrollo especializadas).
- **Onboarding/Offboarding**: El agente puede automatizar sugerencias de revocación o asignación de cuentas basándose en el departamento del usuario.

## 4. Troubleshooting Básico (Workarounds)
- **VPN no conecta**: Recomendar reiniciar el cliente de VPN y cambiar de WiFi. Si persiste, crear ticket.
- **Contraseña olvidada**: Redirigir al usuario al portal de Self-Service Password Reset (SSPR) en `/auth/reset`. No pedir contraseñas por chat bajo ninguna circunstancia.
