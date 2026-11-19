Once the feature is enabled, simply create manufacturing orders as usual.

When you create a manufacturing order that matches an existing non-planned
order (same product, same bill of materials, same company and a scheduled start
date within the configured window), its quantity is added to the existing order
and no second order is created. The components to consume are scaled
accordingly.

This is especially useful when manufacturing orders are loaded in batches (for
example, a monthly production plan imported from a spreadsheet): identical lines
are consolidated into a single order per product and bill of materials.

Grouping only happens when the new order has a scheduled start date. Orders
created by procurement (make-to-order, sale orders, multi-level or
subcontracting replenishment) and subcontracted orders are never grouped.
