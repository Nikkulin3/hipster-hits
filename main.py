import os
import re
import textwrap

from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import json
import segno
from PIL import Image, ImageDraw, ImageFont


class Song:
    QR_SCALE = 10
    IMAGE_SIZE = None

    def __init__(self, track: dict):
        self.data = track

    def save_qr(self, playlist_id, use_cached=True):
        pth = f"cache/{playlist_id}/{self.id}_qr.png"
        if not os.path.exists(pth) or not use_cached:
            qr = segno.make_qr(self.href)
            qr.save(pth, scale=Song.QR_SCALE)

    def save_text(self, playlist_id, use_cached=False):

        def add_text(percent_x, percent_y, text, font_size=20):
            assert 0 <= percent_x <= 1
            assert 0 <= percent_y <= 1
            W, H = Song.IMAGE_SIZE
            _, _, w, h = d.multiline_textbbox(
                (0, 0), text, align="center", font_size=font_size
            )
            x, y = round(percent_x * W), round(percent_y * H)
            x, y = (W - w) / 2 - W / 2 + x, (H - h) / 2 - H / 2 + y

            d.multiline_text(
                (x, y), text, fill=(0, 0, 0), align="center", font_size=font_size
            )

        if Song.IMAGE_SIZE is None:
            with Image.open(f"cache/{playlist_id}/{self.id}_qr.png") as im:
                Song.IMAGE_SIZE = im.size
        img = Image.new("RGB", Song.IMAGE_SIZE, (255, 255, 255))
        d = ImageDraw.Draw(img)
        add_text(0.5, 0.2, self.artist, 20)
        add_text(0.5, 0.47, self.release, 100)
        add_text(0.5, 0.8, self.name, 20)
        add_text(0.5, 0.9, self.album, 15)
        if "Tango" in self.name:
            img.show()  # todo continue at: Wenn sie diesen Tango hört - Remastered 2002 (umlaute, text width)
        img.save(f"cache/{playlist_id}/{self.id}_text.png")

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def href(self) -> str:
        return self.data["external_urls"]["spotify"]

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def album(self) -> str:
        return self.data["album"]["name"]

    @property
    def release(self) -> str:
        return self.data["album"]["release_date"][:4]

    @property
    def artist(self) -> str:
        return ", ".join([artist["name"] for artist in self.data["artists"]])

    @property
    def popularity(self) -> str:
        return self.data["popularity"]

    def __str__(self):
        return (
            f"{self.release} - '{self.name}' von '{self.artist}' "
            f"(Album: '{self.album}', Popularität: {self.popularity}, Url: {self.href})"
        )


class Playlist:
    def __init__(self, playlist: str):
        if playlist.startswith("https://"):
            self.playlist_id = self.id_from_url(playlist)
        else:
            self.playlist_id = playlist
        assert (
            re.fullmatch("[a-zA-Z0-9]*", self.playlist_id)
            and len(self.playlist_id) == 22
        ), f"invalid playlist id provided"
        self.json_data = {}
        self.extract_json()

        self.tracks = [
            Song(item["track"]) for item in self.json_data["tracks"]["items"]
        ]

    @property
    def name(self) -> str:
        return self.json_data["name"]

    @property
    def href(self) -> str:
        return self.json_data["external_urls"]["spotify"]

    def extract_json(self, use_cached: bool = True):
        json_cached_file = f"cache/{self.playlist_id}_raw.json"
        for folder in ["cache", "output", f"cache/{self.playlist_id}"]:
            if not os.path.exists(folder):
                os.makedirs(folder)
        try:
            if not use_cached:
                os.remove(json_cached_file)
            with open(json_cached_file, "r") as f:
                self.json_data = json.load(f)
        except FileNotFoundError:
            sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
            self.json_data = sp.playlist(self.playlist_id)
            with open(json_cached_file, "w") as f:
                json.dump(self.json_data, f)

    def save_qr_codes(self):
        for track in self.tracks:
            track.save_qr(self.playlist_id)

    def save_text(self):
        for track in self.tracks:
            track.save_text(self.playlist_id)

    @staticmethod
    def id_from_url(url):
        return re.match(r".*spotify\.com/playlist/([a-zA-Z0-9]*)", url).groups()[0]

    def __str__(self):
        return (
            f"\nPlaylist: {self.name} ({self.href})"
            + "\n\n"
            + "\n".join([str(track) for track in self.tracks])
        )


def main():
    playlist = Playlist("2S5UtSsnlyMDzawaJuuGzs")
    print(playlist)
    playlist.save_qr_codes()
    playlist.save_text()


if __name__ == "__main__":
    main()
