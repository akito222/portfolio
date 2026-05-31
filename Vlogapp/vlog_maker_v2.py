import concurrent.futures
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import threading
import time

import numpy as np
import requests
import streamlit as st
from moviepy.editor import (AudioFileClip, CompositeAudioClip,
                             CompositeVideoClip, ImageClip, VideoFileClip,
                             concatenate_videoclips)
import moviepy.video.fx.all as vfx
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. 音声生成ロジック & フリガナ処理
# ==========================================
def generate_voice(text, output_filename, speaker_id, speed_scale=1.5):
    """音声生成（スレッド内から呼ぶため例外を raise する）"""
    clean_text = text.replace('*', '')
    res1 = requests.post("http://localhost:50021/audio_query",
                         params={"text": clean_text, "speaker": speaker_id}, timeout=30)
    res1.raise_for_status()
    query_data = res1.json()
    query_data["speedScale"] = speed_scale
    res2 = requests.post("http://localhost:50021/synthesis",
                         params={"speaker": speaker_id}, json=query_data, timeout=60)
    res2.raise_for_status()
    with open(output_filename, "wb") as f:
        f.write(res2.content)
    return output_filename

def process_furigana(text):
    visual = re.sub(r'\*([^*|]+)\*\|([^\s。、！？\n*]+)', r'*\1*', text)
    audio  = re.sub(r'\*([^*|]+)\*\|([^\s。、！？\n*]+)', r'\2', text)
    visual = re.sub(r'([^\s。、！？\n*|]+)\|([^\s。、！？\n*]+)', r'\1', visual)
    audio  = re.sub(r'([^\s。、！？\n*|]+)\|([^\s。、！？\n*]+)', r'\2', audio)
    return visual, audio

def auto_wrap_text(text, max_chars):
    """各行をmax_chars文字で折り返す（既存の改行は維持）"""
    result = []
    for line in text.split('\n'):
        while len(line) > max_chars:
            result.append(line[:max_chars])
            line = line[max_chars:]
        result.append(line)
    return '\n'.join(result)

# ----------------------------------------------------------
# キャッシュ設定
# ----------------------------------------------------------
VOICE_CACHE_DIR = os.path.join("temp_uploads", "voice_cache")
SCENE_CACHE_DIR = os.path.join("temp_uploads", "scene_cache")

def _compute_voice_hash(audio_text, speaker_id, speed_scale):
    key = f"{audio_text}|{speaker_id}|{speed_scale}"
    return hashlib.sha256(key.encode()).hexdigest()[:24]

def _compute_scene_hash(scene, voice_hash, is_draft, font_path):
    params = {
        "voice_hash":   voice_hash,
        "text":         scene["text"],
        "text_color":   scene["text_color"],
        "stroke_color": scene["stroke_color"],
        "accent_color": scene["accent_color"],
        "accent_scale": scene["accent_scale"],
        "stroke_width": scene["stroke_width"],
        "text_position":scene["text_position"],
        "text_anim":    scene.get("text_anim", "なし"),
        "effect":       scene["effect"],
        "fade_in":      scene["fade_in"],
        "fade_out":     scene["fade_out"],
        "se":           str(scene["sound_effects"]),
        "trim_start":   scene.get("trim_start", 0.0),
        "speed_scale":  scene.get("speed_scale", 1.5),
        "is_draft":     is_draft,
        "font_path":    font_path,
        "file_size":    str(os.path.getsize(scene["file"])) if os.path.exists(scene["file"]) else "0",
    }
    key = json.dumps(params, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:24]

def _get_scene_thumbnail(file_path, size=(160, 284)):
    """ストーリーボード用サムネイル（PIL Image）を返す"""
    try:
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            img = Image.open(file_path).convert('RGB')
        else:
            clip = VideoFileClip(file_path)
            img = Image.fromarray(clip.get_frame(0)).convert('RGB')
            clip.close()
        w, h = img.size
        target_ratio = size[0] / size[1]
        if w / h > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))
        return img.resize(size, Image.LANCZOS)
    except Exception:
        return None

# ==========================================
# 2. 字幕描画（共通コア）★ プレビューと動画生成で共用
# ==========================================
def _draw_text_stroked(draw, text, x, y, font, fill, stroke_color, stroke_width):
    """テキスト1片をストローク付きで描画する（PIL内蔵stroke_widthを使用）"""
    draw.text((x, y), text, font=font, fill=fill, anchor="lt",
              stroke_width=stroke_width, stroke_fill=stroke_color)


def _draw_subtitle_on_image(img, text, font_path, target_w, target_h,
                             text_color, stroke_color, accent_color,
                             accent_scale, position, stroke_width):
    """PILのImageに直接字幕を描画して返す（プレビュー・動画生成共用）"""
    draw = ImageDraw.Draw(img)
    font_size = 90

    while True:
        try:
            font       = ImageFont.truetype(font_path, font_size)
            font_large = ImageFont.truetype(font_path, int(font_size * accent_scale))
        except Exception:
            font       = ImageFont.load_default()
            font_large = font
            break
        lines = text.split('\n')
        max_line_w = 0
        for line in lines:
            parts = line.split('*')
            lw = sum(draw.textlength(p, font=(font_large if j % 2 == 1 else font))
                     for j, p in enumerate(parts) if p)
            max_line_w = max(max_line_w, lw)
        if max_line_w > target_w * 0.9 and font_size > 20:
            font_size -= 2
        else:
            break

    lines = text.split('\n')
    bbox = draw.textbbox((0, 0), "あ", font=font_large)
    actual_line_height = bbox[3] - bbox[1]
    line_spacing = 20
    total_h = len(lines) * actual_line_height + (len(lines) - 1) * line_spacing

    if position == "中央":
        text_center_y = int(target_h * 0.5)
    elif position == "上部":
        text_center_y = int(target_h * 0.25)
    else:
        text_center_y = int(target_h * 0.75)

    start_y   = text_center_y - (total_h / 2)
    current_y = start_y

    for line in lines:
        parts = line.split('*')
        lw = sum(draw.textlength(p, font=(font_large if j % 2 == 1 else font))
                 for j, p in enumerate(parts) if p)
        current_x = (target_w - lw) / 2
        for j, part in enumerate(parts):
            if part:
                f     = font_large if j % 2 == 1 else font
                color = accent_color if j % 2 == 1 else text_color
                _draw_text_stroked(draw, part, current_x, current_y,
                                   f, color, stroke_color, stroke_width)
                current_x += draw.textlength(part, font=f)
        current_y += actual_line_height + line_spacing

    return img


