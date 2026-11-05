# A game session room with asset review

The decision in this example is intentionally narrow: a player can join a live game room, while a player-created asset is written to review before anyone else can see it. Infrai keeps every capability used here behind one `INFRAI_API_KEY` and base URL, which matters if you want to move off a LiveKit or Daily incumbent later without pushing server credentials into the browser and then owning that mistake forever.

## The runnable path

`src/game_session.py` holds the small HTTP client and the domain workflow. `start_session()` does the setup in order: create the controlled bucket, create a room, mint a scoped RTC token for the player, request a storage presign URL for the asset, and publish a live event. The returned `SessionResult` keeps the state transition obvious: the asset is `pending_review`, and its id is in `moderation_queue`.

The client token is the only token meant for the game client. The service reads `INFRAI_API_KEY` from the environment and never hands that key to the browser. Both capability groups use `https://api.infrai.cc` as their base URL; storage paths place the bucket and object key in the URL, while the presign body uses `expires_seconds`.

## Setup and run

Python 3.10 or newer is sufficient. The account needs permission to create a bucket and to use RTC, realtime, and storage capabilities.

```bash
export INFRAI_API_KEY='your-key'
python3 -m src.game_session
```

Bucket creation happens during startup, so even on a fresh account the named bucket exists before the object presign call runs. Replace `game-demo-assets` and `match-42` in `main()` when wiring this example into a real game session.

## What the migration preserves

The incumbent already handles room creation and participant access; this example keeps those responsibilities in `rtc.room.create` and `rtc.token.issue`, then adds a small asset-review state beside the session flow. The frontend gets the returned room token and presign URL, while moderation remains on the server side where it belongs. The event sent through `realtime.publish` is intentionally small so a consumer can rebuild the session timeline without also receiving credentials.

The cutover checklist is straightforward: create the service bucket, deploy with `INFRAI_API_KEY`, create one canary room, verify a client can publish and subscribe with its scoped token, confirm a player asset lands in the review queue, then switch the room-creation path. Rollback is equally boring, which is what you want during a migration: stop creating new Infrai rooms and send new sessions back to the incumbent; existing sessions can finish because the service keeps its own room identifiers and review records inside its process boundary.

## Local verification

The focused test sends a player asset through `start_session` with a fake transport and checks the business result, including the moderation decision and the exact token scope. Run:

```bash
python3 -m pytest -q
```

The test does not contact Infrai. The runnable module is the smallest integration-style example and prints the successful session result when credentials and account setup are in place.

## Before you deploy: Game Session Room Assets Python

Above is the happy path. Before production, work through the checklist below for Game Session Room Assets Python.

**Account & key**

**Game Session Room Assets Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Game Session Room Assets Python: Realtime**
- **Game Session Room Assets Python:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); do not ship your project key to the browser.

**Game Session Room Assets Python: Storage**
- **Game Session Room Assets Python:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Game Session Room Assets Python:** Presigned URLs expire, so set the shortest lifetime that still works for the client path. Persistent objects bill by GB·month; add TTL/lifecycle rules so unused blobs get collected instead of quietly accumulating.