"""
Test shim: a minimal stand-in for the GenLayer SDK.

The contract is a single file that does `from genlayer import *`. To unit-test the
*pure, deterministic* helpers (URL/host parsing, allowlist checks, fence stripping,
flag normalisation, JSON extraction, assessment normalisation) we install this stub
into `sys.modules` before importing the contract. Nothing here simulates consensus —
consensus behaviour belongs in GenLayer Studio, not in a Python unit test.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts" / "agent_reputation.py"


class _Sub:
    """Anything subscriptable and callable, e.g. TreeMap[str, Agent], u8(3)."""

    def __init__(self, name: str):
        self._name = name

    def __class_getitem__(cls, item):  # pragma: no cover
        return cls

    def __getitem__(self, item):
        return self

    def __call__(self, value=None, *a, **k):
        return value


class _Contract:
    """Stand-in for gl.Contract so the contract class can be defined."""


class _Any:
    """Attribute bag that returns itself, so gl.public.write works as a decorator."""

    def __getattr__(self, name):
        if name == "Contract":
            return _Contract
        return self

    def __call__(self, fn=None, *a, **k):
        return fn if callable(fn) else self


def install() -> types.ModuleType:
    mod = types.ModuleType("genlayer")
    mod.gl = _Any()
    mod.Address = _Sub("Address")
    mod.u8 = int
    mod.u32 = int
    mod.u64 = int
    mod.u256 = int
    mod.bigint = int
    mod.DynArray = _Sub("DynArray")
    mod.TreeMap = _Sub("TreeMap")
    mod.allow_storage = lambda cls: cls
    mod.__all__ = [
        "gl",
        "Address",
        "u8",
        "u32",
        "u64",
        "u256",
        "bigint",
        "DynArray",
        "TreeMap",
        "allow_storage",
    ]
    sys.modules["genlayer"] = mod
    return mod


def load_contract_module() -> types.ModuleType:
    install()
    import importlib.util

    spec = importlib.util.spec_from_file_location("agent_reputation", CONTRACT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
