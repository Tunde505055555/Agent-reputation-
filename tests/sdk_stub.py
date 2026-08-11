"""
Minimal stand-in for the parts of the `genlayer` SDK the pure helpers touch.

The contract module is imported for its deterministic helpers only; no GenVM,
no network, no LLM. Anything non-deterministic is never called by the tests.
"""

import sys
import types
import typing


class _Int(int):
    def __new__(cls, value=0):
        return super().__new__(cls, int(value))


u8 = _Int
u256 = _Int


class Address:
    def __init__(self, value: str = "0x" + "0" * 40):
        self._value = value

    @property
    def as_hex(self) -> str:
        return self._value


class _Generic:
    def __class_getitem__(cls, item):
        return list


class DynArray(_Generic):
    pass


class TreeMap(dict):
    def __class_getitem__(cls, item):
        return dict


def allow_storage(cls):
    return cls


class _Nondet:
    class web:
        @staticmethod
        def render(*_a, **_k):  # pragma: no cover - never called in tests
            raise RuntimeError("nondet is not available in unit tests")

    @staticmethod
    def exec_prompt(*_a, **_k):  # pragma: no cover
        raise RuntimeError("nondet is not available in unit tests")


class _Vm:
    class Return:
        def __init__(self, data):
            self.data = data

    @staticmethod
    def run_nondet(*_a, **_k):  # pragma: no cover
        raise RuntimeError("consensus is not available in unit tests")


class _EqPrinciple:
    @staticmethod
    def strict_eq(fn):  # pragma: no cover
        return fn()


class _Message:
    sender_address = Address()


class _Gl:
    nondet = _Nondet
    vm = _Vm
    eq_principle = _EqPrinciple
    message = _Message

    class public:
        @staticmethod
        def write(fn):
            return fn

        @staticmethod
        def view(fn):
            return fn

    class Contract:
        pass


gl = _Gl


def install() -> None:
    """Register a fake `genlayer` module so `from genlayer import *` works."""
    module = types.ModuleType("genlayer")
    for name in (
        "u8",
        "u256",
        "Address",
        "DynArray",
        "TreeMap",
        "allow_storage",
        "gl",
    ):
        setattr(module, name, globals()[name])
    module.__all__ = [
        "u8",
        "u256",
        "Address",
        "DynArray",
        "TreeMap",
        "allow_storage",
        "gl",
    ]
    module.typing = typing
    sys.modules["genlayer"] = module
