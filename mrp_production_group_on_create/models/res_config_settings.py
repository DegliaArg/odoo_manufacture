# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # NOTE: field names must NOT start with "group_": res.config.settings
    # treats any such field as a permission-group setting and requires an
    # "implied_group" attribute, raising on the settings form otherwise.
    grouping_on_create_enabled = fields.Boolean(
        string="Group MOs on creation",
        help="When creating a manufacturing order manually, look for an "
        "existing non-planned order with the same product and bill of "
        "materials within the configured window and add the quantity to it "
        "instead of creating a second order.",
        config_parameter="mrp_production_group_on_create.enabled",
    )
    grouping_on_create_window_days = fields.Integer(
        string="Grouping window (± days)",
        help="Number of days, before and after the scheduled start date, "
        "within which an existing order is considered a grouping target. "
        "0 means the same day only.",
        config_parameter="mrp_production_group_on_create.window_days",
    )
