# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "MRP Production Group On Create",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/manufacture",
    "license": "AGPL-3",
    "summary": "Group manually created manufacturing orders of the same "
    "product and bill of materials into a single order.",
    "depends": ["mrp"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
}
