from urllib3.util import parse_url

import grequests

from fastapi.responses import PlainTextResponse, FastAPI

_MINER_HOST = "a53d8b9e8f9604e088da646d930fcb8d-956876586.us-east-2.elb.amazonaws.com"

_NODE_LIST = [
    "a726a6b13cb0b42bf9202b826589691f-1185007955.us-east-2.elb.amazonaws.com",
    "adb0e2bb7e3244739a0cc5f41f472276-45738665.us-east-2.elb.amazonaws.com",
    "adb82cf4701c74b36984366808e29915-1650973590.us-east-2.elb.amazonaws.com",
    "a68fae48aeecd4661bc653eb8bfb5815-777682477.us-east-2.elb.amazonaws.com",
    "a9a7fa4e68584472eadaa859c1ccfa96-307491802.us-east-2.elb.amazonaws.com",
    "a2e01f4a7f4ce47efa3097d52fdf56f8-108664089.us-east-2.elb.amazonaws.com",
    "a6b8aa8271d6946ea998b110863cbfb9-1918498264.us-east-2.elb.amazonaws.com",
    "ae4fa84e10d214209ad600a77371223a-1562070758.us-east-2.elb.amazonaws.com",
    "af7640523846d4152b45b33076a5629d-1374793070.us-east-2.elb.amazonaws.com",
    "a0d01f897e0a2434798e8b4607ac32ea-994288696.us-east-2.elb.amazonaws.com",
    "aaa453a1c166c4d7eb6dad7151ca373b-1343028350.us-east-2.elb.amazonaws.com",
    "a5e8503f9fd024ca292f193c86de744a-754114509.us-east-2.elb.amazonaws.com",
    "a00d334f09e1c42feb4c38f8c3010543-423825111.us-east-2.elb.amazonaws.com",
    "aa7d058e4606a4cc7b2bc7c6c915670b-1136359886.us-east-2.elb.amazonaws.com",
    "afff4ede31cef4543a2706d8b1f594e2-1812701003.us-east-2.elb.amazonaws.com",
    "af1da83a0dbf14b1d976308c7b3efb5d-689966316.us-east-2.elb.amazonaws.com",
    "a2bb53cb50b1f4e698396bdc9f93320e-1430351524.us-east-2.elb.amazonaws.com",
    "a86a3b8c3140943ec9abe0115e8ab0b6-1765153438.us-east-2.elb.amazonaws.com",
    "adb1932b4da92426abd7116c65875faa-1809698636.us-east-2.elb.amazonaws.com",
    "ac38a8718f27544c088bb73086ff305c-1852178024.us-east-2.elb.amazonaws.com",
    "a249bfd0a2d824fbf96c0ab7106b5fb0-80418454.us-east-2.elb.amazonaws.com",
    "a965cf61739c14183b9ee206b8458306-810507692.us-east-2.elb.amazonaws.com",
    "afe446b3d248f4bf29f9b92d0b71d195-848460787.us-east-2.elb.amazonaws.com",
    "a34415872a2ae4f9b89b6c639df0fee7-1415055500.us-east-2.elb.amazonaws.com",
    "a58819a6914a24305af83416886e8f39-2046615975.us-east-2.elb.amazonaws.com",
    "a50aca9e3537a4e97b6754475e3d619c-1739743385.us-east-2.elb.amazonaws.com",
    "a927855518edb4fd8945282bf5f9b4ae-837122180.us-east-2.elb.amazonaws.com",
    "a37a4ef26ef2f41bdb6939d68681f5e8-1379894347.us-east-2.elb.amazonaws.com",
    "ab9ae0958ce02433e9151e58da984a20-2032716986.us-east-2.elb.amazonaws.com",
    "a188856db6b6945199a1b9b308e941a1-1648614630.us-east-2.elb.amazonaws.com",
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

app = FastAPI()


def make_query_request(host: str, query: str) -> grequests.AsyncRequest:
    return grequests.post(
        f"http://{host}/graphql",
        json={"query": query},
        headers={"Content-Type": "application/json"},
    )


def make_get_tip_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _GET_TIP_GRAPHQL_QUERY)


def make_get_rpc_clients_count_request(host: str) -> grequests.AsyncRequest:
    return make_query_request(host, _RPC_CLIENTS_COUNT_GRAPHQL_QUERY)


@app.get("/metrics")
def aggregate_metrics():
    responses = grequests.map(
        (
            *map(make_get_tip_request, (_MINER_HOST, *_NODE_LIST)),
            *map(make_get_rpc_clients_count_request, _NODE_LIST),
        )
    )

    metrics = ""
    for response in responses:
        try:
            if response.status_code != 200:
                continue

            host = parse_url(response.url).host
            data = response.json()["data"]
            metric: str

            if "nodeStatus" in data:
                tip_index = data["nodeStatus"]["tip"]["index"]
                metric = f'ninechronicles_tip_index{{host="{host}"}} {tip_index}'
            elif "rpcInformation" in data:
                rpc_clients_count = data["rpcInformation"]["totalCount"]
                metric = f'ninechronicles_rpc_clients_count{{host="{host}"}} {rpc_clients_count}'

            metrics += metric
            metrics += "\n"
        except:
            pass

    return PlainTextResponse(metrics)
