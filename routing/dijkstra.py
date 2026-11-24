from core.contracts import Graph, RouteRequest, Context, RouteResult, Algorithm
from routing.astar import search_core


def find_route(graph: Graph, request: RouteRequest, context: Context, with_trace: bool = False) -> RouteResult:
    return search_core(
        graph=graph,
        request=request,
        context=context,
        heuristic_fn=lambda graph, node, destination: 0.0,
        algorithm_name=Algorithm.DIJKSTRA,
        with_trace=with_trace
    )