"""Demo: run the Archon orchestrator loop end to end.

Shows the full ritual flow for a shadow-work intention:
  intention capture -> routing -> parallel divination -> aggregation
  -> synthesis -> safety review -> final response.

Usage:
    .venv/bin/python demo.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ccp.archon import Archon, new_user  # noqa: E402
from ccp.schemas import BirthData, Intention  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    user = new_user(
        display_name="Johnny",
        spiritual_language=True,
        birth_data_processing=True,
        trauma_adjacent=True,
        altered_state_content=True,
        birth_data=BirthData(date="1990-04-15", location="Denver, CO"),
    )

    intention = Intention(
        text="Why do I keep sabotaging good relationships when they start "
             "getting serious?",
        tags=["shadow_work", "relationship"],
        timeframe="present",
    )

    print("=" * 72)
    print("COSMIC CHAOS PORTAL — Archon demo run")
    print("=" * 72)
    print(f"\nIntention: {intention.text}")
    print(f"Tags: {', '.join(intention.tags)}")
    print(f"Consent: spiritual={user.consent.spiritual_language} "
          f"birth_data={user.consent.birth_data_processing} "
          f"trauma_adjacent={user.consent.trauma_adjacent} "
          f"altered_state={user.consent.altered_state_content}\n")

    response = Archon().run_sync(intention, user)

    print("-" * 72)
    print(f"Run {response.run_id} -> {response.state.value.upper()} "
          f"[{response.response_style} voice]")
    print("-" * 72)
    print(response.narrative)
    if response.notices:
        print("\n## Notices")
        for n in response.notices:
            print(f"- {n}")
    if response.crisis_resources:
        print("\n## Support resources")
        for r in response.crisis_resources:
            print(f"- {r}")
    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
