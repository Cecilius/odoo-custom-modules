# Product RFB Sequence by Category

Generates internal references of the form `RFB-<category code>-<number>`
(for example `RFB-07-00042`) from a per-category sequence.

## Configuration

Give each product category a unique two-digit **Category Code** (00-99) on
the category form. The sequence `product.category.seq.<code>` is created on
first use.

## Usage

- On a product whose category has a code, click **Generate RFB Code**. If
  the product already has a reference, a confirmation dialog asks before it is
  overwritten.
- Internal references are unique (case- and whitespace-insensitive) when set.
- After importing products or restoring data, administrators can select
  categories and run *Action > Align RFB Sequences (Dry Run / Apply)*. The
  sequences only ever move forward, past the highest existing reference
  (archived products included). The same alignment is available from an Odoo
  shell via `scripts/adjust_rfb_sequences.py`.
