# Modified for MB Scene Creator (2026): independent integration namespace.
"""Test setup: make the integration of this repo importable as custom_components.mb_scene_creator."""

import os

import custom_components

custom_components.__path__.append(os.path.join(os.path.dirname(__file__), "..", "custom_components"))
