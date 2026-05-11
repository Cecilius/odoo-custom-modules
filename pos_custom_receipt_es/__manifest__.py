# pos_custom_receipt_es/__manifest__.py
{
    "name": "POS Custom Receipt ES",
    "version": "19.0.1.0.0",
    "summary": "Custom POS receipt layout (Spanish style) via QWeb extension",
    "author": "Reparero",
    "website": "https://reparero.es",
    "license": "LGPL-3",
    "category": "Point of Sale",
    "depends": ["point_of_sale"],
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_custom_receipt_es/static/src/xml/pos_custom_receipt.xml",
        ],
    },
    "installable": True,
    "application": False,
}