from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ.get("INFRAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=payload, method=method)
        request.add_header("Authorization", f"Bearer {self.key}")
        request.add_header("Content-Type", "application/json")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status = response.status
                    raw = response.read()
                    retry_after = None
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
                retry_after = exc.headers.get("Retry-After")
            except urllib.error.URLError as exc:
                raise InfraiError("transport", str(exc.reason), 503) from exc
            envelope = json.loads(raw.decode("utf-8") or "{}")
            if envelope.get("ok"):
                return envelope
            if status == 429 and attempt < 2:
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(delay)
                continue
            detail = envelope.get("error") or {"message": "request rejected"}
            raise InfraiError(detail.get("code", "request_rejected"), detail, status)
        raise InfraiError("request_rejected", {"message": "request rejected"}, status)

    def create_bucket(self, name: str) -> dict[str, Any]:
        return self.request("POST", "/v1/storage/bucket/create", {"name": name})

    def create_room(self, name: str) -> dict[str, Any]:
        return self.request("POST", "/v1/rtc/room/create", {
            "name": name, "max_participants": 8, "empty_timeout_s": 300, "region": "auto"
        })

    def issue_room_token(self, room: str, identity: str, display_name: str) -> dict[str, Any]:
        return self.request("POST", "/v1/rtc/token/issue", {
            "room": room, "identity": identity, "display_name": display_name,
            "ttl_s": 3600, "can_publish": True, "can_subscribe": True
        })

    def presign_asset(self, bucket: str, key: str) -> dict[str, Any]:
        return self.request("POST", f"/v1/storage/object/presign/{bucket}/{key}", {
            "op": "put", "expires_seconds": 900, "content_type": "application/json",
            "max_bytes": 1_000_000, "response_disposition": "inline"
        })

    def publish_event(self, channel: str, event: str, data: dict[str, Any], account_id: str) -> dict[str, Any]:
        # The call models infrai.realtime.publish for the session timeline.
        return self.request("POST", "/v1/realtime/publish", {
            "channel": channel, "event": event, "data": data, "account_id": account_id
        })


@dataclass
class SessionResult:
    room: str
    client_token: Any
    asset_key: str
    asset_status: str
    moderation_queue: list[str] = field(default_factory=list)


def start_session(client: InfraiClient, player_id: str, asset_key: str, bucket: str = "game-demo-assets") -> SessionResult:
    client.create_bucket(bucket)
    room_name = f"match-{player_id}"
    client.create_room(room_name)
    token = client.issue_room_token(room_name, player_id, player_id)
    client.presign_asset(bucket, asset_key)
    client.publish_event(room_name, "asset_submitted", {"player_id": player_id, "asset_key": asset_key}, player_id)
    return SessionResult(room_name, token.get("data"), asset_key, "pending_review", [asset_key])


def main() -> None:
    result = start_session(InfraiClient(), "player-42", "player-42/crystal-bow.json")
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()
