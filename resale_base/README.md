# Resale Base

Shared foundation for the `resale_*` modules.

## Features

- Adds the **Resale** section to *Settings*; other resale modules add their
  options to the `resale_settings_block` block.
- Defines the **Resale** access privilege (category *Supply Chain*):

  - **User** (`resale_base.group_resale_user`): implied by every internal
    user. Create and edit resale products, product tests and advertisements.
  - **Administrator** (`resale_base.group_resale_manager`): implied by
    *Settings / Administration*. Configure platforms, condition texts and test
    outcomes, and delete resale products.

## Usage

Depend on `resale_base` and reference the groups above in access rules,
menus and views instead of `base.group_user` / `base.group_system`.
