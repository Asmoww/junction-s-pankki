"""Names for categories, MCC sub-categories and the three baskets. Single source for data build, tools and UI."""

MCC_LABELS = {
    5411: "Supermarkets", 5499: "Kiosks & convenience stores", 5422: "Butchers & fish shops", 5451: "Bakeries & dairy shops",
    5812: "Restaurants", 5814: "Fast food & cafes", 5813: "Bars & pubs",
    4111: "Public transport", 5541: "Fuel", 5542: "Fuel (automated)", 7523: "Parking", 4121: "Taxis",
    7922: "Theatre & concerts", 7999: "Recreation & sports", 7832: "Cinema", 7991: "Attractions & museums",
    7996: "Amusement parks",
    5912: "Pharmacy", 8011: "Doctors", 8099: "Health services", 8021: "Dentists",
    5200: "Home supplies", 5732: "Electronics", 5251: "Hardware", 5712: "Furniture", 5734: "Software & apps",
    5941: "Sports gear", 5651: "Clothing", 5999: "Other shopping", 5691: "Fashion", 5942: "Books", 5945: "Toys & games",
    4722: "Travel agencies", 4511: "Flights", 7011: "Hotels", 7512: "Car rental",
}

# Sub-category for rows without a merchant code (all bills, and some purchases).
NO_MCC_SUB = {"Housing": "Rent & housing", "Utilities": "Utility bills"}

SPEND_CATEGORIES = ["Housing", "Utilities", "Groceries", "Transportation", "Health", "Home & Tech",
                    "Restaurants", "Entertainment", "Lifestyle", "Travel"]

BASKETS = {
    1: {"name": "Fixed must-pays", "short": "Must-pays",
        "explain": "Mandatory and regular: rent, utilities, groceries, commuting."},
    2: {"name": "Surprise must-pays", "short": "Surprises",
        "explain": "Mandatory but irregular: health, repairs, appliances, big one-off costs."},
    3: {"name": "Everyday extras", "short": "Extras",
        "explain": "Small choices that slip through your fingers: eating out, coffee, fun, shopping, taxis."},
}