# ★ 新機能① リアルタイムプレビュー
def create_subtitle_preview(text, font_path, target_w=360, target_h=640,
                             text_color="#FFFFFF", stroke_color="#000000",
                             accent_color="#FF0000", accent_scale=1.3,
                             position="中央", stroke_width=16):
    """字幕プレビュー用のPIL Imageを返す（動画生成不要）"""
    bg = Image.new('RGBA', (target_w, target_h), (30, 30, 30, 255))
    overlay = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
    _draw_subtitle_on_image(overlay, text, font_path, target_w, target_h,
                            text_color, stroke_color, accent_color,
                            accent_scale, position, stroke_width)
    result = Image.alpha_composite(bg, overlay)
    return result.convert("RGB")


def create_subtitle_clip(text, duration, font_path, target_w=720, target_h=1280,
                          text_color="#FFFFFF", stroke_color="#000000",
                          accent_color="#FF0000", accent_scale=1.3,
                          position="中央", stroke_width=16):
    img = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
    _draw_subtitle_on_image(img, text, font_path, target_w, target_h,
                            text_color, stroke_color, accent_color,
                            accent_scale, position, stroke_width)
    return ImageClip(np.array(img)).set_duration(duration)


# ==========================================
# 3. 映像処理ユーティリティ
# ==========================================
def make_vertical_crop_clip(clip, target_w, target_h):
    clip_ratio   = clip.w / clip.h
    target_ratio = target_w / target_h
    resized = clip.resize(height=target_h) if clip_ratio > target_ratio else clip.resize(width=target_w)
    return resized.crop(x_center=resized.w/2, y_center=resized.h/2,
                        width=target_w, height=target_h)

def generate_thumbnail(bg_file_path, text, opacity, font_path, font_size,
                        stroke_width, target_w=720, target_h=1280):
    try:
        ext = bg_file_path.split('.')[-1].lower()
        if ext in ['mp4', 'mov']:
            clip = VideoFileClip(bg_file_path)
            frame = clip.get_frame(0)
            clip.close()
            bg_img = Image.fromarray(frame).convert("RGBA")
        else:
            bg_img = Image.open(bg_file_path).convert("RGBA")
    except Exception:
        bg_img = Image.new('RGBA', (target_w, target_h), (50, 50, 50, 255))

    bg_w, bg_h   = bg_img.size
    target_ratio = target_w / target_h
    bg_ratio     = bg_w / bg_h
    if bg_ratio > target_ratio:
        new_h, new_w = target_h, int(target_h * bg_ratio)
    else:
        new_w, new_h = target_w, int(target_w / bg_ratio)

    bg_img = bg_img.resize((new_w, new_h), Image.LANCZOS)
    left, top = (new_w - target_w) / 2, (new_h - target_h) / 2
    bg_img = bg_img.crop((left, top, left + target_w, top + target_h))

    overlay = Image.new('RGBA', (target_w, target_h),
                        (0, 0, 0, int(255 * opacity / 100.0)))
    thumb = Image.alpha_composite(bg_img, overlay)
    draw  = ImageDraw.Draw(thumb)

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    lines        = text.split('\n')
    line_spacing = 20
    bbox         = draw.textbbox((0, 0), "あ", font=font)
    actual_line_height = bbox[3] - bbox[1]
    total_h  = len(lines) * actual_line_height + (len(lines) - 1) * line_spacing
    start_y  = (target_h - total_h) / 2
    current_y = start_y

    for line in lines:
        if line.strip():
            lw        = draw.textlength(line, font=font)
            current_x = (target_w - lw) / 2
            _draw_text_stroked(draw, line, current_x, current_y,
                               font, "#FFFFFF", "#000000", stroke_width)
        current_y += actual_line_height + line_spacing

    return thumb.convert("RGB")


# ==========================================
# 4. メインビルド処理
# ==========================================
def _prog(state, value, text=""):
    if state is not None:
        state["value"] = min(float(value), 1.0)
        state["text"]  = text


def _build_scene_clip(vs, font_path, se_dir, T_W, T_H, FPS, speed_scale):
    """1シーンを合成して scene_cache に MP4 として保存し、パスを返す"""
    scene      = vs["scene"]
    line_data  = vs["lines"]
    total_chars = vs["total_chars"]
    wav_path   = vs["wav_path"]
    scene_hash = vs["scene_hash"]
    cached_mp4 = os.path.join(SCENE_CACHE_DIR, f"{scene_hash}.mp4")

    if os.path.exists(cached_mp4):
        return cached_mp4, True   # (path, cache_hit)

    v_clip    = AudioFileClip(wav_path)
    total_dur = v_clip.duration
    scene_v_clips = [v_clip.set_start(0.0)]
    scene_s_clips = []
    offset    = 0.0

    for d in line_data:
        dur = (total_dur * len(d["audio"]) / total_chars
               if total_chars > 0 else total_dur / len(line_data))
        s_clip = create_subtitle_clip(
            d["visual"], dur, font_path, T_W, T_H,
            scene["text_color"], scene["stroke_color"],
            scene["accent_color"], scene["accent_scale"],
            position=scene["text_position"],
            stroke_width=scene.get("stroke_width", 16)
        ).set_start(offset)

        anim = scene.get("text_anim", "なし")
        if anim == "ポップイン":
            def pop_effect(t):
                if t < 0.1:    return 0.7 + 0.35 * (t / 0.1)
                elif t < 0.15: return 1.05 - 0.05 * ((t - 0.1) / 0.05)
                return 1.0
            s_clip = s_clip.resize(pop_effect).set_position('center').fx(vfx.fadein, 0.05)
        elif anim == "スライドアップ":
            s_clip = (s_clip.set_position(lambda t: ('center', max(0, 30 - 150 * t)))
                      .fx(vfx.fadein, 0.15))
        scene_s_clips.append(s_clip)
        offset += dur

    se_clips = []
    for se_item in scene["sound_effects"]:
        if se_item["name"] != "なし":
            sp = os.path.join(se_dir, se_item["name"])
            if os.path.exists(sp):
                se_clips.append(AudioFileClip(sp).set_start(se_item["start_time"]))

    if scene["file"].lower().endswith(('.jpg', '.jpeg', '.png')):
        m_clip = ImageClip(scene["file"]).set_duration(offset)
    else:
        raw = VideoFileClip(scene["file"])
        ts  = scene.get("trim_start", 0.0)
        if ts >= raw.duration: ts = 0.0
        trimmed = raw.subclip(ts, raw.duration)
        m_clip = (trimmed.fx(vfx.loop, duration=offset)
                  if trimmed.duration < offset else trimmed.subclip(0, offset))

    zoom_val = 1.2
    eff = scene["effect"]
    if eff in ["右へスライド", "左へスライド"]:
        base = make_vertical_crop_clip(m_clip, int(T_W * zoom_val), int(T_H * zoom_val)).set_duration(offset)
        mx   = int(T_W * (zoom_val - 1.0))
        if eff == "右へスライド":
            eff_clip = base.set_position(lambda t, _mx=mx, _off=offset: (int(-_mx + _mx * t / _off), "center"))
        else:
            eff_clip = base.set_position(lambda t, _mx=mx, _off=offset: (int(-_mx * t / _off), "center"))
        processed = CompositeVideoClip([eff_clip], size=(T_W, T_H)).set_duration(offset)
    elif eff == "ズームイン":
        base = make_vertical_crop_clip(m_clip, T_W, T_H).set_duration(offset)
        processed = base.resize(lambda t, _off=offset: 1.0 + 0.2 * t / _off).set_position("center")
    elif eff == "ズームアウト":
        base = make_vertical_crop_clip(m_clip, T_W, T_H).set_duration(offset)
        processed = base.resize(lambda t, _off=offset: 1.2 - 0.2 * t / _off).set_position("center")
    else:
        processed = make_vertical_crop_clip(m_clip, T_W, T_H).set_duration(offset)

    combined  = CompositeAudioClip(scene_v_clips + se_clips)
    composed  = CompositeVideoClip([processed] + scene_s_clips).set_audio(combined)
    fade_t    = min(0.3, offset / 2)
    if scene["fade_in"]:  composed = composed.fx(vfx.fadein,  fade_t)
    if scene["fade_out"]: composed = composed.fx(vfx.fadeout, fade_t)

    composed.write_videofile(cached_mp4, fps=FPS, codec="libx264", audio_codec="aac",
                             preset="ultrafast", threads=2, logger=None)
    composed.close()
    return cached_mp4, False   # (path, cache_hit)


