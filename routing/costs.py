from core.contracts import Edge, EdgeKind, Context, Profile, IncidentKind, Graph

PENALTY_TRANSFER = 8.0
PENALTY_RAIN = 3.0
DEFAULT_HEADWAY_MINUTES = 4.0
PENALTY_HEAT = 1.5
EXTREME_HEAT_C = 38.0


def line_delay(line_id: str, context: Context) -> float:
    return sum(
        incident.extra_minutes
        for incident in context.incidents
            if incident.kind == IncidentKind.LINE_DELAY and incident.line_id == line_id
    )

def is_station_blocked(station_id: str, context: Context, profile: Profile, graph: Graph | None = None) -> bool:
    for incident in context.incidents:
        if incident.kind == IncidentKind.STATION_CLOSED and incident.station_id == station_id:
            return True

    if profile == Profile.ACCESSIBLE and graph is not None:
        station_info = graph.stations.get(station_id)
        if station_info is not None and not station_info.has_elevator:
            return True
    return False

def initial_wait(line_id: str, context: Context) -> float:
    return (context.headways.get(line_id, DEFAULT_HEADWAY_MINUTES) / 2.0) + line_delay(line_id, context)


def real_edge_minutes(edge: Edge, context: Context) -> float:
    minutes = edge.minutes
    if edge.kind == EdgeKind.TRANSFER:
        _, target_line = edge.target
        headway = context.headways.get(target_line, DEFAULT_HEADWAY_MINUTES)
        minutes += (headway / 2.0) + line_delay(target_line, context)
    return minutes


def edge_cost(edge: Edge, context: Context, profile: Profile, graph: Graph | None = None) -> float:
    source_station, source_line = edge.source
    target_station, target_line = edge.target

    if is_station_blocked(source_station, context, profile, graph) or is_station_blocked(target_station, context, profile, graph):
        return float("inf")

    cost = real_edge_minutes(edge, context)

    if edge.kind == EdgeKind.TRANSFER:
        if profile == Profile.FEWEST_TRANSFERS:
            cost += PENALTY_TRANSFER
        if context.weather is not None:
            station_info = graph.stations.get(target_station) if graph is not None else None
            is_underground = station_info.underground if station_info is not None else False
            if not is_underground:
                if context.weather.is_raining:
                    cost += PENALTY_RAIN
                if context.weather.temperature_c >= EXTREME_HEAT_C:
                    cost += PENALTY_HEAT

    return max(edge.minutes, cost)