This module groups manually created manufacturing orders so that there is a
single order per product and bill of materials.

When a manufacturing order is created manually (from the user interface or
through an import), the module looks for an existing order that:

* has the same product and bill of materials,
* belongs to the same company,
* is not planned yet and is still in draft or confirmed state,
* has a scheduled start date within a configurable ± day window.

If such an order is found, the new quantity is added to it instead of creating
a second order. Otherwise, the order is created normally.

Manufacturing orders created by procurement (make-to-order, sale orders,
multi-level or subcontracting replenishment) as well as subcontracted orders
are never grouped.
