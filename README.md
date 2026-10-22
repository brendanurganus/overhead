# OverHead

Every tracked satellite (about 14,700) around a live-clouded 3D Earth, computed in real time from public orbit data, with "Look up" ground views where you stand at Yosemite's Tunnel View or on the Schattberg above Saalbach, Austria, and watch real satellite passes cross the real night sky.

Built by Brendan Urganus with Claude (Anthropic).

## What's real

- **Satellites:** orbits from CelesTrak (via mirrors), LEOrbit and SatNOGS, propagated with SGP4 in your browser; catalog details from Jonathan McDowell's GCAT.
- **Earth:** NASA GIBS true-color VIIRS imagery for the clouds, NASA Blue Marble and Black Marble; water mask from Natural Earth.
- **Moon:** NASA Scientific Visualization Studio CGI Moon Kit (Lunar Reconnaissance Orbiter data).
- **Sky:** stars from d3-celestial (© 2015 Olaf Frohn, BSD 3-Clause); Sun, Moon and planet positions from Astronomy Engine.
- **Yosemite:** USGS 3DEP elevation and USDA NAIP aerial imagery (public domain).
- **Saalbach:** Austrian open elevation data (DGM Österreich, CC BY 3.0 AT, via Tilezen terrain tiles) and basemap.at aerial imagery (CC BY 4.0), winterized.

## Methodology and licenses

[`methodology.html`](methodology.html) explains how every number is computed, the known limits, and every source with its license and required credit. Short version of the licenses:

- GCAT: CC BY 4.0, "data from GCAT (J. McDowell, planet4589.org/space/gcat)".
- SatNOGS DB: CC BY-SA 4.0. Because some orbital elements in `data/sats.json` come from SatNOGS DB, that file is offered under CC BY-SA 4.0.
- NASA imagery and models (GIBS, Blue Marble, Black Marble, CGI Moon Kit, NASA 3D Resources): not copyrighted; use does not imply NASA endorsement. GIBS: "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)."
- USGS 3DEP and USDA NAIP: public domain. Natural Earth: public domain. ambientCG Rock026: CC0.
- Saalbach terrain via Tilezen: Austria terrain data © offene Daten Österreichs, Digitales Geländemodell (DGM) Österreich (CC BY 3.0 AT); Europe terrain data produced using Copernicus data and information funded by the European Union, EU-DEM layers; SRTM and GMTED2010 courtesy of the U.S. Geological Survey.
- basemap.at: CC BY 4.0, "Datenquelle: basemap.at".
- CelesTrak orbital data, the satvisor-data and LEOrbit mirrors, and Mike McCants' magnitudes: no license stated by the providers.
- Libraries: three.js, satellite.js and Astronomy Engine (MIT). Fonts: Barlow Condensed and IBM Plex (SIL OFL 1.1).

OverHead is an independent project and is not affiliated with or endorsed by any of these organizations. The scripts in `tools/` rebuild the cloud and orbit data.
