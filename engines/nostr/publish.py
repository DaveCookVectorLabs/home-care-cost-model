#!/usr/bin/env python3
"""
Publish Home Care Cost Model content to Nostr public relays.
"""

import asyncio
import json
from pathlib import Path
from nostr_sdk import (
    Keys, Client, EventBuilder, Tag, Metadata,
    NostrSigner, RelayUrl,
)

RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.nostr.band",
    "wss://relay.snort.social",
    "wss://nostr.wine",
    "wss://relay.primal.net",
]

KEYS_FILE = Path(__file__).parent / "nostr_keys.json"


def get_keys():
    data = json.loads(KEYS_FILE.read_text())
    keys = Keys.parse(data["nsec"])
    print(f"Loaded keypair: {keys.public_key().to_bech32()}")
    return keys


LONG_FORM_CONTENT = """# The Home Care Cost Model: A Reference Framework for Aging in Place in Canada

Families across Canada routinely make high-stakes decisions about home care for older adults and people living with disability. Three distinct service categories — personal support (PSW, HCA, HSW), skilled nursing (LPN, RN), and housekeeping or cleaning services — are regulated, priced, and subsidised differently and cannot be freely substituted. The single most common misunderstanding is whether a housekeeper or cleaning service can substitute for a PSW. Legally, the answer is no whenever personal care tasks are required.

## The cost model

The reference implementation takes an assessment triple (Katz ADL score, Lawton IADL score, cognitive and mobility status), the recipient's jurisdiction, household composition, and primary diagnosis, and returns a recommended service mix, private-pay cost, allocated subsidised hours, and a full federal-plus-provincial tax relief stack indexed to the 2026 taxation year.

## Datasets

Eight open datasets are published under CC BY 4.0:

- `home_care_services_canada.csv` — scope of practice and rate bands across 13 Canadian jurisdictions
- `home_care_tax_parameters_2026.csv` — METC, DTC, CCC, VAC VIP parameters
- `home_care_subsidy_programs.csv` — provincial and territorial subsidised programs
- `home_care_scenarios.csv` — 5,000 synthetic household scenarios
- `home_care_per_province_rate_bands.csv` — CPI-adjusted 2019–2026 rate bands
- `home_care_cost_model_archetypes.csv` — canonical archetype lookup grid
- `home_care_tax_relief_sensitivity.csv` — tax credit sensitivity by income band
- `home_care_subsidy_gap.csv` — cross-province subsidy gap analysis

## Engines

Seven language implementations (Python, Rust, Java, Ruby, Elixir, PHP, Go) compute identical results to the cent.

## Findings

- Hybrid service mix (PSW for personal care + cleaning service for housekeeping) is typically 10–20% cheaper than an all-PSW plan.
- METC + DTC + CCC stacking reduces eligible households' out-of-pocket by 15–35% but is routinely under-claimed.
- Cross-province subsidy gap (model-recommended hours vs allocated hours) varies by a factor of three.

Reference model only. Not clinical or financial advice.

Working paper: https://www.binx.ca/guides/home-care-cost-model-guide.pdf
Zenodo DOI: 10.5281/zenodo.19491364
Repository: https://github.com/DaveCookVectorLabs/home-care-cost-model
"""

SHORT_NOTES = [
    (
        "Published an open reference cost model for Canadian home care "
        "service-mix decisions. Covers all 10 provinces + 3 territories "
        "with 2026 federal and provincial tax relief parameters. Seven "
        "language engines compute identical results to the cent. "
        "Reference model only; not clinical or financial advice.\n\n"
        "https://github.com/DaveCookVectorLabs/home-care-cost-model"
    ),
    (
        "Released 8 open datasets on Canadian home care: scope of "
        "practice, rate bands, subsidised programs, 5,000 synthetic "
        "scenarios, and cross-province subsidy gap analysis. CC BY 4.0.\n\n"
        "https://huggingface.co/datasets/davecook1985/home-care-cost-model"
    ),
    (
        "The three tax credits most families miss when paying for home "
        "care in Canada: Medical Expense Tax Credit, Disability Tax "
        "Credit, and Canada Caregiver Credit. Stacked, they reduce "
        "out-of-pocket by 15-35% for eligible households."
    ),
    (
        "Scope-of-practice gate in the Home Care Cost Model: if ADL ≤ 4 "
        "or cognition is moderate/severe, a housekeeper or cleaning "
        "service cannot legally substitute for a PSW/HCA. The hybrid "
        "mix (PSW for personal care + cleaning service for housekeeping) "
        "is what minimises cost within legal scope."
    ),
]


async def main():
    keys = get_keys()
    signer = NostrSigner.keys(keys)
    client = Client(signer)

    for relay in RELAYS:
        await client.add_relay(RelayUrl.parse(relay))
    await client.connect()
    await asyncio.sleep(3)

    # Long-form NIP-23 article
    hashtags = [
        Tag.hashtag("homecare"),
        Tag.hashtag("agingInPlace"),
        Tag.hashtag("canada"),
        Tag.hashtag("healthpolicy"),
        Tag.hashtag("opensource"),
    ]
    builder = EventBuilder.long_form_text_note(LONG_FORM_CONTENT).tags([
        Tag.identifier("home-care-cost-model-canada"),
        Tag.title("The Home Care Cost Model: A Reference Framework for Aging in Place in Canada"),
        *hashtags,
    ])
    output = await client.send_event_builder(builder)
    print(f"Long-form article published: {output.id.to_bech32()}")
    await asyncio.sleep(1)

    # Short notes (kind 1)
    short_tags = [
        Tag.hashtag("homecare"),
        Tag.hashtag("canada"),
        Tag.hashtag("healthpolicy"),
    ]
    for i, note in enumerate(SHORT_NOTES):
        builder = EventBuilder.text_note(note).tags(short_tags)
        output = await client.send_event_builder(builder)
        print(f"Note {i+1} published: {output.id.to_bech32()}")
        await asyncio.sleep(1)

    await asyncio.sleep(3)
    await client.disconnect()

    npub = keys.public_key().to_bech32()
    print(f"\nDone. View: https://njump.me/{npub}")


if __name__ == "__main__":
    asyncio.run(main())
