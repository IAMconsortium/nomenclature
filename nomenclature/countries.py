import os
import pycountry

# `nomenclature` uses pycountry to (optionally) add all countries and ISO3 codes
# For readability and in line with conventions of the IAMC community,
# several "standard" country names are shortened
# Please keep this list in sync with `templates/model-registration-template.xlsx`
PYCOUNTRY_NAME_OVERRIDE = {
    "Bolivia, Plurinational State of": "Bolivia",
    "Holy See (Vatican City State)": "Vatican",
    "Micronesia, Federated States of": "Micronesia",
    "Congo, The Democratic Republic of the": "Democratic Republic of the Congo",
    "Iran, Islamic Republic of": "Iran",
    "Korea, Republic of": "South Korea",
    "Korea, Democratic People's Republic of": "North Korea",
    "Lao People's Democratic Republic": "Laos",
    "Syrian Arab Republic": "Syria",
    "Moldova, Republic of": "Moldova",
    "Tanzania, United Republic of": "Tanzania",
    "Venezuela, Bolivarian Republic of": "Venezuela",
    "Palestine, State of": "Palestine",
    "Taiwan, Province of China": "Taiwan",
}
PYCOUNTRY_NAME_ADD = [
    dict(
        name="Kosovo",
        note="Kosovo recognized under UNSC resolution 1244, alpha_3 code not assigned"
    ),
]


class Countries(pycountry.ExistingCountries):
    """List of countries based on ISO 3166 database with simplications"""

    def __init__(self):

        super().__init__(os.path.join(pycountry.DATABASE_DIR, "iso3166-1.json"))

        # modify country names
        for iso_name, nc_name in PYCOUNTRY_NAME_OVERRIDE.items():
            obj = self.get(name=iso_name)
            obj.name = nc_name
            obj.iso_name = iso_name
            obj.note = "Name changed from ISO 3166 in line with community standards"
            self.indices["name"][nc_name.lower()] = obj

        # add countries that are not officially recognized
        # but relevant for IAM community
        for entry in PYCOUNTRY_NAME_ADD:
            obj = self.data_class(**entry)
            self.objects.append(obj)

            for key, value in entry.items():
                # Lookups and searches are case insensitive. Normalize here.
                value = value.lower()
                if key in self.no_index:
                    continue
                index = self.indices.setdefault(key, {})
                if value in index:
                    raise ValueError(f"Index conflict for country {key}: {value}")
                index[value] = obj


# Initialize `countries` for direct access via API and in codelist module
countries = Countries()
