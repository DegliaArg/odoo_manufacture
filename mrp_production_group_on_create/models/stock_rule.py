# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _run_manufacture(self, procurements):
        # Procurement-driven manufacturing orders (make-to-order, sale orders,
        # multi-level/subcontracting replenishment...) must never be grouped by
        # this module, which only targets manual creation.
        return super(
            StockRule, self.with_context(group_on_create_skip=True)
        )._run_manufacture(procurements)
