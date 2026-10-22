# OverHead

Every tracked satellite (about 14,700) around a live-clouded 3D Earth, computed in real time from public orbit data, with "Look up" ground views where you stand at Yosemite's Tunnel View or on the Schattberg above Saalbach, Austria, and watch real satellite passes cross the real night sky.

Built by Brendan Urganus with Claude (Anthropic).

## What's real

- **Satellites:** orbits from CelesTrak (via mirrors), LEOrbit and SatNOGS, propagated with SGP4 in your browser; catalog details from Jonathan McDowell's GCAT.
- **Earth:** NASA GIBS true-color VIIRS imagery for the clouds, NASA Blue Marble and Black Marble.
- **Sky:** stars from d3-celestial; Sun, Moon and planet positions from Astronomy Engine.
- **Yosemite:** USGS 3DEP elevation and USDA NAIP aerial imagery (public domain).
- **Saalbach:** Austrian open elevation data (DGM Österreich, CC BY 3.0 AT, via Tilezen terrain tiles) and basemap.at aerial imagery (CC BY 4.0), winterized.

Full credits are in the page's About panel. The scripts in `tools/` rebuild the cloud and orbit data.
