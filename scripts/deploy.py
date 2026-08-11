"""
Headless deployment of AgentReputation with genlayer-py.

    pip install genlayer-py
    export GENLAYER_RPC=http://localhost:4000/api      # Studio default
    export GENLAYER_PRIVATE_KEY=0x...                  # optional on Studio
    python scripts/deploy.py --min-evidence 3 \
        --allowed-domains github.com,upwork.com,etherscan.io

Studio users can equally paste contracts/agent_reputation.py into the UI; this
script only exists so deployment is reproducible in CI.
"""

import argparse
import os
import pathlib
import sys

CONTRACT = (
    pathlib.Path(__file__).resolve().parents[1] / "contracts" / "agent_reputation.py"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy AgentReputation")
    parser.add_argument("--allowed-domains", default="")
    parser.add_argument("--criteria", default="")
    parser.add_argument("--min-evidence", type=int, default=2)
    parser.add_argument("--rpc", default=os.environ.get("GENLAYER_RPC", ""))
    args = parser.parse_args()

    try:
        from genlayer_py import create_account, create_client
        from genlayer_py.chains import localnet
    except ImportError:
        print("genlayer-py is not installed: pip install genlayer-py", file=sys.stderr)
        return 1

    key = os.environ.get("GENLAYER_PRIVATE_KEY")
    account = create_account(account_private_key=key) if key else create_account()
    client = create_client(
        chain=localnet,
        account=account,
        endpoint=args.rpc or None,
    )

    code = CONTRACT.read_bytes()
    tx_hash = client.deploy_contract(
        code=code,
        args=[args.allowed_domains, args.criteria, args.min_evidence],
    )
    receipt = client.wait_for_transaction_receipt(transaction_hash=tx_hash)
    address = receipt.get("data", {}).get("contract_address", receipt)
    print("deployed AgentReputation at:", address)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
