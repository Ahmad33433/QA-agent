# Planted bugs (ground truth)

The agent is not told about these. A run is scored by how many it reports.

1. Newsletter form accepts an invalid email ("abc" shows "Subscribed!").
2. "Add to cart" does nothing (cart count never changes).
3. The "Pricing" link leads to a missing page (404).
4. Quantity "-" goes to 0 and negative numbers.
5. The share button is an icon with no accessible name (no text or aria-label).

Controls that work and should NOT be reported: "+" quantity button, login (admin / secret),
the Home link.
