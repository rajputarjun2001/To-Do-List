## Earth Zoom Reel Generator (9:16)

Create a smooth zoom-out reel from a ground photo -> city -> country -> full Earth. Output is a 9:16 vertical MP4.

### Usage
1. Place your photo at assets/photo.jpg
2. Optional: place music at assets/music.mp3
3. Create venv and install deps:

   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

4. Generate:

   python scripts/create_earth_zoom.py --photo assets/photo.jpg --location "City, Country" --music assets/music.mp3 --out output/earth_zoom_reel.mp4

