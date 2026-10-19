"""Regressions for complete snapshots, missing positions and recommendation exclusion."""

import unittest
import tempfile
import time
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from unittest import mock

import library_tools as library
from netease_session import SessionManager
from persistence import PersistentStore


def song(song_id):
    return {"id": song_id, "name": f"Song {song_id}", "ar": [], "al": {}}


class LibraryTests(unittest.TestCase):
    def test_playlist_lookup_bounds_embedded_tracks_without_losing_full_ids(self):
        ids = list(range(1, 4269))
        playlist = {"trackCount": len(ids), "trackIds": [{"id": i} for i in ids]}
        with mock.patch.object(library.upstream, "netease_request", return_value={"code": 200, "playlist": playlist}) as request:
            result = library.upstream._playlist_detail(4)
        query = parse_qs(urlparse(request.call_args.args[0]).query)
        self.assertEqual(query["n"], ["1"])
        self.assertEqual(library.upstream._playlist_track_ids(result), (ids, len(ids)))

    def test_loopback_login_loads_official_challenge_over_https(self):
        login_id = "synthetic-login-attempt-1234"
        attempt = {"created_monotonic": time.monotonic(), "qr_payload": "https://music.163.com/test"}
        with mock.patch.dict(library.upstream.QR_LOGIN_ATTEMPTS, {login_id: attempt}, clear=True):
            page = library.upstream._qr_login_page(login_id)
        self.assertIn("protocol:'https'", page)

    def test_process_refresh_observes_login_saved_by_another_process(self):
        with tempfile.TemporaryDirectory() as folder:
            store = PersistentStore(str(Path(folder) / "session.sqlite3"))
            reader = SessionManager(lambda: store, "")
            writer = SessionManager(lambda: store, "")
            self.assertIsNone(reader.current())
            writer.save("MUSIC_U=synthetic; __csrf=synthetic", source="qr_login")
            reader.refresh_from_storage()
            self.assertEqual(reader.current()["source"], "qr_login")

    def test_500_entry_snapshot_retains_missing_position_and_server_order(self):
        ids = list(range(900, 400, -1))
        playlist = {"id": 4, "name": "Likes", "trackIds": [{"id": value} for value in ids], "trackCount": 500}
        def fetch(selected):
            return [song(value) for value in reversed(selected) if value != 880]
        with mock.patch.object(library.upstream, "_playlist_detail", return_value=playlist), mock.patch.object(library.upstream, "_fetch_song_records", side_effect=fetch) as network:
            result = library.read_playlist(4, 500)
        self.assertEqual(network.call_count, 10)
        self.assertEqual([item["song_id"] for item in result["songs"]], ids)
        self.assertEqual(result["songs"][20], {"position": 21, "song_id": 880, "found": False})
        self.assertEqual(result["missing_song_ids"], [880])
        self.assertEqual(result["pagination"]["found"], 499)
        self.assertFalse(result["chronological_order_verified"])

    def test_liked_playlist_uses_owned_special_type_after_first_page(self):
        pages = [
            {"playlists": [{"playlist_id": 3, "name": "我喜欢的音乐", "owned": False, "special_type": 5}], "pagination": {"next_offset": 100}},
            {"playlists": [{"playlist_id": 9, "name": "Custom name", "owned": True, "special_type": 5}], "pagination": {"next_offset": None}},
        ]
        with mock.patch.object(library, "list_playlists", side_effect=pages):
            self.assertEqual(library.liked_playlist()["playlist_id"], 9)

    def test_recommendation_exclusion_checks_likes_beyond_recent_500(self):
        with mock.patch.object(library, "liked_playlist", return_value={"playlist_id": 4}), mock.patch.object(library, "playlist_snapshot", return_value=({}, list(range(1, 901)), 900)):
            result = library.check_liked_song_ids([900, 1000])
        self.assertEqual(result["checks"], [{"song_id": 900, "liked": True}, {"song_id": 1000, "liked": False}])

    def test_incomplete_track_id_list_cannot_be_reported_as_full(self):
        playlist = {"trackIds": [{"id": 4}], "trackCount": 500}
        with mock.patch.object(library.upstream, "_playlist_detail", return_value=playlist):
            with self.assertRaises(library.upstream.NetEaseError):
                library.read_playlist(4, 500)

    def test_ambiguous_liked_playlist_identification_fails(self):
        page = {"playlists": [{"owned": True, "special_type": 5}, {"owned": True, "special_type": 5}], "pagination": {"next_offset": None}}
        with mock.patch.object(library, "list_playlists", return_value=page):
            with self.assertRaises(library.upstream.NetEaseError):
                library.liked_playlist()


if __name__ == "__main__":
    unittest.main()
