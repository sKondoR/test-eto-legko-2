"""Печатает OpenAPI-схему в stdout без запуска сервера."""

import json
import sys

from app.main import app

sys.stdout.write(json.dumps(app.openapi(), indent=2))