def build_vlog(scenes, output_filename, font_path, se_dir, thumb_settings=None,
               is_draft=False, speaker_id=13, speed_scale=1.5,
               progress_state=None, cancel_flag=None):
    T_W, T_H = (360, 640) if is_draft else (720, 1280)
    FPS = 10 if is_draft else 24
    os.makedirs(VOICE_CACHE_DIR, exist_ok=True)
    os.makedirs(SCENE_CACHE_DIR, exist_ok=True)

    # シーンの前処理
    valid_scenes = []
    for index, scene in enumerate(scenes):
        if not scene["text"].strip():
            continue
        lines = [l for l in scene["text"].split('\n') if l.strip()]
        if not lines:
            continue
        line_data, full_audio, total_chars = [], "", 0
        for l in lines:
            vt, at = process_furigana(l)
            vt = vt.replace('、', '').replace('。', '')
            line_data.append({"visual": vt, "audio": at})
            full_audio += at
            total_chars += len(at)
        valid_scenes.append({
            "idx": index, "scene": scene, "lines": line_data,
            "audio_text": full_audio, "total_chars": total_chars,
            "speed": scene.get("speed_scale", speed_scale),
        })

    n = len(valid_scenes)
    if n == 0:
        if progress_state: progress_state["done"] = True
        return

    # ===================================================
    # Phase 1: 並列音声生成（キャッシュ付き）
    # ===================================================
    _prog(progress_state, 0, f"音声を並列生成中 (0/{n})...")
    completed = [0]

    def _voice_task(vs):
        h      = _compute_voice_hash(vs["audio_text"], speaker_id, vs["speed"])
        cached = os.path.join(VOICE_CACHE_DIR, f"{h}.wav")
        if not os.path.exists(cached):
            generate_voice(vs["audio_text"], cached, speaker_id, vs["speed"])
        vs["wav_path"]   = cached
        vs["voice_hash"] = h

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(n, 4)) as ex:
        futs = {ex.submit(_voice_task, vs): vs for vs in valid_scenes}
        for fut in concurrent.futures.as_completed(futs):
            if cancel_flag and cancel_flag.get("flag"):
                if progress_state: progress_state["cancelled"] = True
                break
            try:
                fut.result()
                completed[0] += 1
                _prog(progress_state, completed[0] / n * 0.4,
                      f"音声生成中 ({completed[0]}/{n})...")
            except Exception as e:
                raise RuntimeError(f"音声生成エラー: {e}")

    if cancel_flag and cancel_flag.get("flag"):
        if progress_state: progress_state["done"] = True
        return

    # scene_hash を確定（voice_hash が揃ってから）
    for vs in valid_scenes:
        vs["scene_hash"] = _compute_scene_hash(vs["scene"], vs["voice_hash"], is_draft, font_path)

    # ===================================================
    # Phase 2: シーン合成（差分キャッシュ付き）
    # ===================================================
    scene_mp4_list = []

    # サムネイルクリップ
    if (thumb_settings and thumb_settings.get("use_thumb")
            and thumb_settings.get("text", "").strip()):
        _prog(progress_state, 0.4, "サムネイル生成中...")
        thumb_img  = generate_thumbnail(
            thumb_settings["bg_file"], thumb_settings["text"],
            thumb_settings["opacity"], font_path,
            thumb_settings["font_size"], thumb_settings["stroke_width"], T_W, T_H)
        thumb_path = os.path.join(SCENE_CACHE_DIR, "thumb_clip.mp4")
        from moviepy.audio.AudioClip import AudioArrayClip
        silence = AudioArrayClip(np.zeros((int(0.1 * 44100), 2)), fps=44100).set_duration(0.1)
        (ImageClip(np.array(thumb_img)).set_duration(0.1)
         .set_audio(silence)
         .write_videofile(thumb_path, fps=FPS, codec="libx264", audio_codec="aac",
                          preset="ultrafast", logger=None))
        scene_mp4_list.append(thumb_path)

    for i, vs in enumerate(valid_scenes):
        if cancel_flag and cancel_flag.get("flag"):
            if progress_state: progress_state["cancelled"] = True
            break
        label = f"シーン {vs['idx']+1}/{len(scenes)} ({i+1}/{n})"
        _prog(progress_state, 0.4 + i / n * 0.55, f"合成中: {label}...")
        mp4_path, hit = _build_scene_clip(vs, font_path, se_dir, T_W, T_H, FPS, speed_scale)
        scene_mp4_list.append(mp4_path)
        tag = "✅キャッシュ" if hit else "🔨レンダリング"
        _prog(progress_state, 0.4 + (i + 1) / n * 0.55, f"{tag}: {label}")

    if cancel_flag and cancel_flag.get("flag"):
        if progress_state: progress_state["done"] = True
        return

    # ===================================================
    # Phase 3: 最終結合（ffmpeg concat → moviepy fallback）
    # ===================================================
    if scene_mp4_list:
        _prog(progress_state, 0.96, "最終結合中...")
        filelist = os.path.join(SCENE_CACHE_DIR, "_concat.txt")
        with open(filelist, "w", encoding="utf-8") as f:
            for p in scene_mp4_list:
                f.write(f"file '{os.path.abspath(p)}'\n")
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", filelist, "-c", "copy", output_filename],
            capture_output=True
        )
        try: os.remove(filelist)
        except: pass

        if result.returncode != 0:
            # ffmpeg 失敗時は moviepy でフォールバック
            clips = [VideoFileClip(p) for p in scene_mp4_list]
            final = concatenate_videoclips(clips, method="compose")
            final.write_videofile(output_filename, fps=FPS, codec="libx264",
                                  preset="ultrafast", threads=4, logger=None)
            final.close()
            for c in clips:
                try: c.close()
                except: pass

        _prog(progress_state, 1.0, "完了！")

    if progress_state is not None:
        progress_state["done"] = True


