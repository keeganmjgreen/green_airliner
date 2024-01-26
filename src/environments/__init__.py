from .environment import BaseEnvironment, Environment, EnvironmentConfig
from .ev_taxis_emulator_environment import EvTaxisEmulatorEnvironment
from .visualizer_environment import VisualizerEnvironment

ENVIRONMENT_CLASSES = {
    "Environment": Environment,
    "EvTaxisEmulatorEnvironment": EvTaxisEmulatorEnvironment,
    "VisualizerEnvironment": VisualizerEnvironment,
}
