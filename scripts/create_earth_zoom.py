#!/usr/bin/env python3
import argparse
import os
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageOps, ImageEnhance

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.audio.AudioClip import AudioClip as MPAudioClip
from moviepy.editor import vfx

try:
    import exifread  # type: ignore
except Exception:
    exifread = None

try:
    from geopy.geocoders import Nominatim  # type: ignore
except Exception:
    Nominatim = None

try:
    from staticmap import StaticMap, CircleMarker  # type: ignore
except Exception:
    StaticMap = None

import requests

TARGET_SIZE = (1080, 1920)  # 9:16 vertical
FPS = 30
TOTAL_DURATION_S = 12.0


@dataclass
class LocationGuess:
    latitude: float
    longitude: float
    display_name: str


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_exif_gps(image_path: str) -> Optional[Tuple[float, float]]:
    if exifread is None:
        return None
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        def _ratio_to_float(ratio):
            return float(ratio.num) / float(ratio.den)
        def _convert(values, ref):
            d = _ratio_to_float(values[0])
            m = _ratio_to_float(values[1])
            s = _ratio_to_float(values[2])
            dd = d + m/60.0 + s/3600.0
            if ref in ['S', 'W']:
                dd = -dd
            return dd
        lat_key = 'GPS GPSLatitude'
        lat_ref_key = 'GPS GPSLatitudeRef'
        lon_key = 'GPS GPSLongitude'
        lon_ref_key = 'GPS GPSLongitudeRef'
        if all(k in tags for k in [lat_key, lat_ref_key, lon_key, lon_ref_key]):
            lat = _convert(tags[lat_key].values, str(tags[lat_ref_key]))
            lon = _convert(tags[lon_key].values, str(tags[lon_ref_key]))
            return (lat, lon)
    except Exception:
        return None
    return None


def geocode_location(query: str) -> Optional[LocationGuess]:
    if not query:
        return None
    try:
        if Nominatim is None:
            return None
        geolocator = Nominatim(user_agent='earth-zoom-script')
        loc = geolocator.geocode(query, timeout=10)
        if loc is None:
            return None
        return LocationGuess(latitude=loc.latitude, longitude=loc.longitude, display_name=loc.address)
    except Exception:
        return None


def fetch_nasa_blue_marble(save_path: str) -> str:
    ensure_dir(os.path.dirname(save_path))
    if os.path.exists(save_path):
        return save_path
    url = 'https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73882/world.topo.bathy.200412.3x5400x2700.jpg'
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(r.content)
    return save_path


def build_osm_static(lat: float, lon: float, zoom: int, size: Tuple[int, int], save_path: str) -> str:
    if StaticMap is None:
        raise RuntimeError('staticmap dependency missing. Please install requirements.')
    ensure_dir(os.path.dirname(save_path))
    m = StaticMap(size[0], size[1], url_template='https://tile.openstreetmap.org/{z}/{x}/{y}.png')
    marker = CircleMarker((lon, lat), 'red', 6)
    m.add_marker(marker)
    image = m.render(zoom=zoom, center=(lon, lat))
    image.save(save_path)
    return save_path


def letterbox_to_916(img: Image.Image) -> Image.Image:
    target_w, target_h = TARGET_SIZE
    ratio_target = target_w / target_h
    ratio_img = img.width / img.height
    if ratio_img > ratio_target:
        new_h = target_h
        new_w = int(ratio_img * new_h)
    else:
        new_w = target_w
        new_h = int(new_w / ratio_img)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    cropped = resized.crop((left, top, left + target_w, top + target_h))
    return cropped


def enhance_natural(img: Image.Image) -> Image.Image:
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Color(img).enhance(1.06)
    img = ImageEnhance.Contrast(img).enhance(1.04)
    img = ImageEnhance.Sharpness(img).enhance(1.05)
    return img


def build_zoom_from_image(img_path: str, duration: float, start_scale: float, end_scale: float) -> ImageClip:
    base = Image.open(img_path).convert('RGB')
    base = letterbox_to_916(base)
    base = enhance_natural(base)
    frame_np = np.array(base)

    def make_frame(t: float):
        prog = t / duration
        scale = start_scale + (end_scale - start_scale) * prog
        frame = Image.fromarray(frame_np)
        w, h = frame.size
        resized = frame.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        rw, rh = resized.size
        left = (rw - TARGET_SIZE[0]) // 2
        top = (rh - TARGET_SIZE[1]) // 2
        cropped = resized.crop((left, top, left + TARGET_SIZE[0], top + TARGET_SIZE[1]))
        return np.array(cropped)

    clip = ImageClip(frame_np).set_duration(duration)
    clip = clip.set_make_frame(make_frame)
    return clip.set_fps(FPS)


