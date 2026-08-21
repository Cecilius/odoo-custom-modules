/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(FormController.prototype, {
    async beforeSave(record, options) {
        // Run standard base controller validations first
        const result = await super.beforeSave(...arguments);
        if (result === false) {
            return false;
        }

        // Only target product models
        if (!["product.template", "product.product"].includes(record.resModel)) {
            return result;
        }

        // Check if category field is dirty (changed by user)
        if (record.isDirty(["categ_id"])) {
            const categoryData = record.data.categ_id;

            // Fetch the category record details to check if it has a 2-digit code
            if (categoryData && categoryData[0]) {
                const categoryId = categoryData[0];
                const [category] = await this.model.orm.read(
                    "product.category",
                    [categoryId],
                    ["category_code", "name"]
                );

                if (category && category.category_code && category.category_code.length === 2) {
                    // Prompt user before committing save / navigating away
                    const confirmed = await new Promise((resolve) => {
                        this.dialogService.add(ConfirmationDialog, {
                            title: _t("Confirm Category Sequence Assignment"),
                            body: _t(
                                `Assigning category "${category.name}" will generate a new RFB sequence code (RFB-${category.category_code}-XXXXXX). Do you want to proceed?`
                            ),
                            confirmLabel: _t("Confirm & Generate"),
                            cancelLabel: _t("Reject / Cancel"),
                            confirm: () => resolve(true),
                            cancel: () => resolve(false),
                            dismiss: () => resolve(false),
                        });
                    });

                    // If user rejects/closes modal, abort save and block pager navigation
                    if (!confirmed) {
                        return false;
                    }
                }
            }
        }

        return result;
    },
});
