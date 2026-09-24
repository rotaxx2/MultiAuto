"""Development settings for MultiAuto."""

from .base import *  # noqa: F403

DEBUG = env_bool("DEBUG", True)  # noqa: F405

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
