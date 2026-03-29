from __future__ import annotations

from urllib.error import HTTPError, URLError

from mitmproxy import ctx, http

from capture_common import send_flow_to_backend

class CaptureAddon:
    def response(self, flow: http.HTTPFlow) -> None:
        try:
            send_flow_to_backend(flow)
        except HTTPError as e:
            ctx.log.error(f"mitm capture HTTP error: {e}")
        except URLError as e:
            ctx.log.error(f"mitm capture URL error: {e}")
        except Exception as e:
            ctx.log.error(f"mitm capture error: {e}")


addons = [CaptureAddon()]
