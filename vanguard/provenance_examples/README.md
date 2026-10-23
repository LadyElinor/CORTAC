# Synthetic pinned-provenance example

All content, provenance references, controllers and review outputs in this folder
are fabricated software fixtures. The example pin is public and co-located with
the inventory for reproducibility. This is **not independent trust enrollment**,
authenticated source evidence, a genuine review or a held-out pilot.

From the repository root:

```sh
python scripts/vanguard_provenance.py vanguard/provenance_examples/packet.json \
  --inventory vanguard/provenance_examples/inventory.json \
  --inventory-sha256 a3c241c8cb104d766d4dc312565d6ce83ec340f4591e1cf0dcf1ca00259230aa \
  --as-of 2020-01-04 \
  --artifact-map vanguard/provenance_examples/artifact-map.json
```

Expected: exit 0, `PINNED_PROVENANCE_CONSISTENT`, scope `FROZEN_REVIEW_INPUT`,
`authority: NONE`, disabled execution and no authentication/factual judgment.
The historical date is the fixture's explicit evaluation date, not today's date.
Changing it to `2020-02-01` produces expiration holds and exit 3. Removing the
pin or artifact map also produces an incomplete report. Altering source/claim
text and regenerating the caller's bindings cannot match this frozen inventory.

`expected_inventory_digest.txt` holds the canonical-JSON inventory hash, not a
hash of the formatted file bytes. `artifact.txt` is checked as exact raw bytes.
In an operational use, the expected pin and evaluation date must come from the
separate operator channel, with independent provenance review. Do not compute
and accept a replacement pin merely because a comparison failed.

The source-only limitation and deliberate coordinated-fabrication controls are
in `package/wac_offline/vanguard_provenance_fixtures_v1.py`. Run
`python scripts/vanguard_provenance_controls.py` to inspect their fixed outcomes.
