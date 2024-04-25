:: SET CLIENT ID BELOW
set SPOTIPY_CLIENT_ID=changeme123
:: SET CLIENT SECRET BELOW
set SPOTIPY_CLIENT_SECRET=changeme1234

:::::::::::::::::::

:: SPECIFY SPOTIFY PLAYLIST BELOW
set PLAYLIST=https://open.spotify.com/playlist/37i9dQZF1DX1tz6EDao8it

::::::::::::::::::

venv\Scripts\activate.bat
python main.py %PLAYLIST%
