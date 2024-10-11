import glob
import os
import re
import sys
import textwrap
import unicodedata
import warnings
from typing import Generator, Union

import drawsvg as draw
import spotipy
import json
import segno
from fpdf import FPDF, Align
from spotipy.oauth2 import SpotifyClientCredentials
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM


class Song:
    QR_SCALE = 10
    IMAGE_SIZE = None

    def __init__(self, track: dict):
        self.data = track

    def save_qr(self, playlist_id: str, use_cached=True):
        pth = f"cache/{playlist_id}/{self.id}_qr.svg"
        if not os.path.exists(pth) or not use_cached:
            qr = segno.make_qr(self.href)
            qr.save(pth, kind="svg")

    def save_text(self, playlist_id: str, use_cached: bool = False):
        # use_cached must be set to false if manual json edits are allowed
        W = H = 400
        scaling = 1 / 370 * W

        def add_text(
            percent_x: float,
            percent_y: float,
            text: str,
            font_size: int = 20,
            wrap_width: int = 22,
            max_lines: int = 3,
        ):
            assert 0 <= percent_x <= 1
            assert 0 <= percent_y <= 1
            font_size *= scaling
            x, y = 0, round(percent_y * H) - H / 2
            wrapped = textwrap.wrap(text, width=int(wrap_width * scaling))
            overfull = "..." if len(wrapped) > max_lines else ""
            text = "\n".join(wrapped[:max_lines]) + overfull
            svg_text = draw.Text(
                text,
                font_size,
                x=x,
                y=y,
                text_anchor="middle",
                fill="black",
                font_family="Arial",
            )
            d.append(svg_text)

        outfile_png = f"cache/{playlist_id}/{self.id}_text.png"
        outfile_svg = outfile_png.replace(".png", ".svg")
        if use_cached and os.path.exists(outfile_png):
            return

        d = draw.Drawing(W, H, origin="center")
        # d.append(draw.Rectangle(x=-W / 2, y=-W / 2, width=W, height=H, stroke='none', fill='grey'))
        add_text(0.5, 0.2, self.artist, 30, max_lines=2)
        add_text(0.5, 0.55, self.release, 100)
        add_text(0.5, 0.7, self.name, 20)
        add_text(0.5, 0.85, self.album, 15)
        d.save_svg(outfile_svg)
        d = svg2rlg(outfile_svg)
        renderPM.drawToFile(d, outfile_png)

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def href(self) -> str:
        return self.data["url"]

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def album(self) -> str:
        return self.data["album"]

    @property
    def release(self) -> str | None:
        return self.data["release"]

    @property
    def artist(self) -> str:
        return self.data["artist"]

    @property
    def popularity(self) -> str:
        return self.data["popularity"]

    def __str__(self):
        return (
            f"{self.release} - '{self.name}' von '{self.artist}' "
            f"(Album: '{self.album}', Popularität: {self.popularity}, Url: {self.href})"
        )

    @staticmethod
    def get_simplified_data(data):
        try:
            release = data["album"]["release_date"][:4]
        except TypeError:
            release = None
        return {
            "id": data["id"],
            "url": data["external_urls"]["spotify"],
            "artist": ", ".join([artist["name"] for artist in data["artists"][:2]]),
            "release": release,
            "name": data["name"],
            "album": data["album"]["name"],
            "popularity": data["popularity"],
        }


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
        self.json_data = self.get_cache_data()
        if self.json_data is None:
            playlist_data = self.poll_spotify()
            self.json_data = {
                "name": playlist_data["name"],
                "href": playlist_data["external_urls"]["spotify"],
                "tracks": [
                    Song.get_simplified_data(item["track"])
                    for item in playlist_data["tracks"]["items"]
                ],
            }
            json_cached_file = f"cache/{self.playlist_id}_raw.json"
            with open(json_cached_file, "w") as f:
                json.dump(self.json_data, f, indent=4)
        tracks = [Song(s) for s in self.json_data["tracks"]]
        self.tracks = {tr.id: tr for tr in tracks if tr.release is not None}

    @property
    def name(self) -> str:
        return self.json_data["name"]

    @property
    def path_safe_name(self) -> str:
        return slugify(self.name)

    @property
    def href(self) -> str:
        return self.json_data["href"]

    def get_cache_data(self, use_cached: bool = True) -> dict | None:
        json_cached_file = f"cache/{self.playlist_id}_raw.json"
        for folder in ["cache", "output", f"cache/{self.playlist_id}"]:
            if not os.path.exists(folder):
                os.makedirs(folder)
        try:
            if not use_cached:
                os.remove(json_cached_file)
            with open(json_cached_file, "r") as f:
                json_data = json.load(f)
        except FileNotFoundError:
            return None
        return json_data

    def poll_spotify(self):
        sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
        json_data = sp.playlist(self.playlist_id)
        next_ = json_data["tracks"]["next"]
        result = json_data["tracks"]
        while next_ is not None:
            result = sp.next(result)
            next_ = result["next"]
            json_data["tracks"]["items"] += result["items"]
        json_data["tracks"]["next"] = None
        return json_data

    def save_qr_codes(self):
        for track in self.tracks.values():
            track.save_qr(self.playlist_id)

    def get_track(self, track_id: str):
        return self.tracks[track_id]

    def save_text(self):
        for track in self.tracks.values():
            track.save_text(self.playlist_id)

    def generate_pdf(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            PDFCreator(self).generate_pdf(
                f"output/{self.path_safe_name}_{self.playlist_id}.pdf"
            )

    @staticmethod
    def id_from_url(url):
        return re.match(r".*spotify\.com/playlist/([a-zA-Z0-9]*)", url).groups()[0]

    def __str__(self):
        return (
            f"\nPlaylist: {self.name} ({self.href}, {len(self.tracks)} tracks)"
            + "\n\n"
            + "\n".join([str(track) for track in self.tracks.values()])
            + f"\nPlaylist: {self.name} ({self.href}, {len(self.tracks)} tracks)"
        )


class PDFCreator:
    def __init__(self, playlist: Playlist):
        self.playlist = playlist

    def generate_pdf(self, outfile: str):
        self.playlist.save_qr_codes()
        self.playlist.save_text()
        pdf = FPDF()
        pdf.set_font("Times", size=12)
        qr_filenames = glob.glob(f"cache/{self.playlist.playlist_id}/*qr.svg")
        img_filenames = glob.glob(f"cache/{self.playlist.playlist_id}/*text.png")
        qr_codes = (img for img in sorted(qr_filenames))
        text_imgs = (img for img in sorted(img_filenames))

        W, H = pdf.epw, pdf.eph
        margin = pdf.t_margin
        w = W / 3

        def next_of(gen: Generator[str, None, None], size=12):
            out = []
            while len(out) < size:
                try:
                    out.append(next(gen))
                except StopIteration:
                    while len(out) % 3 != 0:
                        out.append(None)
                    break
            return (img for img in out)

        def add_img(img: str, pos: Union[Align, float]):
            if img is None:
                return
            pdf.image(img, w=w, h=w, x=pos, y=margin + row * w)

        num_pages = (len(qr_filenames) / 12).__ceil__()
        for page_number in range(num_pages):
            page1 = next_of(qr_codes)
            print(f"processing page {page_number+1}/{num_pages}")
            page_number += 1
            try:
                images = [next(page1) for _ in range(3)]
                pdf.add_page()
                for row in range(4):
                    add_img(images[0], Align.L)
                    add_img(images[1], Align.C)
                    add_img(images[2], Align.R)
                    images = [next(page1) for _ in range(3)]
            except StopIteration:
                pass
            page2 = next_of(text_imgs)
            try:
                images = [next(page2) for _ in range(3)][::-1]
                pdf.add_page()
                for row in range(4):
                    add_img(images[0], Align.L)
                    add_img(images[1], Align.C)
                    add_img(images[2], Align.R)
                    images = [next(page2) for _ in range(3)][::-1]
            except StopIteration:
                pass
        pdf.output(outfile)
        print(f"file saved at: {outfile}")


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def main():
    args = sys.argv
    if len(args) < 2:
        print(
            "usage: python main.py https://link/to/spotify/playlist OR python main.py <playlist_id>"
        )
        raise ValueError("no playlist specified")
    playlist = Playlist(args[1])
    print(playlist)
    playlist.generate_pdf()


if __name__ == "__main__":
    try:
        main()
    except spotipy.oauth2.SpotifyOauthError:
        print(
            "ERROR: Spotify client id and client secret must be set first. Read Readme.md for instructions."
        )
        exit(1)
