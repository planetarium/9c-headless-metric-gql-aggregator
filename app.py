from typing import Optional
from urllib3.util import parse_url
from dateutil.parser import parse

import grequests

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

_MINER_HOST = [
    "9c-miner.planetarium.dev",
    "9c-main-validator-1.nine-chronicles.com",
    "9c-main-validator-2.nine-chronicles.com",
    "9c-main-validator-3.nine-chronicles.com",
    "9c-main-validator-4.nine-chronicles.com"
]

_NODE_LIST = [
    "9c-main-rpc-1.nine-chronicles.com",
    "9c-main-rpc-2.nine-chronicles.com",
    "9c-main-rpc-3.nine-chronicles.com",
    "9c-main-rpc-4.nine-chronicles.com",
    "9c-main-rpc-5.nine-chronicles.com",
    "tky-nc-1.ninodes.com",
    "sgp-nc-1.ninodes.com",
    "nj-nc-1.ninodes.com",
    "la-nc-1.ninodes.com",
    "fra-nc-1.ninodes.com",
    "9c-main-full-state.planetarium.dev",
    "api.9c.gg",
    "9c-main-data-provider-db.nine-chronicles.com",
    "d131807iozwu1d.cloudfront.net",
    "9c-main-onboarding-query.nine-chronicles.com",
    "9c-main-onboarding-transfer.nine-chronicles.com",
    "9c-main-validator-1.nine-chronicles.com",
    "9c-main-validator-2.nine-chronicles.com",
    "9c-main-validator-3.nine-chronicles.com",
    "9c-main-validator-4.nine-chronicles.com"
]

_GET_TIP_GRAPHQL_QUERY = """
query {
    nodeStatus {
        tip {
            index
        }
    }
}
"""


_RPC_CLIENTS_COUNT_GRAPHQL_QUERY = """
query {
    rpcInformation {
        totalCount
    }
}
"""

_STAGED_TXIDS_GRAPHQL_QUERY = """
query {
    nodeStatus {
        stagedTxIdsCount
    }
}
"""

_SUBSCRIBER_ADDRESSES_GRAPHQL_QUERY = """
query {
    nodeStatus {
        subscriberAddressesCount
    }
}
"""

_BLOCK_INTERVAL_GRAPHQL_QUERY = """
query{
  chainQuery{
    blockQuery{
      blocks(desc:true, limit:2){
        transactions{
          signature
        }
        timestamp
      }
    }
  }
}
"""

app = FastAPI()


def make_query_request(host: str, query: str) -> grequests.AsyncRequest:
    try:
        if host == "api.9c.gg" or host == "9c-main-data-provider-db.nine-chronicles.com":
            return grequests.post(
                f"http://{host}/graphql_headless",
                json={"query": query},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        return grequests.post(
            f"http://{host}/graphql",
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    except:
        pass


def make_get_tip_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _GET_TIP_GRAPHQL_QUERY)


def make_get_rpc_clients_count_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _RPC_CLIENTS_COUNT_GRAPHQL_QUERY)


def make_get_staged_txids_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _STAGED_TXIDS_GRAPHQL_QUERY)


def make_get_subscribe_addresses_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _SUBSCRIBER_ADDRESSES_GRAPHQL_QUERY)

def make_get_block_interval_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _BLOCK_INTERVAL_GRAPHQL_QUERY)

def exception_handler(request, exception):
    print(exception)


@app.get("/metrics")
def aggregate_metrics():
    BANNED_HOSTS = [
    ]

    responses = grequests.map(
        (
            *map(make_get_tip_request, (_MINER_HOST, *_NODE_LIST)),
            *map(make_get_rpc_clients_count_request, _NODE_LIST),
            *map(make_get_staged_txids_request, filter(lambda x: x not in BANNED_HOSTS, _NODE_LIST)),
            *map(make_get_subscribe_addresses_request, filter(lambda x: x not in BANNED_HOSTS, _NODE_LIST)),
            *map(make_get_block_interval_request, _MINER_HOST),
        ), exception_handler=exception_handler
    )

    metrics = ""
    for response in responses:
        try:
            if response.status_code != 200:
                continue

            host = parse_url(response.url).host
            name = host
            data = response.json()["data"]
            metric: Optional[str] = None

            if "nodeStatus" in data:
                node_status = data["nodeStatus"]
                if "tip" in node_status:
                    tip_index = node_status["tip"]["index"]
                    if tip_index is not None:
                        metric = f'ninechronicles_tip_index{{host="{host}",name="{name}"}} {tip_index}'
                elif "stagedTxIdsCount" in node_status:
                    staged_txids_count = node_status["stagedTxIdsCount"]
                    if staged_txids_count is not None:
                        metric = f'ninechronicles_staged_txids_count{{host="{host}",name="{name}"}} {staged_txids_count}'
                elif "subscriberAddressesCount" in node_status:
                    subscriber_addresses_count = node_status["subscriberAddressesCount"]
                    if subscriber_addresses_count is not None:
                        metric = f'ninechronicles_subscriber_addresses_count{{host="{host}",name="{name}"}} {subscriber_addresses_count}'
            elif "rpcInformation" in data:
                rpc_clients_count = data["rpcInformation"]["totalCount"]
                if rpc_clients_count is not None:
                    metric = f'ninechronicles_rpc_clients_count{{host="{host}",name="{name}"}} {rpc_clients_count}'
            elif "chainQuery" in data:
                tip_timestamp = data["chainQuery"]["blockQuery"]["blocks"][0]["timestamp"]
                previous_timestamp = data["chainQuery"]["blockQuery"]["blocks"][1]["timestamp"]
                time = parse(tip_timestamp) - parse(previous_timestamp)
                interval = time.total_seconds()
                transactions = data["chainQuery"]["blockQuery"]["blocks"][0]["transactions"]
                tx_count = len(transactions)
                print(tx_count)
                metric = f'ninechronicles_tx_count{{host="{host}",name="{name}"}} {tx_count}'
                metric += "\n"
                print(interval)
                metric += f'ninechronicles_block_interval{{host="{host}",name="{name}"}} {interval}'

            if metric is not None:
                metrics += metric
                metrics += "\n"
        except:
            pass

    return PlainTextResponse(metrics)
