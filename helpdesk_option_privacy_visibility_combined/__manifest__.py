# © 2025 Crumges
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

{
    "name": "Helpdesk: Combined Internal & Portal Visibility",
    "summary": "Agrega una opción de privacidad 'combined' para que internos y portal colaboren en el mismo equipo.",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "author": "Crumges",
    "maintainers": ["crumges"],
    "website": "https://www.crumges.com",
    "category": "Services/Helpdesk",
    "depends": ["helpdesk"],
    "data": [],
    "assets": {},
    "application": False,
    "installable": True,
    "auto_install": False,
    "development_status": "Production/Stable",
    "images": [],
    "description": """
Extiende helpdesk.team con una nueva visibilidad 'combined' para permitir que usuarios internos
y de portal colaboren sobre los mismos tickets de un equipo.

- Valida uso con website_helpdesk_form.
- Ajusta reglas de acceso para reflejar la visibilidad combinada.
""",
}
