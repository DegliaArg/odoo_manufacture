# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestMrpProductionGroupOnCreate(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.MrpProduction = cls.env["mrp.production"]
        cls.company = cls.env.company
        cls.env["ir.config_parameter"].sudo().set_param(
            "mrp_production_group_on_create.enabled", "True"
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "mrp_production_group_on_create.window_days", "1"
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "TEST Groupable product",
                "is_storable": True,
                "route_ids": [
                    (6, 0, [cls.env.ref("mrp.route_warehouse0_manufacture").id])
                ],
            }
        )
        cls.component = cls.env["product.product"].create(
            {"name": "TEST Component", "is_storable": True}
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product.product_tmpl_id.id,
                "product_id": cls.product.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.component.id, "product_qty": 2.0})
                ],
            }
        )
        cls.bom2 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product.product_tmpl_id.id,
                "product_id": cls.product.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.component.id, "product_qty": 3.0})
                ],
            }
        )

    def _make_vals(self, qty, date_start, bom=None):
        bom = bom or self.bom
        return {
            "product_id": self.product.id,
            "bom_id": bom.id,
            "product_qty": qty,
            "product_uom_id": self.product.uom_id.id,
            "date_start": date_start,
            "company_id": self.company.id,
        }

    def _search_orders(self, bom=None):
        domain = [("product_id", "=", self.product.id), ("state", "!=", "cancel")]
        if bom is not None:
            domain.append(("bom_id", "=", bom.id))
        return self.MrpProduction.search(domain)

    def test_group_same_product_bom_in_window(self):
        mo1 = self.MrpProduction.create(
            self._make_vals(5, "2026-12-01 08:00:00")
        )
        mo2 = self.MrpProduction.create(
            self._make_vals(3, "2026-12-02 08:00:00")
        )
        # Both create calls returned the very same (grouped) order.
        self.assertEqual(mo1, mo2)
        orders = self._search_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders.product_qty, 8)

    def test_no_group_out_of_window(self):
        self.MrpProduction.create(self._make_vals(5, "2026-12-01 08:00:00"))
        self.MrpProduction.create(self._make_vals(3, "2026-12-10 08:00:00"))
        self.assertEqual(len(self._search_orders()), 2)

    def test_no_group_different_bom(self):
        self.MrpProduction.create(self._make_vals(5, "2026-12-01 08:00:00"))
        self.MrpProduction.create(
            self._make_vals(3, "2026-12-01 08:00:00", bom=self.bom2)
        )
        self.assertEqual(len(self._search_orders()), 2)

    def test_no_group_when_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "mrp_production_group_on_create.enabled", "False"
        )
        self.MrpProduction.create(self._make_vals(5, "2026-12-01 08:00:00"))
        self.MrpProduction.create(self._make_vals(3, "2026-12-01 08:00:00"))
        self.assertEqual(len(self._search_orders()), 2)

    def test_no_group_with_skip_context(self):
        # Simulates procurement-driven creation (MTO/replenishment).
        self.MrpProduction.create(self._make_vals(5, "2026-12-01 08:00:00"))
        self.MrpProduction.with_context(group_on_create_skip=True).create(
            self._make_vals(3, "2026-12-01 08:00:00")
        )
        self.assertEqual(len(self._search_orders()), 2)

    def test_group_batch_create(self):
        # Several identical rows, as in a monthly import, collapse into one.
        orders = self.MrpProduction.create(
            [
                self._make_vals(5, "2026-12-01 08:00:00"),
                self._make_vals(3, "2026-12-01 10:00:00"),
                self._make_vals(2, "2026-12-02 09:00:00"),
            ]
        )
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders.product_qty, 10)
        self.assertEqual(len(self._search_orders()), 1)

    def test_no_group_without_date(self):
        # Without a scheduled start date no target can be evaluated.
        vals1 = self._make_vals(5, "2026-12-01 08:00:00")
        vals2 = self._make_vals(3, "2026-12-01 08:00:00")
        del vals2["date_start"]
        self.MrpProduction.create(vals1)
        self.MrpProduction.create(vals2)
        self.assertEqual(len(self._search_orders()), 2)

    def test_find_target_other_company_excluded(self):
        self.MrpProduction.create(self._make_vals(5, "2026-12-01 08:00:00"))
        vals = self._make_vals(3, "2026-12-01 08:00:00")
        vals["company_id"] = self.company.id + 1000  # non-matching company
        target = self.MrpProduction._group_on_create_find_target(vals)
        self.assertFalse(target)

    def test_components_scaled_on_group(self):
        self.MrpProduction.create(self._make_vals(5, "2026-12-01 08:00:00"))
        self.MrpProduction.create(self._make_vals(5, "2026-12-01 08:00:00"))
        order = self._search_orders()
        self.assertEqual(len(order), 1)
        self.assertEqual(order.product_qty, 10)
        move = order.move_raw_ids.filtered(
            lambda m: m.product_id == self.component
        )
        # Component consumption (2 per unit) must follow the grouped quantity.
        self.assertEqual(move.product_uom_qty, 20)
