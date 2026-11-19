# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

ENABLED_PARAM = "mrp_production_group_on_create.enabled"
WINDOW_PARAM = "mrp_production_group_on_create.window_days"

# States of a manufacturing order that has not been started yet and can still
# absorb extra quantity.
_GROUPABLE_STATES = ("draft", "confirmed")


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    @api.model
    def _group_on_create_enabled(self):
        """Return whether the group-on-create feature is active."""
        value = (
            self.env["ir.config_parameter"].sudo().get_param(ENABLED_PARAM) or ""
        )
        return value.strip().lower() in ("1", "true", "yes")

    @api.model
    def _group_on_create_window_days(self):
        """Return the ± day window used to look for a grouping target."""
        value = self.env["ir.config_parameter"].sudo().get_param(WINDOW_PARAM)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    # ------------------------------------------------------------------
    # Qualification helpers
    # ------------------------------------------------------------------
    def _group_on_create_is_subcontracting(self):
        """Subcontracted orders must never be grouped."""
        self.ensure_one()
        return self.bom_id.type == "subcontract"

    def _group_on_create_is_mto(self):
        """Orders tied to a sale order (make-to-order) are excluded.

        Internal manufacturing demand (a child order whose output feeds a
        parent's consumption) is *not* considered make-to-order and may be
        grouped: only a downstream move linked to a sale order, or a
        procurement group tied to a sale order, marks the order as MTO.
        """
        self.ensure_one()
        group = self.procurement_group_id
        if group and "sale_id" in group._fields and group.sale_id:
            return True
        for move in self.move_finished_ids.move_dest_ids:
            if "sale_line_id" in move._fields and move.sale_line_id:
                return True
            if (
                move.group_id
                and "sale_id" in move.group_id._fields
                and move.group_id.sale_id
            ):
                return True
        return False

    def _group_on_create_qualifies(self):
        """Return whether an existing order may act as a grouping target."""
        self.ensure_one()
        return (
            self.state in _GROUPABLE_STATES
            and not self.is_planned
            and self.product_id
            and self.bom_id
            and not self._group_on_create_is_subcontracting()
            and not self._group_on_create_is_mto()
        )

    @api.model
    def _group_on_create_vals_qualify(self, vals):
        """Lightweight qualification of the values of the order being created.

        At ``create`` time the moves are not computed yet, so only the values
        that are reliably present are checked here. Deeper checks are performed
        against the existing candidate in :meth:`_group_on_create_qualifies`.
        """
        if not vals.get("product_id") or not vals.get("bom_id"):
            return False
        if not vals.get("product_qty"):
            return False
        # A grouping target can only be found when a scheduled start date is
        # provided; otherwise we cannot evaluate the time window.
        if not vals.get("date_start"):
            return False
        bom = self.env["mrp.bom"].browse(vals["bom_id"])
        if bom.type == "subcontract":
            return False
        group_id = vals.get("procurement_group_id")
        if group_id:
            group = self.env["procurement.group"].browse(group_id)
            if "sale_id" in group._fields and group.sale_id:
                return False
        return True

    # ------------------------------------------------------------------
    # Target search
    # ------------------------------------------------------------------
    @api.model
    def _group_on_create_target_domain(self, vals):
        company_id = vals.get("company_id") or self.env.company.id
        date = fields.Datetime.to_datetime(vals["date_start"])
        days = self._group_on_create_window_days()
        date_start = date.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - relativedelta(days=days)
        date_end = date.replace(
            hour=23, minute=59, second=59, microsecond=0
        ) + relativedelta(days=days)
        return [
            ("product_id", "=", vals["product_id"]),
            ("bom_id", "=", vals["bom_id"]),
            ("company_id", "=", company_id),
            ("state", "in", list(_GROUPABLE_STATES)),
            ("is_planned", "=", False),
            ("date_start", ">=", fields.Datetime.to_string(date_start)),
            ("date_start", "<=", fields.Datetime.to_string(date_end)),
        ]

    @api.model
    def _group_on_create_find_target(self, vals):
        """Return an existing order the new values can be grouped into."""
        if not self._group_on_create_vals_qualify(vals):
            return self.browse()
        candidates = self.search(
            self._group_on_create_target_domain(vals), order="date_start, id"
        )
        for candidate in candidates:
            if candidate._group_on_create_qualifies():
                return candidate
        return self.browse()

    def _group_on_create_absorb(self, vals):
        """Add the new order quantity to this (existing) target order."""
        self.ensure_one()
        added_qty = vals.get("product_qty", 0.0)
        new_qty = self.product_qty + added_qty
        self.env["change.production.qty"].create(
            {"mo_id": self.id, "product_qty": new_qty}
        ).change_prod_qty()
        origin = vals.get("origin")
        if origin and origin not in (self.origin or ""):
            self.origin = (self.origin + "," + origin) if self.origin else origin
        # Leave a trace on the target order for auditability.
        self.message_post(
            body=_(
                "Grouped on creation: +%(added)s %(uom)s (origin: "
                "%(origin)s). New total: %(total)s %(uom)s.",
                added=added_qty,
                uom=self.product_uom_id.name,
                origin=origin or _("n/a"),
                total=new_qty,
            )
        )

    # ------------------------------------------------------------------
    # Override
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("group_on_create_skip") or not (
            self._group_on_create_enabled()
        ):
            return super().create(vals_list)
        records = self.browse()
        for vals in vals_list:
            target = self._group_on_create_find_target(vals)
            if target:
                target._group_on_create_absorb(vals)
                records |= target
            else:
                # Create one at a time so that orders created earlier in this
                # same batch become valid grouping targets for the next ones
                # (e.g. several identical rows of a monthly import).
                records |= super().create([vals])
        return records
