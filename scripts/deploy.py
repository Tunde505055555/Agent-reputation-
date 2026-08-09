"""
Headless deploy / smoke-call for AgentReputation.

Requires the official Python SDK client:

    pip install genlayer-py

Usage (Studio running locally on http://localhost:8545 by default):

    python scripts/deploy.py
    python scripts/deploy.py --allowed-domains "github.com,etherscan.io" --min-evidence 3

This script only deploys and reads back `config()`. It is deliberately thin: the
contract is the deliverable, this is tooling.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.chains import localnet

CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "agent_reputation.py"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allowed-domains", default="", help="comma separated hostnames")
    ap.add_argument("--criteria", default="", help="extra rubric guidance")
    ap.add_argument("--min-evidence", type=int, default=2)
    args = ap.parse_args()

    account = create_account()
    client = create_client(chain=localnet, account=account)

    code = CONTRACT.read_bytes()
    tx_hash = client.deploy_contract(
        code=code,
        args=[args.allowed_domains, args.criteria, args.min_evidence],
    )
    receipt = client.wait_for_transaction_receipt(transaction_hash=tx_hash)
    address = receipt["tx_data_decoded"]["contract_address"]
    print(f"deployed AgentReputation at {address}")

    config = client.read_contract(address=address, function_name="config", args=[])
    print("config:", config)


if __name__ == "__main__":
    main()
