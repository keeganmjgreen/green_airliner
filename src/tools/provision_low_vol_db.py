"""A script to provision the low-volume database from the ``START_STATE`` from an EvTaxisEmulator
config file (such as ``ev_taxis_emulator_config.py``), and clear any existing provisioning
information if already present.

This script may be used by VS Code launch configurations (in ``.vscode/launch.json``).

Designed to be run from a development machine.

WARNING: Not designed to play nice with data existing in low-volume database, e.g., if a matching
catalog entry already exists. Not designed to be run more than once, certainly not with the same
EV Taxis Emulator config.
"""

import argparse
import runpy
import typing

from src.projects import PROJECT_TYPE
from src.deployment_interfaces.db_connections import (
    DbConnection,
    LowVolDb,
    LowVolDbLocalAccess,
)
from src.deployment_interfaces.low_vol_db_provisioner import LowVolDbProvisioner


def main(
    configs_dir: str,
    ev_taxis_emulator_config_filename: str,
    project: PROJECT_TYPE,
    low_vol_db_class: DbConnection,
) -> None:
    # Initialize the EvTaxisEmulator:
    ev_taxis_emulator = runpy.run_path(configs_dir + ev_taxis_emulator_config_filename)[
        "ev_taxis_emulator"
    ]

    low_vol_db = low_vol_db_class()
    db_provisioner = LowVolDbProvisioner(PROJECT=project, LOW_VOL_DB=low_vol_db)
    # db_provisioner.clear_low_vol_db_provisioning()
    db_provisioner.provision_low_vol_db(
        state=ev_taxis_emulator.START_STATE, ev_specs=ev_taxis_emulator.EV_SPECS
    )


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs-dir", dest="configs_dir")
    parser.add_argument(
        "--ev-taxis-emulator-config-filename",
        dest="ev_taxis_emulator_config_filename",
        default=None,
    )
    parser.add_argument(
        "--project",
        choices=list(typing.get_args(PROJECT_TYPE)),
        dest="project",
        default=None,
    )
    parser.add_argument(
        "--low-vol-db-class",
        choices=list(LOW_VOL_DB_CLASSES.keys()),
        dest="low_vol_db_class",
        default=None,
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    LOW_VOL_DB_CLASSES = {
        "LowVolDb": LowVolDb,
        "LowVolDbLocalAccess": LowVolDbLocalAccess,
    }
    args = parse_cli_args()
    main(
        args.configs_dir,
        args.ev_taxis_emulator_config_filename,
        project=args.project,
        low_vol_db_class=LOW_VOL_DB_CLASSES[args.low_vol_db_class],
    )
