from typing import Optional
from urllib3.util import parse_url

import grequests

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

_MINER_HOST = "9c-miner.planetarium.dev"

_NODE_LIST = [
    "9c-main-rpc-1.nine-chronicles.com",
    "9c-main-rpc-2.nine-chronicles.com",
    "9c-main-rpc-3.nine-chronicles.com",
    "9c-main-rpc-4.nine-chronicles.com",
    "9c-main-rpc-5.nine-chronicles.com",
    "9c-main-rpc-31.nine-chronicles.com",
    "tky-nc-1.ninodes.com",
    "sgp-nc-1.ninodes.com",
    "nj-nc-1.ninodes.com",
    "la-nc-1.ninodes.com",
    "fra-nc-1.ninodes.com",
    "9c-main-full-state.planetarium.dev",
    "9c-main-miner-2.nine-chronicles.com",
    "9c-main-miner-3.nine-chronicles.com",
    "api.9c.gg",
    "9c-main-data-provider-db.nine-chronicles.com",
    "a5bba99adb503495baa274a7e06a91bb-225412308.us-east-2.elb.amazonaws.com:23061",
    "a0da6ab2a59a546e6b632a6cb9c0a577-498991761.us-east-2.elb.amazonaws.com:23061",
    "9c-internal-rpc-1.nine-chronicles.com",
    "a778316ca16af4065a02dc2753c1a0fc-1775306312.us-east-2.elb.amazonaws.com",
    "ae177a0efd48c42c68ef1908fcdb0954-1722243693.us-east-2.elb.amazonaws.com:31235"
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

            if metric is not None:
                metrics += metric
                metrics += "\n"
        except:
            pass

    return PlainTextResponse(metrics)
