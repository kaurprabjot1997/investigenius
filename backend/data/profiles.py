"""Mock client-profile generator. Field categories are inspired by RBC's
UCP4.0 metadata (age/tenure/income bands, digital engagement, product
holdings, segmentation codes) — no real client data was used or accessed to
build this; every value produced here is fabricated by this generator from
random distributions.

Governance note: demographic/segmentation fields (age, generation,
new_to_canada_segment, residence_country, vulnerability_segment, etc.) are
stored and surfaced to investigators as context — real analysts do use this
kind of profile context — but are deliberately NOT read by
app/graph/clustering.py's automated risk_score. Automated scoring is driven
only by transactional/structural signals (structuring patterns, cycles,
degree centrality). Feeding demographic or segmentation codes into an
automated risk multiplier is exactly the kind of proxy-discrimination risk a
bank's fair-lending/model-risk review would flag, so the split is enforced
at the architecture level — clustering.py never imports this module — rather
than left as a reviewer's judgment call.
"""
from __future__ import annotations

import random

AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
GENERATION_BY_AGE = {
    "18-24": "Gen Z",
    "25-34": "Millennial",
    "35-44": "Millennial",
    "45-54": "Gen X",
    "55-64": "Boomer",
    "65+": "Boomer",
}
INCOME_BANDS = ["<$20K", "$20K-$40K", "$40K-$60K", "$60K-$80K", "$80K-$120K", "$120K+"]
CREDIT_BANDS = ["300-579", "580-669", "670-739", "740-799", "800-850"]
OCCUPATIONS = ["Salaried employee", "Self-employed", "Retired", "Student", "Contract worker", "Homemaker"]
PROFITABILITY_SEGMENTS = ["Low", "Medium", "High", "Premier"]
VULNERABILITY_SEGMENTS = ["None", "None", "None", "Monitor", "Elevated"]  # weighted toward None
WALLET_BAND_SEGMENTS = ["Primary bank", "Secondary bank", "Banking elsewhere"]
PRODUCT_SEGMENTS = ["Starter", "Core banking", "Multi-product", "Full relationship"]

_PROFILE_COLUMNS = (
    "account_id, age_range, generation, tenure_years, income_after_tax_range, "
    "credit_score_range, occupation, residence_country, non_resident_tax_flag, "
    "new_to_canada_segment, digital_enrolled, digital_active_ind, mobile_auth_ind, "
    "active_product_count, total_relationship_balance, profitability_segment, "
    "vulnerability_segment, wallet_band_segment, client_product_segment, staff_flag"
)
INSERT_SQL = f"INSERT INTO client_profiles ({_PROFILE_COLUMNS}) VALUES ({','.join('?' * 20)})"


def make_profile(account_id: str, account_type: str, *, tenure_bias: str | None = None) -> tuple:
    """tenure_bias: 'short' for newly-recruited-looking accounts (mule hubs),
    'long' for established-customer-looking accounts (benign noise), None for
    the ambient random range (structuring/round-tripping scheme accounts,
    where tenure isn't the interesting signal).
    """
    if account_type == "external":
        return None  # no UCP record for an account outside the bank

    if tenure_bias == "short":
        tenure_years = round(random.uniform(0.1, 1.5), 1)
    elif tenure_bias == "long":
        tenure_years = round(random.uniform(5, 25), 1)
    else:
        tenure_years = round(random.uniform(0.5, 15), 1)

    new_to_canada = 1 if (tenure_bias == "short" and random.random() < 0.4) else 0
    residence_country = "CA" if random.random() > 0.05 else random.choice(["US", "GB", "IN", "PH"])

    if account_type == "business":
        return (
            account_id, "", "", tenure_years, "", "",
            "Business", residence_country, 0, 0,
            1 if random.random() > 0.3 else 0, 1 if random.random() > 0.4 else 0, 1 if random.random() > 0.5 else 0,
            random.randint(2, 8), round(random.uniform(2000, 500000), 2),
            random.choice(PROFITABILITY_SEGMENTS), "None",
            random.choice(WALLET_BAND_SEGMENTS), random.choice(PRODUCT_SEGMENTS), 0,
        )

    age_range = random.choice(AGE_BANDS)
    digital_enrolled = 1 if (tenure_bias != "short" and random.random() > 0.25) else (1 if random.random() > 0.7 else 0)
    return (
        account_id,
        age_range,
        GENERATION_BY_AGE[age_range],
        tenure_years,
        random.choice(INCOME_BANDS),
        random.choice(CREDIT_BANDS),
        random.choice(OCCUPATIONS),
        residence_country,
        1 if residence_country != "CA" and random.random() > 0.5 else 0,
        new_to_canada,
        digital_enrolled,
        digital_enrolled and (1 if random.random() > 0.3 else 0),
        digital_enrolled and (1 if random.random() > 0.4 else 0),
        random.randint(1, 6),
        round(random.uniform(200, 150000), 2),
        random.choice(PROFITABILITY_SEGMENTS),
        random.choice(VULNERABILITY_SEGMENTS),
        random.choice(WALLET_BAND_SEGMENTS),
        random.choice(PRODUCT_SEGMENTS),
        0,
    )
