"""A universal entrypoint script, which may be used by different VS Code launch configurations (in
``.vscode/launch.json``) AND is used by the Dockerfile for the deployed EV Taxis Optimizer or EV
Taxis Emulator.
"""

import argparse
import datetime as dt
import runpy
import typing
from typing import Type, Union

from src.deployment_interfaces.ev_taxis_interface import EvTaxisInterface
from src.environments import ENVIRONMENT_CLASSES, BaseEnvironment
from src.projects import PROJECT_TYPE


def main(
    configs_dir: str,
    ev_taxis_emulator_config_filename: Union[str, None],
    agent_config_filename: Union[str, None],
    environment_config_filename: str,
    environment_class: Type[BaseEnvironment],
    project: Union[PROJECT_TYPE, None],
) -> None:
    environment_config = runpy.run_path(configs_dir + environment_config_filename)[
        "environment_config"
    ]

    # Initialize either the EV taxis interface or EV taxis emulator, whichever is specified in the
    #     CLI args:
    if ev_taxis_emulator_config_filename is not None:
        ev_taxis_emulator_or_interface = runpy.run_path(
            configs_dir + ev_taxis_emulator_config_filename
        )["ev_taxis_emulator"]
    else:
        ev_taxis_emulator_or_interface = EvTaxisInterface(PROJECT=project)

    # Initialize an agent if specified in the CLI args:
    if agent_config_filename is not None:
        agent_or_interface = runpy.run_path(configs_dir + agent_config_filename)[
            "agent"
        ]
    else:
        # agent_or_interface = AgentInterface()
        # ^ Not used in favor of ``EvTaxisEmulatorEnvironment``...
        agent_or_interface = None

    environment = environment_class(
        environment_config,
        ev_taxis_emulator_or_interface,
        agent_or_interface,
        PROJECT=project,
    )
    environment.run()


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs-dir", dest="configs_dir")
    parser.add_argument(
        "--ev-taxis-emulator-config-filename",
        dest="ev_taxis_emulator_config_filename",
        default=None,
    )
    parser.add_argument(
        "--agent-config-filename",
        dest="agent_config_filename",
        default=None,
    )
    parser.add_argument(
        "--environment-config-filename",
        dest="environment_config_filename",
        default=None,
    )
    parser.add_argument(
        "--environment-class-name",
        choices=list(ENVIRONMENT_CLASSES.keys()),
        dest="environment_class_name",
        default="Environment",
    )
    parser.add_argument(
        "--project",
        choices=list(typing.get_args(PROJECT_TYPE)),
        dest="project",
        default=None,
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_cli_args()
    main(
        args.configs_dir,
        args.ev_taxis_emulator_config_filename,
        args.agent_config_filename,
        args.environment_config_filename,
        environment_class=ENVIRONMENT_CLASSES[args.environment_class_name],
        project=args.project,
    )
