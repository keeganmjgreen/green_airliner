from .environment import BaseEnvironment, Environment, EnvironmentConfig
from .visualizer_environment import VisualizerEnvironment

ENVIRONMENT_CLASSES = {
    "Environment": Environment,
    "VisualizerEnvironment": VisualizerEnvironment,
}
