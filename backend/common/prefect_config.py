"""Prefect configuration - must be imported before any prefect import"""
import os
import logging

logger = logging.getLogger(__name__)

_prefect_api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
os.environ["PREFECT_API_URL"] = _prefect_api_url

if os.getenv("PREFECT_API_URL_SET") != "true":
    print(f"[Prefect Config] PREFECT_API_URL set to : {_prefect_api_url}")
    os.environ["PREFECT_API_URL_SET"] = "true"