"""
Lightweight Built-In Monitoring Server & Local Telemetry Ingestion Receiver.
Uses Python standard library http.server for zero-dependency execution.
"""

import json
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

logger = logging.getLogger("TelemetryServer")


class TelemetryState:
    """Thread-safe telemetry state container."""
    def __init__(self):
        self._lock = threading.Lock()
        self.latest_packet: Optional[Dict[str, Any]] = None
        self.received_telemetry_history = []
        self.gateway_stats: Dict[str, Any] = {}
        self.start_time = time.time()

    def update_latest(self, packet: Dict[str, Any]):
        with self._lock:
            self.latest_packet = packet

    def record_received(self, data: Dict[str, Any]):
        with self._lock:
            self.received_telemetry_history.append({
                "received_at": time.time(),
                "data": data
            })
            if len(self.received_telemetry_history) > 50:
                self.received_telemetry_history.pop(0)

    def update_gateway_stats(self, stats: Dict[str, Any]):
        with self._lock:
            self.gateway_stats = stats

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "latest": self.latest_packet,
                "history_count": len(self.received_telemetry_history),
                "gateway_stats": self.gateway_stats,
                "uptime_sec": round(time.time() - self.start_time, 1)
            }


# Global shared state instance
global_telemetry_state = TelemetryState()


class TelemetryHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for telemetry monitoring and receiver endpoints."""

    def log_message(self, format, *args):
        # Silence routine access logs in console
        return

    def _set_json_headers(self, status_code: int = 200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_json_headers(200)

    def do_GET(self):
        if self.path == "/api/v1/health":
            self._set_json_headers(200)
            snap = global_telemetry_state.get_snapshot()
            response = {
                "status": "UP",
                "service": "python-arduino-serial-sensor-telemetry-microservice",
                "uptime_sec": snap["uptime_sec"]
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif self.path == "/api/v1/telemetry/latest":
            self._set_json_headers(200)
            snap = global_telemetry_state.get_snapshot()
            response = {
                "status": "success",
                "latest_telemetry": snap["latest"]
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif self.path == "/api/v1/metrics":
            self._set_json_headers(200)
            snap = global_telemetry_state.get_snapshot()
            self.wfile.write(json.dumps({
                "status": "success",
                "metrics": snap["gateway_stats"],
                "uptime_sec": snap["uptime_sec"]
            }).encode("utf-8"))

        elif self.path == "/" or self.path.startswith("/dashboard"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = self._render_dashboard_html()
            self.wfile.write(html.encode("utf-8"))

        else:
            self._set_json_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

    def do_POST(self):
        if self.path in ("/api/v1/telemetry", "/Incubadora/Service.php"):
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            content_type = self.headers.get("Content-Type", "")

            parsed_data = {}
            if "application/json" in content_type:
                try:
                    parsed_data = json.loads(body_bytes.decode("utf-8"))
                except Exception as e:
                    logger.error("JSON parse error: %s", e)
            else:
                # Handle URL-encoded form data (e.g. Dato=17.69,4.23...)
                from urllib.parse import parse_qs
                parsed_qs = parse_qs(body_bytes.decode("utf-8"))
                parsed_data = {k: v[0] if len(v) == 1 else v for k, v in parsed_qs.items()}

            global_telemetry_state.record_received(parsed_data)
            self._set_json_headers(200)
            self.wfile.write(json.dumps({
                "status": "success",
                "message": "Telemetry frame received and registered",
                "recorded_at": time.time()
            }).encode("utf-8"))
        else:
            self._set_json_headers(404)
            self.wfile.write(json.dumps({"error": "Unknown POST endpoint"}).encode("utf-8"))

    def _render_dashboard_html(self) -> str:
        """Renders embedded web dashboard with auto-refresh."""
        return """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Arduino IoT Serial Telemetry Gateway</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/4.6.2/css/bootstrap.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; }
    .card-dark { background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
    .metric-value { font-size: 2rem; font-weight: 700; color: #38bdf8; }
    .badge-sensor { font-size: 0.85rem; padding: 0.4rem 0.8rem; border-radius: 9999px; }
  </style>
</head>
<body class="p-4">
  <div class="container">
    <div class="d-flex justify-content-between align-items-center mb-4 border-bottom border-secondary pb-3">
      <div>
        <h2 class="font-weight-bold text-white mb-0">
          <i class="fas fa-microchip text-primary mr-2"></i> Arduino Serial Telemetry Gateway
        </h2>
        <small class="text-muted">Edge Serial-to-Cloud IoT Microservice</small>
      </div>
      <div>
        <span class="badge badge-success px-3 py-2"><i class="fas fa-satellite-dish mr-1"></i> Gateway Activo</span>
      </div>
    </div>

    <!-- Live Metrics Grid -->
    <div class="row mb-4" id="metricsRow">
      <div class="col-md-3 mb-3">
        <div class="card card-dark p-3 text-center">
          <div class="text-muted small text-uppercase font-weight-bold">Tramas Enviadas</div>
          <div class="metric-value text-success" id="valSent">--</div>
        </div>
      </div>
      <div class="col-md-3 mb-3">
        <div class="card card-dark p-3 text-center">
          <div class="text-muted small text-uppercase font-weight-bold">Cola Offline</div>
          <div class="metric-value text-warning" id="valBuffer">--</div>
        </div>
      </div>
      <div class="col-md-3 mb-3">
        <div class="card card-dark p-3 text-center">
          <div class="text-muted small text-uppercase font-weight-bold">Tramas Fallidas</div>
          <div class="metric-value text-danger" id="valFailed">--</div>
        </div>
      </div>
      <div class="col-md-3 mb-3">
        <div class="card card-dark p-3 text-center">
          <div class="text-muted small text-uppercase font-weight-bold">Uptime Gateway</div>
          <div class="metric-value text-info" id="valUptime">-- s</div>
        </div>
      </div>
    </div>

    <!-- Latest Telemetry Card -->
    <div class="card card-dark p-4 mb-4">
      <h5 class="font-weight-bold text-white mb-3">
        <i class="fas fa-thermometer-half text-warning mr-2"></i> Lecturas de Sensores en Vivo
      </h5>
      <div class="row" id="sensorsGrid">
        <div class="col-12 text-center text-muted py-4">Esperando flujo de tramas de telemetría...</div>
      </div>
      <div class="mt-3 text-right">
        <small class="text-muted" id="lastUpdated">Última actualización: --</small>
      </div>
    </div>
  </div>

  <script>
    async function refreshDashboard() {
      try {
        const resLatest = await fetch('/api/v1/telemetry/latest');
        const jsonLatest = await resLatest.json();
        const latest = jsonLatest.latest_telemetry;

        const resMetrics = await fetch('/api/v1/metrics');
        const jsonMetrics = await resMetrics.json();
        const m = jsonMetrics.metrics || {};

        document.getElementById('valSent').innerText = (m.total_sent || 0).toLocaleString();
        document.getElementById('valBuffer').innerText = (m.buffer_size || 0).toLocaleString();
        document.getElementById('valFailed').innerText = (m.total_failed || 0).toLocaleString();
        document.getElementById('valUptime').innerText = (jsonMetrics.uptime_sec || 0) + 's';

        if (latest && latest.sensors) {
          const grid = document.getElementById('sensorsGrid');
          grid.innerHTML = Object.entries(latest.sensors).map(([key, val]) => `
            <div class="col-md-4 col-sm-6 mb-3">
              <div class="p-3 rounded bg-dark border border-secondary text-center">
                <small class="text-muted text-uppercase">${key.replace(/_/g, ' ')}</small>
                <div class="h4 font-weight-bold text-white mb-0 mt-1">${val}</div>
              </div>
            </div>
          `).join('');
          document.getElementById('lastUpdated').innerText = 'Timestamp: ' + latest.timestamp;
        }
      } catch (e) {
        console.error('Refresh error:', e);
      }
    }
    setInterval(refreshDashboard, 1500);
    refreshDashboard();
  </script>
</body>
</html>"""


def start_telemetry_server(host: str = "0.0.0.0", port: int = 8080) -> HTTPServer:
    """Spawns background HTTP server daemon."""
    server = HTTPServer((host, port), TelemetryHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Monitoring web server running at http://%s:%d/", host, port)
    return server
