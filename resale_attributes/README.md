# Resale Attributes

Exposes the configurable **Brand**, **Condition**, **Box** and **Warranty**
product attributes as simple dropdowns on the product form, and maps each
condition to customer-facing texts.

## Configuration

*Settings > Resale*:

- Choose which product attribute plays each role (defaults are created by the
  module: Brand, Condition, Box, Warranty). Changing the Condition attribute
  archives the condition-text mappings of the previous attribute.
- Default warranty for new products.
- *Condition Texts*: one mapping per condition value with operator,
  listing and invoice wording (translatable). Editing mappings requires
  *Resale / Administrator*.

## Features

- `brand_value_id`, `condition_value_id`, `box_value_id` and
  `warranty_value_id` on product templates read and write the corresponding
  attribute line (no variants are created).
- The condition mapping is stored on the product and refreshed when attribute
  lines or mappings change.
- On resale products, the Brand dropdown only offers values of the configured
  Brand attribute.
