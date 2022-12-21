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
    "9c-main-rpc-8.nine-chronicles.com",
    "9c-main-rpc-9.nine-chronicles.com",
    "9c-main-rpc-10.nine-chronicles.com",
    "9c-main-rpc-11.nine-chronicles.com",
    "9c-main-rpc-12.nine-chronicles.com",
    "9c-main-rpc-13.nine-chronicles.com",
    "9c-main-rpc-14.nine-chronicles.com",
    "9c-main-rpc-15.nine-chronicles.com",
    "9c-main-rpc-16.nine-chronicles.com",
    "9c-main-rpc-17.nine-chronicles.com",
    "9c-main-rpc-18.nine-chronicles.com",
    "9c-main-rpc-19.nine-chronicles.com",
    "9c-main-rpc-20.nine-chronicles.com",
    "9c-main-rpc-21.nine-chronicles.com",
    "9c-main-rpc-22.nine-chronicles.com",
    "9c-main-rpc-23.nine-chronicles.com",
    "9c-main-rpc-24.nine-chronicles.com",
    "9c-main-rpc-25.nine-chronicles.com",
    "9c-main-rpc-26.nine-chronicles.com",
    "9c-main-rpc-27.nine-chronicles.com",
    "9c-main-rpc-28.nine-chronicles.com",
    "9c-main-rpc-29.nine-chronicles.com",
    "9c-main-rpc-30.nine-chronicles.com",
    "9c-main-rpc-31.nine-chronicles.com",
    "9c-main-rpc-32.nine-chronicles.com",
    "9c-main-rpc-33.nine-chronicles.com",
    "9c-main-rpc-34.nine-chronicles.com",
    "9c-main-rpc-35.nine-chronicles.com",
    "9c-main-rpc-36.nine-chronicles.com",
    "9c-main-rpc-37.nine-chronicles.com",
    "9c-main-rpc-38.nine-chronicles.com",
    "9c-main-rpc-39.nine-chronicles.com",
    "9c-main-rpc-40.nine-chronicles.com",
    "9c-main-rpc-41.nine-chronicles.com",
    "9c-main-rpc-42.nine-chronicles.com",
    "9c-main-rpc-43.nine-chronicles.com",
    "9c-main-rpc-44.nine-chronicles.com",
    "9c-main-rpc-45.nine-chronicles.com",
    "9c-main-rpc-46.nine-chronicles.com",
    "9c-main-rpc-47.nine-chronicles.com",
    "9c-main-rpc-48.nine-chronicles.com",
    "9c-main-rpc-49.nine-chronicles.com",
    "9c-main-rpc-50.nine-chronicles.com",
    "9c-main-rpc-99.nine-chronicles.com",
    "tky-nc-1.ninodes.com",
    "sgp-nc-1.ninodes.com",
    "nj-nc-1.ninodes.com",
    "la-nc-1.ninodes.com",
    "fra-nc-1.ninodes.com",
    "rpc-for-snapshot.nine-chronicles.com",
    "9c-main-full-state.planetarium.dev",
    "9c-main-miner-2.nine-chronicles.com",
    "9c-main-miner-3.nine-chronicles.com",
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
    return grequests.post(
        f"http://{host}/graphql",
        json={"query": query},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )


def make_get_tip_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _GET_TIP_GRAPHQL_QUERY)


def make_get_rpc_clients_count_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _RPC_CLIENTS_COUNT_GRAPHQL_QUERY)

def make_get_staged_txids_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _STAGED_TXIDS_GRAPHQL_QUERY)


def make_get_subscribe_addresses_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _SUBSCRIBER_ADDRESSES_GRAPHQL_QUERY)


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
        )
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
