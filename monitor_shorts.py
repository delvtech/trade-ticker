"""Deploy a Streamlit dashboard that shows tickers for shorts on select pools."""

import os
import time

import streamlit as st
from agent0 import Chain, Hyperdrive
from agent0.chainsync.db.hyperdrive import get_pool_info, get_trade_events
from dotenv import load_dotenv

# pylint: disable=protected-access

load_dotenv(".env")

## Set ENV variables
# asserts are for type narrowing
RPC_URI = os.getenv("MAIN_RPC_URI")
assert RPC_URI is not None

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
assert ALCHEMY_API_KEY is not None
RPC_URI += ALCHEMY_API_KEY

REGISTRY_ADDRESS = os.getenv("MAIN_REGISTRY_ADDRESS")
assert REGISTRY_ADDRESS is not None

POOL_ADDRESSES = {
    pool_name: os.getenv(pool_name)
    for pool_name in os.getenv("POOL_ADDRESSES", "").replace(" ", "").split(",")
}
assert None not in POOL_ADDRESSES.values()

## Streamlit setup
st.set_page_config(page_title="Morpho pool short ticker", layout="wide")

ticker_placeholders = {pool_name: st.empty() for pool_name in POOL_ADDRESSES.keys()}

## Get data & display in the Streamlit dashboard
with Chain(RPC_URI) as chain:
    registered_pools = Hyperdrive.get_hyperdrive_pools_from_registry(
        chain,
        registry_address=REGISTRY_ADDRESS,
    )
    session = chain.db_session
    assert session is not None  # type narrowing
    max_live_blocks = 5_000
    while True:
        for pool_name, pool_address in POOL_ADDRESSES.items():
            print(f"{pool_address=}")
            print(f"{[pool.hyperdrive_address for pool in registered_pools]}")
            print(f"{[pool for pool in registered_pools if pool.hyperdrive_address == pool_address]}")
            morpho_pool = next(pool for pool in registered_pools if pool.hyperdrive_address == pool_address)
            morpho_pool._sync_events()

            pool_info = get_pool_info(
                session, hyperdrive_address=pool_address, start_block=-max_live_blocks, coerce_float=False
            )
            # Get a block to timestamp mapping dataframe
            block_to_timestamp = pool_info[["block_number", "timestamp"]]

            # Get the trade events
            out = get_trade_events(
                session,
                hyperdrive_address=pool_address,
                all_token_deltas=False,
                coerce_float=False,
                sort_ascending=False,  # We want the latest first in a ticker
                query_limit=1_000,
            ).drop("id", axis=1)
            out = chain._add_hyperdrive_name_to_dataframe(out, "hyperdrive_address")
            out = out[out["event_type"].isin(["OpenShort", "CloseShort"])]
            out = out.merge(block_to_timestamp, how="left", on="block_number")
            # Mapping for any type conversions.
            # Omissions mean leave as is
            type_dict = {
                "block_number": "int",
                "wallet_address": "str",
                "event_type": "str",
                "token_id": "str",
                "token_delta": "float64",
                "base_delta": "float64",
                "vault_share_delta": "float64",
            }
            rename_dict = {
                "timestamp": "Timestamp",
                "block_number": "Block Number",
                "wallet_address": "Wallet",
                "event_type": "Trade",
                "token_id": "Token",
                "token_delta": "Token Change",
                "base_delta": "Base Change",
                "vault_share_delta": "Vault Share Change",
            }
            out = out[list(rename_dict.keys())].astype(type_dict).rename(columns=rename_dict)

            with ticker_placeholders[pool_name].container():
                st.header(pool_name)
                st.dataframe(out.style.format(precision=18), height=200, use_container_width=True)

            # Slow down refreshes
            time.sleep(1)
