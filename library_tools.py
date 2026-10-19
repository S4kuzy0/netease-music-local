"""Complete, ordered library reads for the local NetEase MCP adapter."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import server as upstream


def list_playlists(limit: int = 100, offset: int = 0) -> dict[str, Any]:
    limit = upstream._bounded_int(limit, "limit", 1, 100)
    offset = upstream._non_negative_int(offset, "offset")
    uid = upstream.get_uid()
    response = upstream.netease_request(
        f"https://music.163.com/api/user/playlist?uid={uid}&limit={limit}&offset={offset}"
    )
    upstream._raise_for_upstream_code(response, "Playlist listing failed.")
    items = response.get("playlist")
    if not isinstance(items, list):
        raise upstream.NetEaseError("Playlist listing returned no usable list.")
    return {
        "user_id": uid,
        "playlists": [
            {
                "playlist_id": item.get("id"),
                "name": item.get("name"),
                "track_count": item.get("trackCount"),
                "special_type": item.get("specialType"),
                "owned": (item.get("creator") or {}).get("userId") == uid,
            }
            for item in items
        ],
        "pagination": {
            "offset": offset,
            "returned": len(items),
            "has_next": bool(response.get("more")),
            "next_offset": offset + len(items) if response.get("more") and items else None,
        },
    }


def liked_playlist() -> dict[str, Any]:
    offset = 0
    for _ in range(100):
        page = list_playlists(offset=offset)
        matches = [
            item for item in page["playlists"]
            if item["owned"] and item["special_type"] == 5
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise upstream.NetEaseError("Multiple liked playlists were returned; identification is ambiguous.")
        offset = page["pagination"]["next_offset"]
        if offset is None:
            break
    raise upstream.NetEaseError("Could not identify an owned specialType=5 liked playlist.")


def playlist_snapshot(playlist_id: int) -> tuple[dict[str, Any], list[int], int]:
    playlist_id = upstream._positive_int(playlist_id, "playlist_id")
    playlist = upstream._playlist_detail(playlist_id)
    ids, total = upstream._playlist_track_ids(playlist)
    if len(set(ids)) != len(ids):
        raise upstream.NetEaseError("Playlist contains duplicate IDs; a complete ordered snapshot is ambiguous.")
    return playlist, ids, total


def read_playlist(playlist_id: int, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    limit = upstream._bounded_int(limit, "limit", 1, 500)
    offset = upstream._non_negative_int(offset, "offset")
    playlist, ids, total = playlist_snapshot(playlist_id)
    page_ids = ids[offset:offset + limit]
    records = []
    for start in range(0, len(page_ids), 50):
        records.extend(upstream._fetch_song_records(page_ids[start:start + 50]))
    by_id = {record["id"]: record for record in records}
    songs = [
        {
            "position": offset + index,
            "song_id": song_id,
            "found": song_id in by_id,
            **(upstream._song_summary(by_id[song_id]) if song_id in by_id else {}),
        }
        for index, song_id in enumerate(page_ids, 1)
    ]
    next_offset = offset + len(page_ids)
    snapshot = hashlib.sha256(json.dumps([playlist_id, ids]).encode()).hexdigest()
    return {
        "record_type": "ordered_playlist_snapshot",
        "playlist": {"playlist_id": playlist_id, "name": playlist.get("name"), "total_tracks": total},
        "snapshot_id": snapshot,
        "order_basis": "upstream_playlist_trackIds",
        "chronological_order_verified": False,
        "liked_at_timestamps_available": False,
        "selected_song_ids": page_ids,
        "songs": songs,
        "missing_song_ids": [song_id for song_id in page_ids if song_id not in by_id],
        "pagination": {
            "offset": offset, "limit": limit, "selected": len(page_ids),
            "found": len(by_id), "has_next": next_offset < total,
            "next_offset": next_offset if next_offset < total else None,
        },
    }


def get_liked_songs(limit: int = 100, offset: int = 0) -> dict[str, Any]:
    target = liked_playlist()
    result = read_playlist(target["playlist_id"], limit, offset)
    result["record_type"] = "liked_song_snapshot"
    result["liked_playlist_identification"] = "owned_specialType_5"
    result["order_note"] = (
        "Preserves the server's liked-playlist order. Exact like timestamps and manual "
        "reordering are not inferred. Do not sort by song ID or release date."
    )
    return result


def check_liked_song_ids(song_ids: list[int]) -> dict[str, Any]:
    if not isinstance(song_ids, list) or not 1 <= len(song_ids) <= 500:
        raise ValueError("song_ids must contain 1 to 500 IDs.")
    checked = [upstream._positive_int(value, "song_id") for value in song_ids]
    target = liked_playlist()
    _, ids, total = playlist_snapshot(target["playlist_id"])
    membership = set(ids)
    return {
        "total_liked": total,
        "checks": [{"song_id": song_id, "liked": song_id in membership} for song_id in checked],
    }
