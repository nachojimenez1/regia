"""Tests de A*, Dijkstra, costes y heurística. Responsable: persona 2."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from core.contracts import (
    Algorithm,
    Context,
    Edge,
    EdgeKind,
    Graph,
    Incident,
    IncidentKind,
    LineInfo,
    Profile,
    RouteRequest,
    StationInfo,
    Weather,
)
from routing.astar import find_route as astar_find_route
from routing.costs import edge_cost
from routing.dijkstra import find_route as dijkstra_find_route
from routing.heuristics import estimate


def build_mock_graph() -> Graph:
    """Grafo pequeño de 5 estaciones y 6 nodos con transbordo en 'b' (L1 <-> L2)."""
    stations = {
        "a": StationInfo(
            id="a",
            name="Estación A",
            lat=25.6800,
            lon=-100.3200,
            line_ids=("L1",),
            underground=False,
            has_elevator=True,
        ),
        "b": StationInfo(
            id="b",
            name="Estación B (Transbordo)",
            lat=25.6850,
            lon=-100.3150,
            line_ids=("L1", "L2"),
            underground=True,
            has_elevator=True,
        ),
        "c": StationInfo(
            id="c",
            name="Estación C",
            lat=25.6900,
            lon=-100.3100,
            line_ids=("L1",),
            underground=False,
            has_elevator=False,
        ),
        "d": StationInfo(
            id="d",
            name="Estación D",
            lat=25.6820,
            lon=-100.3120,
            line_ids=("L2",),
            underground=False,
            has_elevator=True,
        ),
        "e": StationInfo(
            id="e",
            name="Estación E",
            lat=25.6880,
            lon=-100.3180,
            line_ids=("L2",),
            underground=False,
            has_elevator=True,
        ),
    }

    lines = {
        "L1": LineInfo(id="L1", name="Línea 1", color="#F5A623", station_ids=("a", "b", "c")),
        "L2": LineInfo(id="L2", name="Línea 2", color="#1D3557", station_ids=("d", "b", "e")),
    }

    edges = {
        ("a", "L1"): [
            Edge(source=("a", "L1"), target=("b", "L1"), kind=EdgeKind.RIDE, minutes=3.0, meters=1000.0),
        ],
        ("b", "L1"): [
            Edge(source=("b", "L1"), target=("a", "L1"), kind=EdgeKind.RIDE, minutes=3.0, meters=1000.0),
            Edge(source=("b", "L1"), target=("c", "L1"), kind=EdgeKind.RIDE, minutes=4.0, meters=1200.0),
            Edge(source=("b", "L1"), target=("b", "L2"), kind=EdgeKind.TRANSFER, minutes=2.0, meters=150.0),
        ],
        ("c", "L1"): [
            Edge(source=("c", "L1"), target=("b", "L1"), kind=EdgeKind.RIDE, minutes=4.0, meters=1200.0),
        ],
        ("d", "L2"): [
            Edge(source=("d", "L2"), target=("b", "L2"), kind=EdgeKind.RIDE, minutes=2.0, meters=800.0),
        ],
        ("b", "L2"): [
            Edge(source=("b", "L2"), target=("d", "L2"), kind=EdgeKind.RIDE, minutes=2.0, meters=800.0),
            Edge(source=("b", "L2"), target=("e", "L2"), kind=EdgeKind.RIDE, minutes=3.0, meters=900.0),
            Edge(source=("b", "L2"), target=("b", "L1"), kind=EdgeKind.TRANSFER, minutes=2.0, meters=150.0),
        ],
        ("e", "L2"): [
            Edge(source=("e", "L2"), target=("b", "L2"), kind=EdgeKind.RIDE, minutes=3.0, meters=900.0),
        ],
    }

    return Graph(stations=stations, lines=lines, edges=edges)


def build_alternative_graph() -> Graph:
    """Grafo con dos caminos de 's1' a 's4':
    - Atajo con transbordo en 's2' pasando por 's5' (sin ascensor): 11 min reales.
    - Camino directo en L1 pasando por 's3' (con ascensor): 14 min reales.
    """
    stations = {
        "s1": StationInfo("s1", "S1", 25.6800, -100.3200, ("L1",), False, True),
        "s2": StationInfo("s2", "S2", 25.6820, -100.3180, ("L1", "L2"), False, True),
        "s3": StationInfo("s3", "S3", 25.6850, -100.3150, ("L1",), False, True),
        "s4": StationInfo("s4", "S4", 25.6880, -100.3150, ("L1", "L2"), False, True),
        "s5": StationInfo("s5", "S5", 25.6850, -100.3180, ("L2",), False, False),
    }

    lines = {
        "L1": LineInfo("L1", "Línea 1", "#F5A623", ("s1", "s2", "s3", "s4")),
        "L2": LineInfo("L2", "Línea 2", "#1D3557", ("s2", "s5", "s4")),
    }

    edges = {
        ("s1", "L1"): [
            Edge(("s1", "L1"), ("s2", "L1"), EdgeKind.RIDE, 2.0, 500.0),
        ],
        ("s2", "L1"): [
            Edge(("s2", "L1"), ("s1", "L1"), EdgeKind.RIDE, 2.0, 500.0),
            Edge(("s2", "L1"), ("s3", "L1"), EdgeKind.RIDE, 8.0, 900.0),
            Edge(("s2", "L1"), ("s2", "L2"), EdgeKind.TRANSFER, 1.0, 80.0),
        ],
        ("s3", "L1"): [
            Edge(("s3", "L1"), ("s2", "L1"), EdgeKind.RIDE, 8.0, 900.0),
            Edge(("s3", "L1"), ("s4", "L1"), EdgeKind.RIDE, 2.0, 500.0),
        ],
        ("s4", "L1"): [
            Edge(("s4", "L1"), ("s3", "L1"), EdgeKind.RIDE, 2.0, 500.0),
            Edge(("s4", "L1"), ("s4", "L2"), EdgeKind.TRANSFER, 1.0, 80.0),
        ],
        ("s2", "L2"): [
            Edge(("s2", "L2"), ("s2", "L1"), EdgeKind.TRANSFER, 1.0, 80.0),
            Edge(("s2", "L2"), ("s5", "L2"), EdgeKind.RIDE, 2.0, 500.0),
        ],
        ("s5", "L2"): [
            Edge(("s5", "L2"), ("s2", "L2"), EdgeKind.RIDE, 2.0, 500.0),
            Edge(("s5", "L2"), ("s4", "L2"), EdgeKind.RIDE, 2.0, 600.0),
        ],
        ("s4", "L2"): [
            Edge(("s4", "L2"), ("s5", "L2"), EdgeKind.RIDE, 2.0, 600.0),
            Edge(("s4", "L2"), ("s4", "L1"), EdgeKind.TRANSFER, 1.0, 80.0),
        ],
    }

    return Graph(stations=stations, lines=lines, edges=edges)


def build_mock_context(
    service_open: bool = True,
    weather: Weather | None = None,
    incidents: tuple[Incident, ...] = (),
) -> Context:
    """Contexto fijo de prueba en hora de Monterrey."""
    tz = ZoneInfo("America/Monterrey")
    when = datetime(2026, 11, 20, 8, 30, tzinfo=tz)
    return Context(
        when=when,
        service_open=service_open,
        headways={"L1": 4.0, "L2": 4.0},
        weather=weather,
        incidents=incidents,
    )


class TestRouting(unittest.TestCase):
    def setUp(self):
        self.graph = build_mock_graph()
        self.alt_graph = build_alternative_graph()
        self.context = build_mock_context()

    def test_origen_igual_a_destino(self):
        """Origen == destino devuelve 1 paso y coste 0.0."""
        request = RouteRequest(origin="a", destination="a", when=self.context.when)
        result = astar_find_route(self.graph, request, self.context)

        self.assertTrue(result.found)
        self.assertEqual(result.total_minutes, 0.0)
        self.assertEqual(result.transfers, 0)
        self.assertEqual(len(result.steps), 1)
        self.assertEqual(result.steps[0].station_id, "a")
        self.assertEqual(result.steps[0].minutes, 0.0)
        self.assertEqual(result.trace, ())

    def test_ruta_calculada_a_mano_y_tiempos_acumulados(self):
        """De 'a' a 'e': espera L1 (2) + a->b (3) + transbordo (2+2) + b->e (3) = 12.0 min."""
        request = RouteRequest(origin="a", destination="e", when=self.context.when)
        result = astar_find_route(self.graph, request, self.context, with_trace=True)

        self.assertTrue(result.found)
        self.assertEqual(result.algorithm, Algorithm.ASTAR)
        self.assertAlmostEqual(result.total_minutes, 12.0)
        self.assertEqual(result.transfers, 1)
        self.assertEqual(
            [(s.station_id, s.line_id, s.minutes) for s in result.steps],
            [
                ("a", "L1", 0.0),
                ("b", "L1", 5.0),
                ("b", "L2", 9.0),
                ("e", "L2", 12.0),
            ],
        )
        self.assertEqual(len(result.trace), result.nodes_expanded)

    def test_ruta_hacia_el_oeste_haversine(self):
        """Ir de 'e' a 'a' (lon destino < lon origen) no debe fallar en Haversine."""
        request = RouteRequest(origin="e", destination="a", when=self.context.when)
        result = astar_find_route(self.graph, request, self.context)

        self.assertTrue(result.found)
        self.assertAlmostEqual(result.total_minutes, 12.0)
        self.assertEqual(result.transfers, 1)

    def test_astar_vs_dijkstra(self):
        """A* y Dijkstra devuelven el mismo coste y A* expande <= nodos."""
        request = RouteRequest(origin="a", destination="e", when=self.context.when)
        res_astar = astar_find_route(self.graph, request, self.context)
        res_dijkstra = dijkstra_find_route(self.graph, request, self.context)

        self.assertTrue(res_astar.found)
        self.assertTrue(res_dijkstra.found)
        self.assertEqual(res_dijkstra.algorithm, Algorithm.DIJKSTRA)
        self.assertAlmostEqual(res_astar.total_minutes, res_dijkstra.total_minutes)
        self.assertLessEqual(res_astar.nodes_expanded, res_dijkstra.nodes_expanded)

    def test_heuristica_admisible_y_consistente(self):
        """h(n) <= coste real restante y h(u) <= coste(u, v) + h(v) en todas las aristas."""
        for graph in (self.graph, self.alt_graph):
            station_ids = list(graph.stations.keys())
            for dest in station_ids:
                # Consistencia en cada arista
                for node, edges in graph.edges.items():
                    h_u = estimate(graph, node, dest)
                    self.assertGreaterEqual(h_u, 0.0)
                    for edge in edges:
                        c_uv = edge_cost(edge, self.context, Profile.FASTEST, graph)
                        h_v = estimate(graph, edge.target, dest)
                        self.assertLessEqual(h_u, c_uv + h_v + 1e-9)

                # Admisibilidad frente a la ruta óptima real
                for orig in station_ids:
                    req = RouteRequest(origin=orig, destination=dest)
                    res = dijkstra_find_route(graph, req, self.context)
                    if res.found:
                        for node in graph.edges:
                            if node[0] == orig:
                                h_val = estimate(graph, node, dest)
                                self.assertLessEqual(h_val, res.total_minutes + 1e-9)

    def test_estacion_cerrada_sin_alternativa(self):
        """Si la única estación de paso está cerrada, found es False."""
        incident = Incident(
            kind=IncidentKind.STATION_CLOSED,
            station_id="b",
            line_id=None,
            extra_minutes=0.0,
            description="Estación B cerrada",
        )
        ctx = build_mock_context(incidents=(incident,))
        request = RouteRequest(origin="a", destination="e")
        result = astar_find_route(self.graph, request, ctx)

        self.assertFalse(result.found)
        self.assertEqual(result.steps, ())

    def test_estacion_cerrada_con_alternativa(self):
        """Si hay ruta alternativa, la búsqueda evita la estación cerrada."""
        incident = Incident(
            kind=IncidentKind.STATION_CLOSED,
            station_id="s5",
            line_id=None,
            extra_minutes=0.0,
            description="Estación S5 cerrada",
        )
        ctx = build_mock_context(incidents=(incident,))
        request = RouteRequest(origin="s1", destination="s4", profile=Profile.FASTEST)
        result = astar_find_route(self.alt_graph, request, ctx)

        self.assertTrue(result.found)
        visited = [step.station_id for step in result.steps]
        self.assertNotIn("s5", visited)
        self.assertIn("s3", visited)
        self.assertAlmostEqual(result.total_minutes, 14.0)

    def test_perfil_accessible_evita_estaciones_sin_ascensor(self):
        """Con Profile.ACCESSIBLE se evita 's5' (sin ascensor) y se usa 's3'."""
        req_fastest = RouteRequest(origin="s1", destination="s4", profile=Profile.FASTEST)
        res_fastest = astar_find_route(self.alt_graph, req_fastest, self.context)
        self.assertIn("s5", [s.station_id for s in res_fastest.steps])

        req_acc = RouteRequest(origin="s1", destination="s4", profile=Profile.ACCESSIBLE)
        res_acc = astar_find_route(self.alt_graph, req_acc, self.context)
        self.assertTrue(res_acc.found)
        self.assertNotIn("s5", [s.station_id for s in res_acc.steps])
        self.assertEqual(res_acc.transfers, 0)

        # Destino sin ascensor -> found=False
        req_no_elev = RouteRequest(origin="a", destination="c", profile=Profile.ACCESSIBLE)
        res_no_elev = astar_find_route(self.graph, req_no_elev, self.context)
        self.assertFalse(res_no_elev.found)

    def test_perfil_fewest_transfers_evita_transbordo(self):
        """Con Profile.FEWEST_TRANSFERS elige la ruta directa en L1 sin inflar total_minutes."""
        req = RouteRequest(origin="s1", destination="s4", profile=Profile.FEWEST_TRANSFERS)
        res = astar_find_route(self.alt_graph, req, self.context)

        self.assertTrue(res.found)
        self.assertEqual(res.transfers, 0)
        self.assertAlmostEqual(res.total_minutes, 14.0)

    def test_retraso_de_linea_se_aplica_una_vez_por_linea(self):
        """Un LINE_DELAY de 5 min en L1 suma 5 min totales, no 5 min por cada tramo."""
        delay = Incident(
            kind=IncidentKind.LINE_DELAY,
            station_id=None,
            line_id="L1",
            extra_minutes=5.0,
            description="Retraso en L1",
        )
        ctx = build_mock_context(incidents=(delay,))
        # a -> b (3) -> c (4) + espera L1 (2) + retraso L1 (5) = 14.0 min
        res = astar_find_route(self.graph, RouteRequest(origin="a", destination="c"), ctx)

        self.assertTrue(res.found)
        self.assertAlmostEqual(res.total_minutes, 14.0)

    def test_lluvia_penaliza_transbordo_en_superficie_sin_romper_admisibilidad(self):
        """Con lluvia en estación no subterránea, el coste del transbordo aumenta."""
        rain_ctx = build_mock_context(
            weather=Weather(temperature_c=22.0, precipitation_mm=8.0, is_raining=True)
        )
        surface_transfer = Edge(("s2", "L1"), ("s2", "L2"), EdgeKind.TRANSFER, 1.0, 80.0)
        dry_cost = edge_cost(surface_transfer, self.context, Profile.FASTEST, self.alt_graph)
        rain_cost = edge_cost(surface_transfer, rain_ctx, Profile.FASTEST, self.alt_graph)

        self.assertGreater(rain_cost, dry_cost)
        self.assertGreaterEqual(rain_cost, surface_transfer.minutes)

    def test_servicio_cerrado_devuelve_found_false(self):
        """Si service_open es False, devuelve found=False sin lanzar excepción."""
        closed_ctx = build_mock_context(service_open=False)
        res = astar_find_route(self.graph, RouteRequest(origin="a", destination="e"), closed_ctx)

        self.assertFalse(res.found)
        self.assertEqual(res.steps, ())

    def test_estacion_inexistente_lanza_value_error(self):
        """IDs que no están en el grafo deben levantar ValueError."""
        req = RouteRequest(origin="inexistente", destination="a")
        with self.assertRaises(ValueError):
            astar_find_route(self.graph, req, self.context)

    def test_sin_traza_devuelve_tupla_vacia(self):
        """Si with_trace es False, trace debe ser una tupla vacía."""
        req = RouteRequest(origin="a", destination="e")
        res = astar_find_route(self.graph, req, self.context, with_trace=False)
        self.assertEqual(res.trace, ())


if __name__ == "__main__":
    unittest.main()