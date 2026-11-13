# Resale Products

Shared product identity and EU product-safety (GPSR) data for second-hand
products. One **resale product** can be linked to many product templates
(for example the same console sold in different conditions).

## Features

- *Resale Products* app with the `resale.product` model: name, category,
  brand, EAN / UPC / ASIN, reference retail price, launch year, manufacturer,
  EU responsible person, CE compliance and safety record (chatter-tracked).
- Identifiers are trimmed and upper-cased. EAN (8/13/14 digits) and UPC-A
  (12 digits) check digits are validated, ASIN must be 10 alphanumerics, and
  each identifier is unique when set.
- The *Price Updated* date is stamped whenever the reference price changes.
- *Create Product* builds a linked product template, copying the name in every
  installed language, the category, and (with `resale_attributes`) the brand
  and default warranty.

## Access

Internal users can create and edit resale products; only *Resale /
Administrator* can delete them (see `resale_base`).