def with_slight_vignette(clip: ImageClip, strength: float = 0.15) -> ImageClip:
    w, h = TARGET_SIZE
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2.0, h / 2.0
    max_r = (cx ** 2 + cy ** 2) ** 0.5
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    mask = 1.0 - strength * (dist / max_r) ** 1.5
    mask = np.clip(mask, 0.85, 1.0)

    def apply(img: np.ndarray) -> np.ndarray:
        return (img.astype(np.float32) * mask[..., None]).astype(np.uint8)

    return clip.fl_image(apply)


def make_ambient_music(duration: float) -> MPAudioClip:
    import math
    def tone(t: float) -> float:
        f1, f2, f3 = 174.0, 196.0, 261.63
        val = 0.28 * math.sin(2*math.pi*f1*t) + 0.2 * math.sin(2*math.pi*f2*t) + 0.18 * math.sin(2*math.pi*f3*t)
        val *= 0.6 + 0.4 * math.sin(2*math.pi*0.08*t)
        return val
    return MPAudioClip(make_frame=lambda t: tone(t), fps=44100).audio_fadein(0.6).audio_fadeout(1.0).volumex(0.6).set_duration(duration)


def main():
    parser = argparse.ArgumentParser(description='Create a vertical Earth zoom reel (9:16) from a ground photo.')
    parser.add_argument('--photo', required=True, help='Path to your starting photo (ground level).')
    parser.add_argument('--location', default='', help='Freeform location (e.g., "Chennai, India"). If omitted, tries EXIF GPS.')
    parser.add_argument('--music', default='assets/music.mp3', help='Optional background music path.')
    parser.add_argument('--out', default='output/earth_zoom_reel.mp4', help='Output video path.')
    parser.add_argument('--keep-assets', action='store_true', help='Keep temporary assets.')
    args = parser.parse_args()

    ensure_dir('output')
    ensure_dir('assets')

    latlon: Optional[Tuple[float, float]] = None
    if args.location:
        guess = geocode_location(args.location)
        if guess:
            latlon = (guess.latitude, guess.longitude)
    if latlon is None:
        gps = read_exif_gps(args.photo)
        if gps is not None:
            latlon = gps
    if latlon is None:
        latlon = (0.0, 0.0)
    lat, lon = latlon

    with tempfile.TemporaryDirectory() as td:
        city_png = os.path.join(td, 'city.png')
        country_png = os.path.join(td, 'country.png')
        earth_jpg = os.path.join(td, 'earth.jpg')

        try:
            build_osm_static(lat, lon, zoom=13, size=TARGET_SIZE, save_path=city_png)
        except Exception:
            Image.new('RGB', TARGET_SIZE, (245, 245, 245)).save(city_png)
        try:
            build_osm_static(lat, lon, zoom=5, size=TARGET_SIZE, save_path=country_png)
        except Exception:
            Image.new('RGB', TARGET_SIZE, (230, 230, 230)).save(country_png)

        fetch_nasa_blue_marble(earth_jpg)

        d1, d2, d3 = 3.5, 3.0, 2.5
        d4 = max(1.0, TOTAL_DURATION_S - (d1 + d2 + d3) - 1.5)

        photo_clip = build_zoom_from_image(args.photo, duration=d1, start_scale=1.18, end_scale=1.0)
        photo_clip = with_slight_vignette(photo_clip)
        city_clip = build_zoom_from_image(city_png, duration=d2, start_scale=1.5, end_scale=1.0).fx(vfx.fadein, 0.3).fx(vfx.fadeout, 0.3)
        country_clip = build_zoom_from_image(country_png, duration=d3, start_scale=1.5, end_scale=1.0).fx(vfx.fadein, 0.3).fx(vfx.fadeout, 0.3)
        earth_clip = build_zoom_from_image(earth_jpg, duration=d4, start_scale=1.2, end_scale=1.0).fx(vfx.fadein, 0.3)

        clips = [
            photo_clip,
            city_clip.crossfadein(0.5),
            country_clip.crossfadein(0.5),
            earth_clip.crossfadein(0.5),
        ]
        video = concatenate_videoclips(clips, method='compose', padding=-0.5)

        music_set = False
        if os.path.exists(args.music):
            try:
                music = AudioFileClip(args.music).audio_fadein(0.5).audio_fadeout(1.0).volumex(0.25)
                music = music.set_duration(video.duration)
                video = video.set_audio(music)
                music_set = True
            except Exception:
                pass
        if not music_set:
            try:
                ambient = make_ambient_music(video.duration)
                video = video.set_audio(ambient)
            except Exception:
                pass

        ensure_dir(os.path.dirname(args.out))
        video.write_videofile(
            args.out,
            fps=FPS,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            bitrate='6M',
            threads=max(1, os.cpu_count() or 1),
        )

        if args.keep_assets:
            os.makedirs('output/tmp_assets', exist_ok=True)
            for p in [city_png, country_png, earth_jpg]:
                if os.path.exists(p):
                    Image.open(p).save(os.path.join('output/tmp_assets', os.path.basename(p)))


if __name__ == '__main__':
    main()
