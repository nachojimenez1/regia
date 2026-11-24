from core.contracts import Graph, RouteRequest, Context, RouteResult, Algorithm, Edge, EdgeKind, NodeId, RouteStep, TraceStep
import heapq
from typing import Callable
from routing.costs import edge_cost, initial_wait, is_station_blocked, real_edge_minutes
from routing.heuristics import estimate


def _snapshot_open(open_heap: list[tuple[float, int, NodeId]], closed_set: set[NodeId]) -> tuple[NodeId, ...]:
    seen: set[NodeId] = set()
    ordered: list[NodeId] = []
    for _, _, node in sorted(open_heap):
        if node not in closed_set and node not in seen:
            seen.add(node)
            ordered.append(node)
    return tuple(ordered)



def search_core(graph: Graph,
                request: RouteRequest,
                context: Context,
                heuristic_fn: Callable[[Graph, NodeId, str], float],
                algorithm_name: Algorithm,
                with_trace: bool = False
                ) -> RouteResult:

    origin = request.origin
    destination = request.destination
    if origin not in graph.stations or destination not in graph.stations:
        raise ValueError(f"Estacion de origen '{origin}' o destino '{destination}' no existe")

    if(
        not context.service_open
        or is_station_blocked(origin, context, request.profile, graph)
        or is_station_blocked(destination, context, request.profile, graph)
    ):
        return RouteResult(found=False,
                           steps=(),
                           total_minutes=0.0,
                           transfers=0,
                           nodes_expanded=0,
                           algorithm=algorithm_name,
                           trace=()
                           )

    if origin == destination:
        origin_info=graph.stations[origin]
        line_id = (origin_info.line_ids[0] if origin_info.line_ids else next(iter(graph.lines.keys()), ""))

        trivial_step = RouteStep(station_id=origin,
                                 line_id=line_id,
                                 minutes=0.0,
                                 )
        return RouteResult(found=True,
                           steps=(trivial_step,),
                           total_minutes=0.0,
                           transfers=0,
                           nodes_expanded=0,
                           algorithm=algorithm_name,
                           trace=()
                           )

    start_nodes: list[NodeId] = [node for node in graph.edges.keys() if node[0] == origin]

    if not start_nodes:
        return RouteResult(found=False,
                           steps=(),
                           total_minutes=0.0,
                           transfers=0,
                           nodes_expanded=0,
                           algorithm=algorithm_name,
                           trace=()
                           )

    open_heap: list[tuple[float, int, NodeId]] = []
    tie_counter=0

    g_score: dict[NodeId, float] = {}
    came_from: dict[NodeId, tuple[NodeId, Edge]] = {}
    closed_set: set[NodeId] = set()
    closed_order: list[NodeId] = []

    for s_node in start_nodes:
        w_init = initial_wait(s_node[1], context)
        g_score[s_node] = w_init
        h_init = heuristic_fn(graph, s_node, destination)
        f_init = w_init + h_init
        heapq.heappush(open_heap, (f_init, tie_counter, s_node))
        tie_counter+=1

    nodes_expanded = 0
    trace_steps: list[TraceStep] = []
    goal_reached_node: NodeId | None = None

    while open_heap:
        f_curr, _, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue

        closed_set.add(current)
        closed_order.append(current)
        nodes_expanded+=1
        curr_g=g_score[current]


        if current[0] == destination:
            goal_reached_node = current

            if with_trace:
                trace_steps.append(
                    TraceStep(node=current,
                              g=curr_g,
                              h=0.0,
                              f=curr_g,
                              open=_snapshot_open(open_heap, closed_set),
                              closed=tuple(closed_order),
                    )
                )
            break


        for edge in graph.edges.get(current, []):
            neighbor=edge.target
            if neighbor in closed_set:
                continue
            cost = edge_cost(edge, context, request.profile, graph)
            if cost == float("inf"):
                continue
            tentative_g = curr_g + cost
            if tentative_g<g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                came_from[neighbor] = (current, edge)

                h_val = heuristic_fn(graph, neighbor, destination)
                f_val = tentative_g + h_val

                heapq.heappush(open_heap, (f_val, tie_counter, neighbor))
                tie_counter+=1

        if with_trace:
            curr_h = heuristic_fn(graph, current, destination)
            trace_steps.append(
                TraceStep(node=current,
                          g=curr_g,
                          h=curr_h,
                          f=f_curr,
                          open=_snapshot_open(open_heap, closed_set),
                          closed=tuple(closed_order)

                )
            )
    if goal_reached_node is None:
        return RouteResult(
            found=False,
            steps=(),
            total_minutes=0.0,
            transfers=0,
            nodes_expanded=nodes_expanded,
            algorithm=algorithm_name,
            trace=tuple(trace_steps) if with_trace else ()

        )
    path_edges: list[Edge] = []
    curr = goal_reached_node
    while curr in came_from:
        prev_node, edge_used = came_from[curr]
        path_edges.append(edge_used)
        curr = prev_node

    path_edges.reverse()

    steps: list[RouteStep] = []

    first_node = path_edges[0].source if path_edges else goal_reached_node
    steps.append(
        RouteStep(
            station_id=first_node[0],
            line_id=first_node[1],
            minutes=0.0,
        )
    )


    accumulated_minutes = initial_wait(first_node[1], context)
    transfers=0

    for edge in path_edges:
        accumulated_minutes += real_edge_minutes(edge, context)
        steps.append(
            RouteStep(
                station_id=edge.target[0],
                line_id=edge.target[1],
                minutes=accumulated_minutes
            )
        )
        if edge.kind == EdgeKind.TRANSFER:
            transfers += 1
    return RouteResult(
        found=True,
        steps=tuple(steps),
        total_minutes=accumulated_minutes,
        transfers=transfers,
        nodes_expanded=nodes_expanded,
        algorithm=algorithm_name,
        trace=tuple(trace_steps) if with_trace else ()
    )


def find_route(graph: Graph, request: RouteRequest, context: Context, with_trace: bool = False) -> RouteResult:
    return search_core(
        graph=graph,
        request=request,
        context=context,
        heuristic_fn=estimate,
        algorithm_name=Algorithm.ASTAR,
        with_trace=with_trace
    )