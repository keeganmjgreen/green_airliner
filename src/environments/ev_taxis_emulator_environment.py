"""
Note: This is used instead of ``agent_interface.py``.
"""

import dataclasses
import datetime as dt
import os
from typing import Any, Dict

import flask
import pytz
import waitress

from src.deployment_interfaces.optimizer_dispatch import AssetAction
from src.emulators import EvTaxisEmulator
from src.modeling_objects import AgentAction
from src.utils.utils import datetime_to_utc_string

from .environment import BaseEnvironment


class EvTaxisEmulatorEnvironment(BaseEnvironment):
    """An environment used in the deployed EV Taxis Emulator component.

    Methods ``get_evs_state``, ``get_charge_points_state``, and ``get_ongoing_trips_state``
    represent API endpoints of the EV Taxis Emulator component (see their docstrings for details).
    Note: Because of this, each of these three methods must first call the environment's
    ``_update_timestamp`` followed by the environment's ``_get_state`` (or the EvTaxisEmulator's
    ``update_state`` directly).

    The first API call must be within the EvTaxisEmulator's ``APPROX_MAX_TIME_STEP`` of its
    ``START_TIMESTAMP`` and each subsequent API call must be within ``APPROX_MAX_TIME_STEP`` of the
    previous API call.
    """

    # Host and port of the EV Taxis Emulator component:
    EV_TAXIS_EMULATOR_HOST: str = os.getenv("EV_TAXIS_EMULATOR_HOST")
    EV_TAXIS_EMULATOR_PORT: int = os.getenv("EV_TAXIS_EMULATOR_PORT")

    def __post_init__(self):
        """
        Todos:
            Use a class for each endpoint.
        """

        super().__post_init__()

        if self.TIME_STEP is not None:
            self.TIME_STEP = None
            self.DELAY_TIME_STEP = None
            print(
                f"{type(self).__name__}.__post_init__: `TIME_STEP` specified and set to None "
                "(along with `DELAY_TIME_STEP`)."
            )

        assert isinstance(self.ev_taxis_emulator_or_interface, EvTaxisEmulator)
        assert self.AGENT_OR_INTERFACE is None
        # self.ev_taxis_emulator_or_interface.provision_low_vol_db(project=self.PROJECT)

        self.flask_app = flask.Flask(__name__)

        @self.flask_app.route("/evs_state", methods=["GET"])
        def get_evs_state():
            """Mimics the current state of EVs that we may be able to obtain live from, e.g.,
            Smartcar.
            """

            self._update_timestamp()
            environment_state = self._get_state(self.current_timestamp)

            return self._format_response(
                {"evs": [ev.to_json() for ev in environment_state.evs_state.values()]}
            )

        @self.flask_app.route("/charge_points_state", methods=["GET"])
        def get_charge_points_state():
            """Mimics the current state of charge points that we may be able to obtain live from,
            e.g., Dubai DEWA EV Green Charger API.
            """

            self._update_timestamp()
            environment_state = self._get_state(self.current_timestamp)

            return self._format_response(
                {
                    "charge_points": [
                        cp.to_json()
                        for charging_site in environment_state.charging_sites_state.values()
                        for cp in charging_site.charge_points.values()
                    ]
                }
            )

        @self.flask_app.route("/ongoing_trips_state", methods=["GET"])
        def get_ongoing_trips_state():
            """Mimics the current trips' state that we may be able to obtain live from, e.g., Dubai
            Taxi's app.
            """

            self._update_timestamp()
            self.ev_taxis_emulator_or_interface.update_state(self.current_timestamp)

            return self._format_response(
                {
                    "ongoing_trips": [
                        trip.to_json(self.current_timestamp)
                        for trip in self.ev_taxis_emulator_or_interface.current_state.ongoing_trips_state
                    ]
                }
            )

        @self.flask_app.route("/action", methods=["POST"])
        def perform_action():
            self._update_timestamp()
            # Update EvTaxisEmulator's ``current_state``:
            self._get_state(self.current_timestamp)

            json_asset_actions = flask.request.get_json()
            asset_actions = [
                AssetAction.from_json(json_aa) for json_aa in json_asset_actions
            ]
            self._perform_action(action=AgentAction.from_asset_actions(asset_actions))

            return "Asset actions performed successfully."

    def _update_timestamp(self) -> None:
        """Update the environment's current timestamp to 'right now'.

        The environment's current timestamp is updated separately (before) that of the
        EvTaxisEmulator.
        """

        self.current_timestamp = dt.datetime.now(tz=pytz.utc)

    def _format_response(self, response: Dict[str, Any]):
        return flask.jsonify(
            {
                **response,
                "timestamp": datetime_to_utc_string(self.current_timestamp),
            }
        )

    def run(self) -> None:
        super().run()

        waitress.serve(
            self.flask_app,
            host=self.EV_TAXIS_EMULATOR_HOST,
            port=int(self.EV_TAXIS_EMULATOR_PORT),
        )
