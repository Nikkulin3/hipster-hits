# Hipster-Hits

This repository mimics the behaviour of the game "Hitster", in which each player has to guess the order of years, as well as title, album and artist of a given Song. This program creates custom playing cards from a given Spotify Playlist.

For rules of the game, go [here](https://www.spielregeln.de/hitster.html).

The original Hitster **APP WILL NOT WORK** for the created QR-Codes, you must use any other QR-Code Scanner on your Phone.

## Installation for Windows Users and Non-Programmers

Download and Install the following programs with default parameters:

- GIT https://git-scm.com/downloads (default installation)
- Python https://www.python.org/downloads/ (on first page, select `Add python.exe to PATH`)

Afterward, open a shell in the desired location e.g. Documents folder (right click => open terminal). Then type (or paste with right click) and press enter:

```commandline
git clone https://github.com/Nikkulin3/hipster-hits.git
```
Now a folder `hipster-hits` will be generated.
To install or update the repository, double-click the `install.bat` file.

Now you need a Spotify API Key. Visit [this page](https://developer.spotify.com/documentation/web-api/tutorials/getting-started) to read how. You will need to set up a "Spotify Developer Account" and create an "App". Under section "request an access token" is more information how to obtain your `Client ID` and `Client Secret`. For quick reference after project creation is done:

- Visit https://developer.spotify.com/dashboard/ (or log in and click the link again)
- Click on the name of your app and go to `Settings`
- Note the `Client ID` on this page
- Click on `View client secret` to display the `Client Secret`
- Note the `Client Secret`

After obtaining `Client ID` and `Client Secret`, right click file `generate.bat->more options->edit` (or open with text editor) and edit the specified text fields.

## Usage

- Right click file `generate.bat->more options->edit` (or open with text editor) and change Spotify Playlist URL, then save.
- Double click file `generate.bat`, the output PDF will be in the `output` folder.
- Song information and images are being cached locally, start fresh (playlist update, etc.) with deleting the `cache` folder.

## Printing

The intended use of the PDF-files is to print them double-sided (length-wise), Only then will QR-codes and text line up automagically.
