from typing import Literal

# ==================================================================================================
# Objects used when querying assets (EVs, charge points) from low-volume database

REALISM_TYPE = Literal[
    "real-assets-only",
    "emulated-assets-only",
    "both-real-and-emulated-assets",
]
"""Whether to keep only real-world assets, emulated assets, or both when querying."""

IS_EMULATED_LOOKUP_BY_REALISM = {
    "real-assets-only": [False],
    "emulated-assets-only": [True],
    "both-real-and-emulated-assets": [False, True],
}
"""Which values of `is_emulated` column of `common.asset` table of low-volume database to filter by
depending on the realism (see ``REALISM_TYPE``).
"""

# ==================================================================================================
