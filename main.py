import glob
import os
import re
import sys
import textwrap
import warnings
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

    def save_qr(self, playlist_id, use_cached=True):
        pth = f"cache/{playlist_id}/{self.id}_qr.svg"
        if not os.path.exists(pth) or not use_cached:
            qr = segno.make_qr(self.href)
            qr.save(pth, kind="svg")

    def save_text(self, playlist_id, use_cached=False):
        W = H = 400
        scaling = 1 / 370 * W

        def add_text(
            percent_x, percent_y, text, font_size=20, wrap_width=22, max_lines=3
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
        return ", ".join([artist["name"] for artist in self.data["artists"][:2]])

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

        tracks = [Song(item["track"]) for item in self.json_data["tracks"]["items"]]
        self.tracks = {tr.id: tr for tr in tracks}

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
            PDFCreator(self).generate_pdf(f"output/{self.playlist_id}--{self.name}.pdf")

    @staticmethod
    def id_from_url(url):
        return re.match(r".*spotify\.com/playlist/([a-zA-Z0-9]*)", url).groups()[0]

    def __str__(self):
        return (
            f"\nPlaylist: {self.name} ({self.href})"
            + "\n\n"
            + "\n".join([str(track) for track in self.tracks.values()])
        )


class PDFCreator:
    def __init__(self, playlist: Playlist):
        self.playlist = playlist

    def generate_pdf(self, outfile):
        self.playlist.save_qr_codes()
        self.playlist.save_text()
        pdf = FPDF()
        pdf.set_font("Times", size=12)
        qr_codes = (
            img
            for img in sorted(glob.glob(f"cache/{self.playlist.playlist_id}/*qr.svg"))
        )
        text_imgs = (
            img
            for img in sorted(glob.glob(f"cache/{self.playlist.playlist_id}/*text.png"))
        )

        W, H = pdf.epw, pdf.eph
        margin = pdf.t_margin
        w = W / 3

        def next_of(gen, size=12):
            out = []
            while len(out) < size:
                try:
                    out.append(next(gen))
                except StopIteration:
                    while len(out) % 3 != 0:
                        out.append(None)
                    break
            return (img for img in out)

        def add_img(img, pos):
            if img is None:
                return
            pdf.image(img, w=w, h=w, x=pos, y=margin + row * w)

        while True:
            page1 = next_of(qr_codes)
            try:
                images = [next(page1) for _ in range(3)]
                if images[0] is None:
                    break
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
                if images[0] is None:
                    break
                pdf.add_page()
                for row in range(4):
                    add_img(images[0], Align.L)
                    add_img(images[1], Align.C)
                    add_img(images[2], Align.R)
                    images = [next(page2) for _ in range(3)][::-1]
            except StopIteration:
                break
        pdf.output(outfile)
        print(f"file saved at: {outfile}")


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
