import { browser } from "@web/core/browser/browser";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";


patch(ListController.prototype, {
    async onRecordSaved(record) {
        await super.onRecordSaved(record);
        const model = record.model.root.resModel;
        if (model === "ai.openrouter.model" || model === "ai.google.model") {
            browser.location.reload();
        }
    },
});
