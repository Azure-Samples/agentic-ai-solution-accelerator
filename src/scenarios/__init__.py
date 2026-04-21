"""Scenarios — each sub-package is one accelerator scenario instance.

The flagship Sales Research & Outreach lives at ``sales_research``. Partners
add new scenarios with ``scripts/scaffold-scenario.py``. The scenario that
runs at any given moment is declared by the top-level ``scenario:`` block in
``accelerator.yaml`` and loaded via :mod:`src.workflow.registry`.
"""
