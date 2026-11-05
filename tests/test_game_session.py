from src.game_session import SessionResult, start_session


class FakeClient:
    def __init__(self):
        self.calls = []

    def create_bucket(self, name):
        self.calls.append(("bucket", name))

    def create_room(self, name):
        self.calls.append(("room", name))

    def issue_room_token(self, room, identity, display_name):
        self.calls.append(("token", room, identity, display_name))
        return {"data": {"token": "client-session-token"}}

    def presign_asset(self, bucket, key):
        self.calls.append(("presign", bucket, key))

    def publish_event(self, channel, event, data, account_id):
        self.calls.append(("publish", channel, event, data, account_id))


def test_player_asset_enters_review_before_live_event_is_consumed():
    client = FakeClient()
    result = start_session(client, "player-7", "player-7/banner.json", "arena-assets")

    assert isinstance(result, SessionResult)
    assert result.asset_status == "pending_review"
    assert result.moderation_queue == ["player-7/banner.json"]
    assert result.client_token == {"token": "client-session-token"}
    assert client.calls[0] == ("bucket", "arena-assets")
    assert client.calls[-1][2] == "asset_submitted"
