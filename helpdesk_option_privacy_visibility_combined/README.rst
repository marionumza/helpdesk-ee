===============================================
Helpdesk: Combined Internal & Portal Visibility
===============================================

|license lgpl-3| |maturity production| |odoo v18|

Este módulo agrega un nuevo valor de visibilidad ``combined`` en
``helpdesk.team`` para permitir que **usuarios internos** y **usuarios portal**
colaboren sobre los mismos tickets dentro de un equipo.

¿Por qué?
=========

En Odoo nativo, las opciones de visibilidad por equipo de Helpdesk son
generalmente:

- ``internal``: acceso para usuarios internos.
- ``invited_internal``: internos invitados/seguidores.
- ``portal``: internos + portal (limitado a seguidores), orientado a soporte con formulario web.

**Limitación nativa**: cuando un equipo necesita que *internos y clientes (portal)*
trabajen juntos pero manteniendo un control fino de seguidores, notificaciones y
reglas, la configuración puede resultar ambigua o insuficiente para ciertos
escenarios de colaboración. Este módulo introduce ``combined`` para
**hacer explícito** ese modo mixto y **ajustar reglas y ayudas de UI**
en consecuencia.

Características
===============

- Nuevo valor ``combined`` en ``helpdesk.team.privacy_visibility``.
- Reglas de acceso adaptadas para que:
  - **Usuarios internos** vean lo correspondiente a su organización/rol.
  - **Usuarios portal** accedan a los tickets donde son seguidores (como en ``portal``).
- Validación cuando el equipo utiliza ``website_helpdesk_form``: solo es válido
  usar ``portal`` o ``combined``.
- Mensajes de ayuda/advertencia en el equipo para orientar la configuración.
- Gestión de seguidores al cambiar la visibilidad (suscribir/desuscribir cuando corresponde).

Compatibilidad
==============

- Probado en **Odoo 17**; el código es **compatible con Odoo 18**.
- En Odoo 18 podrían existir diferencias de ``xml_id`` en algunas
  ``ir.rule`` de Helpdesk (especialmente en reportes/SLA). Si algún ``xml_id``
  cambia, habrá que actualizar la referencia; la lógica no requiere cambios.

Uso
===

1. Ir a **Helpdesk → Configuración → Equipos**.
2. Abrir el equipo objetivo y seleccionar **Visibilidad = Combined**.
3. (Opcional) Si usás **Formulario Web**, mantener ``portal`` o ``combined``.
4. Guardar. El módulo ajusta reglas y seguidores según sea necesario.

Configuración
=============

- No requiere parámetros adicionales.
- Asegurate de que los usuarios portal estén agregados como **seguidores** de
  tickets que deban ver.

Limitaciones conocidas
======================

- Si en Odoo 18 algún ``xml_id`` de regla cambia de nombre, habrá que
  actualizar la referencia en el código para evitar un ``ValueError`` al
  buscarla con ``env.ref``. La funcionalidad del módulo no cambia.

Hoja de ruta
============

- Automatizar una verificación de ``xml_id`` en post-instalación para Odoo 18.
- Documentar escenarios de visibilidad complejos (multiempresa, jerarquías).

Documentación técnica (resumen)
===============================

- Extiende ``helpdesk.team`` agregando un estado de visibilidad ``combined``.
- Añade restricciones cuando ``use_website_helpdesk_form`` está activo.
- Ajusta dominios de ``ir.rule`` para reflejar la visibilidad mixta.
- Apoya la colaboración controlada con clientes (portal) mediante seguidores.

Instalación
===========

Instalar como cualquier módulo estándar:

- Activar modo desarrollador si es necesario.
- Instalar dependencias: ``helpdesk``, ``website_helpdesk_form``.
- Cargar el módulo.

Reporte de bugs
===============

Si encuentras un problema, por favor abrí un issue con:

- Pasos para reproducir
- Resultado actual
- Resultado esperado
- Versión exacta de Odoo y del módulo
- Logs relevantes (si aplica)

Créditos
========

Autores
-------

* Crumges

Mantenedores
------------

* Crumges

|maintainer crumges|

Licencia
========

Este módulo está publicado bajo la licencia **LGPL-3**.

.. |license lgpl-3| image:: https://img.shields.io/badge/license-LGPL--3-blue.svg
   :target: https://www.gnu.org/licenses/lgpl-3.0.html
.. |maturity production| image:: https://img.shields.io/badge/maturity-Production%2FStable-brightgreen.svg
.. |odoo v18| image:: https://img.shields.io/badge/odoo-18.0-ae7ec3.svg
.. |maintainer crumges| image:: https://img.shields.io/badge/maintainer-crumges-000000.svg
