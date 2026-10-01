import csv
from io import StringIO

from app.modules.leads.model import Lead


CSV_FIELDS = [
    "company_name",
    "website",
    "email",
    "phone",
    "address",
    "city",
    "state",
    "country",
    "industry",
    "google_maps_url",
    "place_id",
    "rating",
    "review_count",
    "lead_score",
    "verification_status",
    "verification_score",
    "status",
    "created_at",
]


def generate_csv(leads: list[Lead]) -> bytes:
    output = StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=CSV_FIELDS,
        extrasaction="ignore",
    )

    writer.writeheader()

    for lead in leads:
        writer.writerow(
            {
                field: getattr(lead, field)
                for field in CSV_FIELDS
            }
        )

    return output.getvalue().encode("utf-8")