# ==========================================
# 5. UI構築
# ==========================================
st.set_page_config(page_title="Custom Vlog Maker", layout="wide")
st.title("🎬 AI Vertical Vlog Maker")

# --- session_state 初期化 ---
for key, default in [
    ("video_history",      []),
    ("scene_order",        []),
    ("added_main_files",   set()),
    ("new_scene_count",    0),
    ("style_templates",    {}),
    ("is_building",          False),
    ("build_cancel",         {}),
    ("build_progress",       {}),
    ("build_output_path",    ""),
    ("show_quality_preview", False),
    ("storyboard_cache",     {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

temp_dir = "temp_uploads"
se_dir   = os.path.join("assets", "se")
font_dir = os.path.join("assets", "fonts")
for d in [temp_dir, se_dir, font_dir]:
    os.makedirs(d, exist_ok=True)

# ★ 新機能② ビルトインテンプレート定義
BUILTIN_TEMPLATES = {
    "🔴 赤テロップ（デフォ）": {"tc": "#FFFFFF", "sc": "#000000", "ac": "#FF0000", "as": 1.3, "sw": 16},
    "🟡 黄ハイライト":         {"tc": "#FFFF00", "sc": "#000000", "ac": "#FF8800", "as": 1.4, "sw": 14},
    "⚪ シンプル白":            {"tc": "#FFFFFF", "sc": "#000000", "ac": "#FFFFFF", "as": 1.0, "sw": 10},
    "🔵 クール青":              {"tc": "#FFFFFF", "sc": "#001840", "ac": "#00BFFF", "as": 1.3, "sw": 18},
    "🟢 ナチュラル緑":          {"tc": "#F0FFF0", "sc": "#003300", "ac": "#00DD77", "as": 1.2, "sw": 14},
}

# ==========================================
# サイドバー
# ==========================================
with st.sidebar:
    st.header("⚙️ 全体設定")
    selected_voice = st.selectbox(
        "ナレーション",
        ["青山龍星（渋い低音）", "玄野武宏（爽やか）", "剣崎雌雄（しっかり）", "ずんだもん"])
    voice_map = {
        "青山龍星（渋い低音）": 13,
        "玄野武宏（爽やか）":   11,
        "剣崎雌雄（しっかり）": 21,
        "ずんだもん":            3,
    }
    selected_speed = st.slider("🎙️ 音声スピード（全体デフォルト）", 0.5, 2.0, 1.5, 0.1)

    st.divider()
    st.markdown("**📝 フォント設定**")
    uploaded_font = st.file_uploader("📂 フォントをUP (.ttf / .otf)", type=["ttf", "otf"])
    if uploaded_font is not None:
        final_font_path = os.path.join(font_dir, uploaded_font.name)
        with open(final_font_path, "wb") as f:
            f.write(uploaded_font.getbuffer())
        st.success(f"✅ {uploaded_font.name} を適用！")
    else:
        st.caption("デフォルトのフォントを選択:")
        selected_font = st.selectbox(
            "使用フォント",
            ["メイリオ Bold", "游ゴシック Bold", "MS ゴシック"],
            label_visibility="collapsed")
        font_map = {
            "メイリオ Bold":   "C:/Windows/Fonts/meiryob.ttc",
            "游ゴシック Bold": "C:/Windows/Fonts/YuGothB.ttc",
            "MS ゴシック":     "C:/Windows/Fonts/msgothic.ttc",
        }
        final_font_path = font_map[selected_font]

    st.divider()
    st.markdown("**🎵 効果音（SE）の追加**")
    uploaded_se = st.file_uploader("📂 効果音をUP (.mp3 / .wav)", type=["mp3", "wav"])
    if uploaded_se is not None:
        final_se_path = os.path.join(se_dir, uploaded_se.name)
        with open(final_se_path, "wb") as f:
            f.write(uploaded_se.getbuffer())
        st.success(f"✅ {uploaded_se.name} を追加！")

    # ★ 新機能② スタイルテンプレート管理
    st.divider()
    st.header("🎨 スタイルテンプレート")
    st.caption("現在のシーン設定を名前をつけて保存できます")

    save_tmpl_name = st.text_input("テンプレート名", placeholder="例: 筋トレ系テロップ")
    save_tmpl_scene = st.selectbox(
        "どのシーンから保存？",
        options=st.session_state.scene_order if st.session_state.scene_order else ["（シーンなし）"],
        label_visibility="visible"
    )
    if st.button("💾 テンプレートとして保存", use_container_width=True):
        if save_tmpl_name and save_tmpl_scene in st.session_state.scene_order:
            st.session_state.style_templates[save_tmpl_name] = {
                "tc": st.session_state.get(f"tc_{save_tmpl_scene}", "#FFFFFF"),
                "sc": st.session_state.get(f"sc_{save_tmpl_scene}", "#000000"),
                "ac": st.session_state.get(f"ac_{save_tmpl_scene}", "#FF0000"),
                "as": st.session_state.get(f"as_{save_tmpl_scene}", 1.3),
                "sw": st.session_state.get(f"sw_{save_tmpl_scene}", 16),
            }
            st.success(f"✅ 「{save_tmpl_name}」を保存！")

    if st.session_state.style_templates:
        del_name = st.selectbox(
            "保存済みテンプレートを削除",
            options=list(st.session_state.style_templates.keys()),
            label_visibility="visible"
        )
        if st.button("🗑️ 削除", use_container_width=True):
            del st.session_state.style_templates[del_name]
            st.rerun()

    st.divider()
    st.header("💾 プロジェクト管理")

    export_dict = {}
    for name in st.session_state.scene_order:
        export_dict[name] = {
            "txt":  st.session_state.get(f"txt_{name}", ""),
            "pos":  st.session_state.get(f"pos_{name}", "中央"),
            "tc":   st.session_state.get(f"tc_{name}",  "#FFFFFF"),
            "sc":   st.session_state.get(f"sc_{name}",  "#000000"),
            "ac":   st.session_state.get(f"ac_{name}",  "#FF0000"),
            "as":   st.session_state.get(f"as_{name}",  1.3),
            "sw":   st.session_state.get(f"sw_{name}",  16),
            "eff":  st.session_state.get(f"eff_{name}", "なし"),
            "fi":   st.session_state.get(f"fi_{name}",  False),
            "fo":   st.session_state.get(f"fo_{name}",  False),
            "ta":   st.session_state.get(f"ta_{name}",  "なし"),
            "trim": st.session_state.get(f"trim_{name}", 0.0),
            "spd":  st.session_state.get(f"spd_{name}",  selected_speed),
            "nse":  st.session_state.get(f"nse_{name}",  0),
        }
        for j in range(export_dict[name]["nse"]):
            export_dict[name][f"sen_{j}"] = st.session_state.get(f"sen_{name}_{j}", "なし")
            export_dict[name][f"set_{j}"] = st.session_state.get(f"set_{name}_{j}", 0.0)

    export_dict["thumbnail_data"] = {
        "text": st.session_state.get("thumb_text", ""),
        "op":   st.session_state.get("thumb_op",   50),
        "fs":   st.session_state.get("thumb_fs",   130),
        "sw":   st.session_state.get("thumb_sw",   24),
    }
    export_dict["style_templates"] = st.session_state.style_templates  # ★ テンプレートも保存

    st.download_button(
        "⬇️ 現在の台本を保存",
        data=json.dumps(export_dict, ensure_ascii=False, indent=2),
        file_name="vlog_project.json",
        mime="application/json",
        use_container_width=True
    )

    uploaded_json = st.file_uploader("⬆️ 台本を読み込む", type="json")
    if uploaded_json is not None:
        if st.button("🔄 設定を復元する", use_container_width=True):
            import_dict = json.load(uploaded_json)
            st.session_state.scene_order      = [k for k in import_dict if k not in ("thumbnail_data", "style_templates")]
            st.session_state.added_main_files = set(st.session_state.scene_order)

            if "style_templates" in import_dict:
                st.session_state.style_templates = import_dict["style_templates"]  # ★ 復元

            if "thumbnail_data" in import_dict:
                td = import_dict["thumbnail_data"]
                for k, v in [("thumb_text", td.get("text", "")),
                              ("thumb_op",   td.get("op",   50)),
                              ("thumb_fs",   td.get("fs",   130)),
                              ("thumb_sw",   td.get("sw",   24))]:
                    st.session_state[k] = v

            for name in st.session_state.scene_order:
                data = import_dict[name]
                st.session_state[f"txt_{name}"]  = data.get("txt",  "")
                st.session_state[f"pos_{name}"]  = data.get("pos",  "中央")
                st.session_state[f"tc_{name}"]   = data.get("tc",   "#FFFFFF")
                st.session_state[f"sc_{name}"]   = data.get("sc",   "#000000")
                st.session_state[f"ac_{name}"]   = data.get("ac",   "#FF0000")
                st.session_state[f"as_{name}"]   = data.get("as",   1.3)
                st.session_state[f"sw_{name}"]   = data.get("sw",   16)
                st.session_state[f"eff_{name}"]  = data.get("eff",  "なし")
                st.session_state[f"fi_{name}"]   = data.get("fi",   False)
                st.session_state[f"fo_{name}"]   = data.get("fo",   False)
                st.session_state[f"ta_{name}"]   = data.get("ta",   "なし")
                st.session_state[f"trim_{name}"] = data.get("trim", 0.0)
                st.session_state[f"spd_{name}"]  = data.get("spd",  1.5)
                nse = data.get("nse", 0)
                st.session_state[f"nse_{name}"]  = nse
                for j in range(nse):
                    st.session_state[f"sen_{name}_{j}"] = data.get(f"sen_{j}", "なし")
                    st.session_state[f"set_{name}_{j}"] = data.get(f"set_{j}", 0.0)

            st.session_state.restore_success = True
            st.rerun()

    if st.session_state.get("restore_success"):
        st.success("✅ 台本を復元しました！")
        st.session_state.restore_success = False

    # ---- CSV インポート / エクスポート ----
    st.divider()
    st.header("📄 字幕 CSV")
    st.caption("列順: シーン番号, テキスト, スピード（省略可）")

    # CSV エクスポート
    csv_rows = [["scene", "text", "speed"]]
    for idx, name in enumerate(st.session_state.scene_order, 1):
        csv_rows.append([
            idx,
            st.session_state.get(f"txt_{name}", ""),
            st.session_state.get(f"spd_{name}", 1.5),
        ])
    csv_buf = io.StringIO()
    csv.writer(csv_buf).writerows(csv_rows)
    st.download_button("⬇️ 字幕を CSV で保存", data=csv_buf.getvalue(),
                       file_name="subtitles.csv", mime="text/csv",
                       use_container_width=True)

    # CSV インポート
    uploaded_csv = st.file_uploader("⬆️ 字幕 CSV を読み込む", type="csv", key="csv_upload")
    if uploaded_csv is not None:
        if st.button("📥 CSV から字幕を一括設定", use_container_width=True):
            content = uploaded_csv.read().decode("utf-8-sig")
            reader  = csv.reader(io.StringIO(content))
            next(reader, None)   # ヘッダーをスキップ
            updated = 0
            for row in reader:
                if not row:
                    continue
                try:
                    scene_idx = int(row[0]) - 1
                    if 0 <= scene_idx < len(st.session_state.scene_order):
                        n = st.session_state.scene_order[scene_idx]
                        if len(row) > 1:
                            st.session_state[f"txt_{n}"] = row[1]
                        if len(row) > 2:
                            st.session_state[f"spd_{n}"] = float(row[2])
                        updated += 1
                except (ValueError, IndexError):
                    continue
            st.success(f"✅ {updated} シーンの字幕を更新しました！")
            st.rerun()

se_files = ["なし"] + [f for f in os.listdir(se_dir) if f.endswith(('.mp3', '.wav'))]

# ==========================================
# メインエリア
# ==========================================
st.header("1. 動画の作成")

# ★ 新機能④ 一括設定パネル
with st.expander("⚡ 全シーンに一括適用", expanded=False):
    st.caption("チェックした項目だけを全シーンに上書きします")
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        bulk_tc_on = st.checkbox("文字色を統一")
        bulk_tc    = st.color_picker("文字色##bulk", "#FFFFFF", disabled=not bulk_tc_on)
        bulk_sc_on = st.checkbox("フチ色を統一")
        bulk_sc    = st.color_picker("フチ色##bulk", "#000000", disabled=not bulk_sc_on)
        bulk_ac_on = st.checkbox("強調色を統一")
        bulk_ac    = st.color_picker("強調色##bulk", "#FF0000", disabled=not bulk_ac_on)
    with bc2:
        bulk_sw_on  = st.checkbox("フチ太さを統一")
        bulk_sw     = st.slider("フチ太さ##bulk", 0, 30, 16, disabled=not bulk_sw_on)
        bulk_as_on  = st.checkbox("強調拡大率を統一")
        bulk_as     = st.slider("拡大率##bulk", 1.0, 2.0, 1.3, disabled=not bulk_as_on)
        bulk_spd_on = st.checkbox("音声スピードを統一")
        bulk_spd    = st.slider("スピード##bulk", 0.5, 2.0, selected_speed, 0.1, disabled=not bulk_spd_on)
    with bc3:
        bulk_eff_on = st.checkbox("カメラワークを統一")
        bulk_eff    = st.selectbox("カメラワーク##bulk", ["なし","ズームイン","ズームアウト","右へスライド","左へスライド"], disabled=not bulk_eff_on)
        bulk_pos_on = st.checkbox("テキスト位置を統一")
        bulk_pos    = st.selectbox("位置##bulk", ["中央","上部","下部"], disabled=not bulk_pos_on)
        bulk_fi_on  = st.checkbox("フェードイン全ON")
        bulk_fo_on  = st.checkbox("フェードアウト全ON")

    if st.button("🚀 選択した設定を全シーンに反映", type="primary", use_container_width=True):
        for name in st.session_state.scene_order:
            if bulk_tc_on:  st.session_state[f"tc_{name}"]  = bulk_tc
            if bulk_sc_on:  st.session_state[f"sc_{name}"]  = bulk_sc
            if bulk_ac_on:  st.session_state[f"ac_{name}"]  = bulk_ac
            if bulk_sw_on:  st.session_state[f"sw_{name}"]  = bulk_sw
            if bulk_as_on:  st.session_state[f"as_{name}"]  = bulk_as
            if bulk_spd_on: st.session_state[f"spd_{name}"] = bulk_spd
            if bulk_eff_on: st.session_state[f"eff_{name}"] = bulk_eff
            if bulk_pos_on: st.session_state[f"pos_{name}"] = bulk_pos
            if bulk_fi_on:  st.session_state[f"fi_{name}"]  = True
            if bulk_fo_on:  st.session_state[f"fo_{name}"]  = True
        st.success("✅ 全シーンに反映しました！")
        st.rerun()

uploaded_files = st.file_uploader(
    "📂 ここに動画を入れると末尾にドンドン追加されます",
    type=['jpg','png','mp4'], accept_multiple_files=True)
file_dict = {}

if uploaded_files:
    for f in uploaded_files:
        file_dict[f.name] = f
        if f.name not in st.session_state.added_main_files:
            st.session_state.scene_order.append(f.name)
            st.session_state.added_main_files.add(f.name)

if st.button("➕ 新しい空のシーンを追加", use_container_width=True):
    st.session_state.new_scene_count += 1
    st.session_state.scene_order.append(f"追加シーン_{st.session_state.new_scene_count}")
    st.rerun()

# ★ 新機能③ ドラッグ&ドロップ並び替え
try:
    from streamlit_sortables import sort_items
    st.markdown("**🔀 シーンをドラッグして並び替え**")
    new_order = sort_items(
        [f"シーン {i+1}: {n if '追加シーン' not in n else '空のシーン'}"
         for i, n in enumerate(st.session_state.scene_order)],
        direction="vertical",
        key="scene_sort"
    )
    # ラベルからインデックスを抽出して scene_order を並び替え
    sorted_indices = []
    for label in new_order:
        for i, n in enumerate(st.session_state.scene_order):
            display = f"シーン {i+1}: {n if '追加シーン' not in n else '空のシーン'}"
            if display == label and i not in sorted_indices:
                sorted_indices.append(i)
                break
    new_scene_order = [st.session_state.scene_order[i] for i in sorted_indices]
    if new_scene_order != st.session_state.scene_order:
        st.session_state.scene_order = new_scene_order
        st.rerun()
except ImportError:
    st.caption("💡 `pip install streamlit-sortables` でドラッグ&ドロップが使えます")

# --- シーンカード ---
scenes_data    = []
scenes_to_remove = []

for i, name in enumerate(st.session_state.scene_order):
    counter_key = f"repl_counter_{name}"
    if counter_key not in st.session_state:
        st.session_state[counter_key] = 0
    replace_key = f"repl_upl_{name}_{st.session_state[counter_key]}"

    if replace_key in st.session_state and st.session_state[replace_key] is not None:
        repl_file = st.session_state[replace_key]
        st.session_state[f"ovr_bytes_{name}"] = repl_file.getvalue()
        st.session_state[f"ovr_ext_{name}"]   = repl_file.name.split('.')[-1].lower()
        st.session_state[counter_key] += 1
        st.rerun()

    has_media   = False
    media_bytes = None
    ext         = None

    if f"ovr_bytes_{name}" in st.session_state:
        media_bytes = st.session_state[f"ovr_bytes_{name}"]
        ext         = st.session_state[f"ovr_ext_{name}"]
        has_media   = True
    elif name in file_dict:
        media_bytes = file_dict[name].getvalue()
        ext         = name.split('.')[-1].lower()
        has_media   = True

    with st.container(border=True):
        col_h, col_u, col_d, col_clone, col_del = st.columns([5, 1, 1, 1, 1.5])
        col_h.subheader(f"シーン {i+1}: {name if '追加シーン' not in name else '空のシーン'}")

        if i > 0 and col_u.button("⬆️", key=f"u{name}"):
            st.session_state.scene_order[i], st.session_state.scene_order[i-1] = \
                st.session_state.scene_order[i-1], st.session_state.scene_order[i]
            st.rerun()
        if i < len(st.session_state.scene_order) - 1 and col_d.button("⬇️", key=f"d{name}"):
            st.session_state.scene_order[i], st.session_state.scene_order[i+1] = \
                st.session_state.scene_order[i+1], st.session_state.scene_order[i]
            st.rerun()
        if col_clone.button("📋", key=f"clone{name}", help="このシーンを複製"):
            st.session_state.new_scene_count += 1
            new_name = f"追加シーン_{st.session_state.new_scene_count}"
            idx = st.session_state.scene_order.index(name)
            st.session_state.scene_order.insert(idx + 1, new_name)
            for k in ["txt","pos","tc","sc","ac","as","sw","eff","fi","fo","ta","trim","spd","nse"]:
                if f"{k}_{name}" in st.session_state:
                    st.session_state[f"{k}_{new_name}"] = st.session_state[f"{k}_{name}"]
            nse_count = st.session_state.get(f"nse_{name}", 0)
            for j in range(nse_count):
                for sk in ["sen", "set"]:
                    if f"{sk}_{name}_{j}" in st.session_state:
                        st.session_state[f"{sk}_{new_name}_{j}"] = st.session_state[f"{sk}_{name}_{j}"]
            if f"ovr_bytes_{name}" in st.session_state:
                st.session_state[f"ovr_bytes_{new_name}"] = st.session_state[f"ovr_bytes_{name}"]
                st.session_state[f"ovr_ext_{new_name}"]   = st.session_state[f"ovr_ext_{name}"]
            elif name in file_dict:
                st.session_state[f"ovr_bytes_{new_name}"] = file_dict[name].getvalue()
                st.session_state[f"ovr_ext_{new_name}"]   = name.split('.')[-1].lower()
            st.rerun()
        if col_del.button("🗑️ 削除", key=f"del{name}"):
            scenes_to_remove.append(name)

        c1, c2, c3 = st.columns([1, 2, 1])

        with c1:
            if has_media:
                if ext in ['mp4', 'mov']:
                    st.video(media_bytes)
                else:
                    st.image(media_bytes)
                st.file_uploader("🔄 差し替え", type=['mp4','mov','jpg','png'],
                                  key=replace_key, label_visibility="visible")
            else:
                st.info("👈 ここに動画/画像をドロップ")
                st.file_uploader("📥 新規アップロード", type=['mp4','mov','jpg','png'],
                                  key=replace_key, label_visibility="collapsed")

        with c2:
            st.caption("💡 フリガナ: `*大胸筋*|だいきょうきん`　息継ぎ: 末尾に `。` や `、`")
            txt = st.text_area("テキスト", key=f"txt_{name}",
                                placeholder="今日は\n*大胸筋*|だいきょうきん を\n追い込みます！")
            wrap_c1, wrap_c2 = st.columns([1, 2])
            max_wrap = wrap_c1.number_input("改行幅(文字)", 5, 30, 13, key=f"wrap_n_{name}")
            if wrap_c2.button("↩ 自動改行", key=f"wrap_btn_{name}", use_container_width=True):
                st.session_state[f"txt_{name}"] = auto_wrap_text(txt, int(max_wrap))
                st.rerun()

            # ★ 新機能② テンプレート適用UI
            all_templates = {**BUILTIN_TEMPLATES, **st.session_state.style_templates}
            tmpl_names    = list(all_templates.keys())
            sel_tmpl = st.selectbox("🎨 スタイルテンプレートを適用", ["選択してください"] + tmpl_names,
                                     key=f"tmpl_sel_{name}")
            if sel_tmpl != "選択してください" and st.button("✨ このシーンに適用", key=f"tmpl_apply_{name}"):
                t = all_templates[sel_tmpl]
                st.session_state[f"tc_{name}"] = t["tc"]
                st.session_state[f"sc_{name}"] = t["sc"]
                st.session_state[f"ac_{name}"] = t["ac"]
                st.session_state[f"as_{name}"] = t["as"]
                st.session_state[f"sw_{name}"] = t["sw"]
                st.rerun()

            c_pos, c_anim, c_trim, c_spd = st.columns([1, 1, 1, 1])
            pos      = c_pos.selectbox("📌 位置", ["中央","上部","下部"], key=f"pos_{name}")
            anim     = c_anim.selectbox("🔤 アニメ", ["なし","ポップイン","スライドアップ"], key=f"ta_{name}")
            trim_val = c_trim.number_input("✂️ 開始秒", 0.0, 600.0, 0.0, 0.1, key=f"trim_{name}")
            # ★ シーンごとのスピード
            spd_val  = c_spd.number_input("🎙️ スピード", 0.5, 2.0,
                                           float(st.session_state.get(f"spd_{name}", selected_speed)),
                                           0.1, key=f"spd_{name}")

            cc1, cc2, cc3, cc4, cc5 = st.columns([1, 1, 1, 1.3, 1.3])
            t_col = cc1.color_picker("文字色", "#FFFFFF", key=f"tc_{name}")
            s_col = cc2.color_picker("フチ色",   "#000000", key=f"sc_{name}")
            a_col = cc3.color_picker("強調色",   "#FF0000", key=f"ac_{name}")
            a_scl = cc4.slider("拡大率", 1.0, 2.0, 1.3, key=f"as_{name}")
            s_wid = cc5.slider("フチ太さ", 0, 30, 16,   key=f"sw_{name}")

            ec1, ec2, ec3 = st.columns([2, 1, 1])
            eff   = ec1.selectbox("カメラワーク",
                                   ["なし","ズームイン","ズームアウト","右へスライド","左へスライド"],
                                   key=f"eff_{name}")
            f_in  = ec2.checkbox("F-In",  key=f"fi_{name}")
            f_out = ec3.checkbox("F-Out", key=f"fo_{name}")

            with st.expander("🎵 効果音（SE）設定"):
                num_se        = st.number_input("効果音の数", 0, 5, 0, key=f"nse_{name}")
                scene_se_list = []
                for j in range(num_se):
                    sc_se1, sc_se2 = st.columns([3, 2])
                    se_name  = sc_se1.selectbox("種類", se_files,
                                                 key=f"sen_{name}_{j}",
                                                 label_visibility="collapsed")
                    se_time  = sc_se2.number_input("開始秒数", 0.0, 30.0, 0.0, 0.1,
                                                    key=f"set_{name}_{j}")
                    if se_name != "なし":
                        se_path = os.path.join(se_dir, se_name)
                        if os.path.exists(se_path):
                            sc_se1.audio(se_path)
                    scene_se_list.append({"name": se_name, "start_time": se_time})
                    st.write("")

            if has_media:
                final_filename = f"scene_export_{i}.{ext}"
                p = os.path.join(temp_dir, final_filename)
                if not os.path.exists(p) or os.path.getsize(p) != len(media_bytes):
                    with open(p, "wb") as _f:
                        _f.write(media_bytes)
                scenes_data.append({
                    "file":         p,
                    "text":         txt,
                    "text_color":   t_col,
                    "stroke_color": s_col,
                    "accent_color": a_col,
                    "accent_scale": a_scl,
                    "stroke_width": s_wid,
                    "effect":       eff,
                    "fade_in":      f_in,
                    "fade_out":     f_out,
                    "sound_effects": scene_se_list,
                    "text_position": pos,
                    "text_anim":    anim,
                    "trim_start":   trim_val,
                    "speed_scale":  spd_val,
                })

        # ★ 新機能① リアルタイムプレビュー
        with c3:
            st.caption("👁 字幕プレビュー")
            if txt.strip():
                try:
                    visual_text = txt
                    # フリガナ処理（ビジュアル用）
                    v_preview, _ = process_furigana(visual_text)
                    v_preview    = v_preview.replace('、','').replace('。','')
                    preview_img  = create_subtitle_preview(
                        v_preview, final_font_path,
                        target_w=270, target_h=480,
                        text_color=t_col, stroke_color=s_col,
                        accent_color=a_col, accent_scale=a_scl,
                        position=pos, stroke_width=s_wid
                    )
                    st.image(preview_img, use_container_width=True)
                except Exception as e:
                    st.caption(f"プレビュー生成エラー: {e}")
            else:
                st.info("テキストを入力するとプレビューが表示されます")

if scenes_to_remove:
    for name in scenes_to_remove:
        st.session_state.scene_order.remove(name)
        if name in st.session_state.added_main_files:
            st.session_state.added_main_files.remove(name)
    st.rerun()

# ==========================================
# ストーリーボードビュー
# ==========================================
with st.expander("📋 ストーリーボードビュー", expanded=False):
    if not scenes_data:
        st.info("シーンを追加するとここに一覧表示されます")
    else:
        BOARD_COLS = 4
        cols = st.columns(BOARD_COLS)
        sb_cache = st.session_state.storyboard_cache
        for i, scene in enumerate(scenes_data):
            fp   = scene["file"]
            txt  = (scene["text"].split('\n')[0])[:18] + ("…" if len(scene["text"]) > 18 else "")
            key  = fp
            with cols[i % BOARD_COLS]:
                if key not in sb_cache:
                    img = _get_scene_thumbnail(fp)
                    sb_cache[key] = img
                else:
                    img = sb_cache[key]
                if img is not None:
                    st.image(img, use_container_width=True)
                else:
                    st.write("🎬")
                st.caption(f"**{i+1}** {txt}")
                eff_icon = {"ズームイン": "🔍+", "ズームアウト": "🔍-",
                            "右へスライド": "➡️", "左へスライド": "⬅️"}.get(scene["effect"], "")
                fi_fo = ("F-In " if scene["fade_in"] else "") + ("F-Out" if scene["fade_out"] else "")
                if eff_icon or fi_fo:
                    st.caption(f"{eff_icon} {fi_fo}")

# ==========================================
# サムネイル設定
# ==========================================
st.divider()
st.header("2. サムネイル（カバー画像）の仕込み")
st.info("💡 文字を入力しておくと、動画書き出し時に自動で「0.1秒の表紙」を先頭に付けます。")

use_thumb    = st.checkbox("🖼️ 冒頭にサムネイルを仕込む", value=True)
thumb_settings = None

if use_thumb:
    col_t1, col_t2, col_t3 = st.columns([1, 1, 1])
    with col_t1:
        thumb_file    = st.file_uploader("別の背景を使う場合のみUP", type=['jpg','png','mp4','mov'], key="thumb_file")
        thumb_text    = st.text_area("サムネイルの文字", placeholder="スクワット\n基本のフォーム", key="thumb_text")
        thumb_opacity = st.slider("黒フィルターの濃さ (%)", 0, 100, 50, key="thumb_op")
    with col_t2:
        thumb_font_size = st.slider("文字サイズ", 50, 250, 130, key="thumb_fs")
        thumb_stroke    = st.slider("フチの太さ",   0,  40,  24, key="thumb_sw")

    bg_path_for_thumb = ""
    if thumb_file:
        bg_path_for_thumb = os.path.join(temp_dir, f"thumb_bg_{thumb_file.name}")
        with open(bg_path_for_thumb, "wb") as f:
            f.write(thumb_file.getbuffer())
    elif scenes_data:
        bg_path_for_thumb = scenes_data[0]["file"]

    with col_t3:
        st.caption("👁 サムネイルプレビュー")
        if thumb_text.strip():
            try:
                prev_thumb = generate_thumbnail(
                    bg_path_for_thumb, thumb_text,
                    thumb_opacity, final_font_path,
                    thumb_font_size, thumb_stroke,
                    target_w=270, target_h=480)
                st.image(prev_thumb, use_container_width=True)
            except Exception as e:
                st.caption(f"プレビューエラー: {e}")
        else:
            st.info("文字を入力するとプレビューが表示されます")

    thumb_settings = {
        "use_thumb":    True,
        "bg_file":      bg_path_for_thumb,
        "text":         thumb_text,
        "opacity":      thumb_opacity,
        "font_size":    thumb_font_size,
        "stroke_width": thumb_stroke,
    }

# ==========================================
# 書き出し
# ==========================================
st.divider()
st.header("3. 書き出し")
is_draft_mode = st.checkbox("⚡ テスト用軽量モード（低解像度で高速書き出し）", value=True)

# ドラフト vs 本番 品質比較プレビュー
if st.button("🔍 ドラフト vs 本番 プレビュー", use_container_width=True):
    st.session_state.show_quality_preview = not st.session_state.show_quality_preview

if st.session_state.show_quality_preview and scenes_data:
    first = scenes_data[0]
    v_prev, _ = process_furigana(first["text"])
    v_prev = v_prev.replace('、','').replace('。','')
    if v_prev.strip():
        qc1, qc2 = st.columns(2)
        with qc1:
            st.caption("⚡ ドラフト品質（360×640）")
            try:
                img_d = create_subtitle_preview(
                    v_prev, final_font_path, 360, 640,
                    first["text_color"], first["stroke_color"],
                    first["accent_color"], first["accent_scale"],
                    first["text_position"], first["stroke_width"])
                st.image(img_d, use_container_width=True)
            except Exception as e:
                st.caption(f"エラー: {e}")
        with qc2:
            st.caption("✨ 本番品質（720×1280）")
            try:
                img_p = create_subtitle_preview(
                    v_prev, final_font_path, 720, 1280,
                    first["text_color"], first["stroke_color"],
                    first["accent_color"], first["accent_scale"],
                    first["text_position"], first["stroke_width"])
                st.image(img_p, use_container_width=True)
            except Exception as e:
                st.caption(f"エラー: {e}")
    else:
        st.info("シーン1にテキストを入力するとプレビューが表示されます")

# 書き出し実行 / キャンセル
if st.session_state.is_building:
    ps = st.session_state.build_progress
    st.progress(ps.get("value", 0), text=ps.get("text", "処理中..."))
    if st.button("⏹ キャンセル", type="secondary", use_container_width=True):
        st.session_state.build_cancel["flag"] = True
    if ps.get("done"):
        st.session_state.is_building = False
        if not ps.get("cancelled"):
            out_path = st.session_state.build_output_path
            if out_path and os.path.exists(out_path):
                st.session_state.video_history.append(out_path)
        st.rerun()
    else:
        time.sleep(0.5)
        st.rerun()
else:
    if st.button("✨ 動画を生成開始", type="primary", use_container_width=True):
        if scenes_data:
            cancel_flag    = {"flag": False}
            progress_state = {"value": 0, "text": "開始中...", "done": False, "cancelled": False}
            out = f"vlog_{int(time.time())}.mp4"
            st.session_state.build_cancel       = cancel_flag
            st.session_state.build_progress     = progress_state
            st.session_state.build_output_path  = out
            st.session_state.is_building        = True

            _scenes = scenes_data[:]
            _font   = final_font_path
            _se_dir = se_dir
            _thumb  = thumb_settings
            _draft  = is_draft_mode
            _voice  = voice_map[selected_voice]
            _speed  = selected_speed

            def _run_build():
                try:
                    build_vlog(_scenes, out, _font, _se_dir, _thumb, _draft,
                               _voice, speed_scale=_speed,
                               progress_state=progress_state, cancel_flag=cancel_flag)
                except Exception as e:
                    progress_state["text"]      = f"エラー: {e}"
                    progress_state["cancelled"] = True
                finally:
                    progress_state["done"] = True

            threading.Thread(target=_run_build, daemon=True).start()
            st.rerun()
        else:
            st.warning("⚠️ 動画の入ったシーンが1つもありません！")

if st.session_state.video_history:
    st.header("🎞️ 履歴")
    for vid in reversed(st.session_state.video_history):
        if os.path.exists(vid):
            st.video(vid)