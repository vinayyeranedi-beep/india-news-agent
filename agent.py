#!/usr/bin/env python3
"""
Minute News Agent — Complete 24/7 Auto Post Backend
Author: Vinay Yeranedi
Channel: Minute News (@minutenewsindia)

Platforms: Instagram + Facebook + YouTube
Language: Telugu + English
Topics: Cricket, Bollywood, Politics, World, Tech, Business
Schedule: 7AM, 11AM, 3PM, 7PM, 9PM IST (via GitHub Actions)
Image: Gemini AI (breaking news) + Template (regular news)
Tone: Classic Cinematic
"""

import os, requests, json, time, math, wave, struct, base64
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from io import BytesIO
import google.generativeai as genai

# ═══ KEYS FROM GITHUB SECRETS ════════════════════════════════════════
GEMINI_KEY      = os.environ.get('GEMINI_KEY', '')
GNEWS_KEY       = os.environ.get('GNEWS_KEY', '')
META_TOKEN      = os.environ.get('META_ACCESS_TOKEN', '')
FB_PAGE_ID      = os.environ.get('FB_PAGE_ID', '114140219905300')
INSTAGRAM_ID    = os.environ.get('INSTAGRAM_ID', '')   # add later
YT_API_KEY      = os.environ.get('YT_API_KEY', '')
YT_CHANNEL_ID   = os.environ.get('YT_CHANNEL', '')

# ═══ CONFIG ═══════════════════════════════════════════════════════════
GEMINI_DAILY_LIMIT = 20
img_count = 0

# Platform specs — all 9:16
PLATFORMS = {
    'instagram': {'w': 1080, 'h': 1920, 'ratio': '9:16'},
    'facebook':  {'w': 1080, 'h': 1920, 'ratio': '9:16'},
    'youtube':   {'w': 1080, 'h': 1920, 'ratio': '9:16'},
}

# ═══ CAPTIONS (Telugu + English) ══════════════════════════════════════
CAPTIONS = {
    'Cricket':  '🏏 క్రికెట్ అప్‌డేట్!\n\n{title}\n\n📺 {src}\n\n#Cricket #India #TeamIndia #IPL #MinuteNews #TeluguNews',
    'Bollywood':'🎬 బాలీవుడ్ వార్త!\n\n{title}\n\n📺 {src}\n\n#Bollywood #Cinema #Telugu #MinuteNews #Entertainment',
    'Politics': '🏛️ రాజకీయ వార్త\n\n{title}\n\n📺 {src}\n\n#Politics #India #Breaking #MinuteNews #TeluguNews',
    'World':    '🌍 ప్రపంచ వార్త\n\n{title}\n\n📺 {src}\n\n#WorldNews #India #Breaking #MinuteNews',
    'Tech':     '💻 టెక్ వార్త\n\n{title}\n\n📺 {src}\n\n#Technology #India #Jio #MinuteNews #Tech',
    'Business': '📈 వ్యాపార వార్త\n\n{title}\n\n📺 {src}\n\n#Business #India #Economy #MinuteNews',
}

# ═══ IMAGE PROMPTS (Classic Cinematic Tone) ════════════════════════════
PROMPTS = {
    'Cricket':  'Cricket match India stadium packed crowd night, batsman hitting six, roaring fans waving Indian flags, dramatic floodlights, classic film photography, warm sepia tones, vintage cinema, Kodachrome color grade, 35mm film grain, golden light, 9:16 vertical',
    'Bollywood':'Bollywood premiere night Mumbai, red carpet, blinding camera flashes, luxury cars, giant movie billboard, warm golden lights, classic film photography, vintage cinema aesthetic, sepia warm tones, 9:16 vertical',
    'Politics': 'Indian parliament building New Delhi dawn, Indian tricolor flag waving, majestic government architecture, dramatic golden sky, classic film photography, warm sepia, vintage journalism style, 9:16 vertical',
    'World':    'India global news concept, dramatic lighting, breaking news broadcast, Indian flag, classic photojournalism, warm sepia tones, vintage film grain, 9:16 vertical',
    'Tech':     'Futuristic Mumbai cityscape night, glowing 6G network, fiber optic light trails, digital India concept, classic warm tones over neon, 9:16 vertical',
    'Business': 'Mumbai financial district Nariman Point golden hour, rising stock charts, modern glass towers, prosperity concept, classic film photography, warm golden tones, 9:16 vertical',
}

# ═══ FETCH NEWS ════════════════════════════════════════════════════════
def fetch_news():
    """Fetch top Indian news from GNews API."""
    print('\n[NEWS] Fetching from GNews API...')
    articles = []
    topics = [
        'cricket india', 'bollywood', 'india politics',
        'india world news', 'india technology', 'india business'
    ]
    for topic in topics[:4]:
        try:
            url = f'https://gnews.io/api/v4/search?q={topic}&lang=en&country=in&max=2&token={GNEWS_KEY}'
            r = requests.get(url, timeout=10)
            data = r.json()
            articles.extend(data.get('articles', []))
            time.sleep(0.5)
        except Exception as e:
            print(f'[WARN] GNews error for {topic}: {e}')

    # Remove duplicates
    seen, unique = set(), []
    for a in articles:
        if a['title'] not in seen:
            seen.add(a['title'])
            unique.append(a)

    print(f'[NEWS] Found {len(unique)} articles')
    return unique[:5]

# ═══ DETECT CATEGORY ══════════════════════════════════════════════════
def detect_cat(title):
    t = title.lower()
    if any(x in t for x in ['cricket', 'ipl', 'wicket', 'rohit', 'kohli', 'dhoni', 'match', 'bcci']):
        return 'Cricket'
    if any(x in t for x in ['bollywood', 'film', 'movie', 'actor', 'actress', 'srk', 'deepika', 'salman']):
        return 'Bollywood'
    if any(x in t for x in ['modi', 'parliament', 'election', 'bjp', 'congress', 'govt', 'minister']):
        return 'Politics'
    if any(x in t for x in ['tech', 'jio', '5g', '6g', 'startup', 'ai', 'software', 'apple', 'google']):
        return 'Tech'
    if any(x in t for x in ['market', 'stock', 'economy', 'gdp', 'business', 'rupee', 'sensex']):
        return 'Business'
    return 'World'

def is_breaking(title):
    keywords = ['breaking', 'urgent', 'just in', 'alert', 'record', 'shock', 'exclusive', 'win', 'announce', 'dies', 'resign', 'crash']
    return any(k in title.lower() for k in keywords)

# ═══ GEMINI IMAGE GENERATION ══════════════════════════════════════════
def generate_image_gemini(cat, title):
    """Generate image using Gemini Imagen — 20/day free."""
    global img_count
    if img_count >= GEMINI_DAILY_LIMIT:
        print('[WARN] Daily Gemini quota reached')
        return None
    if not GEMINI_KEY:
        print('[WARN] No Gemini key')
        return None
    try:
        genai.configure(api_key=GEMINI_KEY)
        prompt = PROMPTS.get(cat, PROMPTS['World'])
        model = genai.ImageGenerationModel('imagen-3.0-generate-001')
        result = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio='9:16',
            safety_filter_level='block_some',
            person_generation='allow_adult'
        )
        img = result.images[0]._pil_image
        img_count += 1
        print(f'[GEMINI] Image generated! ({img_count}/{GEMINI_DAILY_LIMIT} today)')
        return img
    except Exception as e:
        print(f'[ERROR] Gemini: {e}')
        return None

# ═══ APPLY CLASSIC CINEMATIC TONE ═════════════════════════════════════
def apply_classic_tone(img):
    """Apply warm sepia classic film tone."""
    img = img.convert('RGB')
    # Sepia
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(0.75)
    # Contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.15)
    # Brightness
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.92)
    # Warm tint
    r, g, b = img.split()
    r = r.point(lambda i: min(255, int(i * 1.08)))
    b = b.point(lambda i: int(i * 0.92))
    img = Image.merge('RGB', (r, g, b))
    return img

# ═══ BUILD POST IMAGE ═════════════════════════════════════════════════
def build_post(article, bg_img, plat='instagram'):
    """Build final post with classic cinematic tone overlay."""
    W, H = PLATFORMS[plat]['w'], PLATFORMS[plat]['h']
    cat = article.get('category', 'World')
    title = article['title']
    src = article['source']['name']
    breaking = is_breaking(title)

    # Base image
    if bg_img:
        # Smart crop to 9:16
        bw, bh = bg_img.size
        target_r = W / H
        src_r = bw / bh
        if src_r > target_r:
            new_w = int(bh * target_r)
            left = (bw - new_w) // 2
            bg_img = bg_img.crop((left, 0, left + new_w, bh))
        else:
            new_h = int(bw / target_r)
            top = (bh - new_h) // 2
            bg_img = bg_img.crop((0, top, bw, top + new_h))
        img = bg_img.resize((W, H), Image.LANCZOS).convert('RGBA')
        # Apply classic tone
        img_rgb = apply_classic_tone(img.convert('RGB'))
        img = img_rgb.convert('RGBA')
    else:
        # Gradient fallback
        img = Image.new('RGBA', (W, H), (26, 16, 0, 255))
        draw_base = ImageDraw.Draw(img)
        for y in range(H):
            ratio = y / H
            r = int(26 + ratio * 10)
            g = int(16 + ratio * 20)
            b = int(0 + ratio * 32)
            draw_base.line([(0, y), (W, y)], fill=(r, g, b, 255))

    draw = ImageDraw.Draw(img)

    # ── Vignette ──
    vig = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    vig_draw = ImageDraw.Draw(vig)
    cx, cy = W // 2, H // 2
    max_r = int(math.sqrt(cx**2 + cy**2))
    for r in range(max_r, 0, -1):
        alpha = int(max(0, min(160, (1 - r/max_r)**2 * 200)))
        vig_draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, vig)
    draw = ImageDraw.Draw(img)

    # ── Film grain ──
    import random
    for _ in range(15000):
        x = random.randint(0, W-1)
        y = random.randint(0, H-1)
        alpha = random.randint(0, 12)
        draw.point((x, y), fill=(255, 220, 150, alpha))

    # ── Bottom gradient ──
    for y in range(int(H * 0.45)):
        py = H - int(H * 0.45) + y
        alpha = int((y / (H * 0.45))**2 * 230)
        draw.line([(0, py), (W, py)], fill=(0, 0, 0, alpha))

    # ── Letterbox bars ──
    lb_h = int(H * 0.07)
    draw.rectangle([0, 0, W, lb_h], fill=(0, 0, 0, 220))
    draw.rectangle([0, H - lb_h, W, H], fill=(0, 0, 0, 220))

    # ── Gold top line ──
    draw.rectangle([0, lb_h, W, lb_h + 5], fill=(201, 150, 58, 255))

    # ── Category badge ──
    cat_colors = {
        'Cricket': (0, 217, 126),
        'Bollywood': (232, 184, 75),
        'Politics': (255, 107, 107),
        'World': (61, 142, 255),
        'Tech': (155, 109, 255),
        'Business': (255, 193, 7),
    }
    cat_emojis = {
        'Cricket': '🏏', 'Bollywood': '🎬', 'Politics': '🏛️',
        'World': '🌍', 'Tech': '💻', 'Business': '📈'
    }
    bc = cat_colors.get(cat, (201, 150, 58))
    badge_y = lb_h + 40
    draw.rounded_rectangle([70, badge_y, 310, badge_y + 60], radius=30, fill=(*bc, 50), outline=(*bc, 200), width=2)
    draw.text((190, badge_y + 30), f'{cat_emojis.get(cat, "📰")} {cat.upper()}', fill=(*bc, 255), anchor='mm')

    # ── Breaking badge ──
    if breaking:
        draw.rounded_rectangle([325, badge_y, 595, badge_y + 60], radius=30, fill=(255, 68, 68, 50), outline=(255, 68, 68, 200), width=2)
        draw.text((460, badge_y + 30), '⚡ BREAKING', fill=(255, 140, 140, 255), anchor='mm')

    # ── Platform badge top right ──
    draw.rounded_rectangle([W-180, lb_h+20, W-20, lb_h+65], radius=22, fill=(201, 150, 58, 40), outline=(201, 150, 58, 100), width=1)
    draw.text((W-100, lb_h+42), '9:16 · 1080×1920', fill=(245, 214, 138, 200), anchor='mm')

    # ── Headline text ──
    words = title.split()
    lines, line = [], ''
    for w in words:
        test = (line + ' ' + w).strip()
        if len(test) > 30 and line:
            lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)

    headline_y = H - lb_h - 220 - (len(lines[:4]) * 80)
    for ln in lines[:4]:
        draw.text((70, headline_y), ln, fill=(245, 214, 138, 255))
        headline_y += 80

    # ── Source + Branding ──
    draw.text((70, H - lb_h - 150), f'📺 {src}', fill=(255, 255, 255, 160))
    draw.text((70, H - lb_h - 90), '⚡ MINUTE NEWS', fill=(201, 150, 58, 230))

    # ── Bottom gold bar ──
    draw.rectangle([0, H - lb_h - 28, W, H - lb_h - 4], fill=(201, 150, 58, 255))
    draw.text((W - 30, H - lb_h - 16), f'MINUTE NEWS · {PLATFORMS[plat]["ratio"]}', fill=(255, 255, 255, 255), anchor='rm')

    return img.convert('RGB')

# ═══ POST TO INSTAGRAM ════════════════════════════════════════════════
def post_to_instagram(img_path, caption):
    """Post image to Instagram via Meta Graph API."""
    if not META_TOKEN or not INSTAGRAM_ID:
        print('[SKIP] Instagram not configured')
        return False
    try:
        print('[INSTAGRAM] Uploading image...')
        # Upload image to get container
        with open(img_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()

        r1 = requests.post(
            f'https://graph.facebook.com/v19.0/{INSTAGRAM_ID}/media',
            json={
                'image_url': f'data:image/jpeg;base64,{img_data}',
                'caption': caption[:2200],
                'access_token': META_TOKEN
            },
            timeout=30
        )
        d1 = r1.json()
        if 'error' in d1:
            raise Exception(d1['error']['message'])

        # Publish
        r2 = requests.post(
            f'https://graph.facebook.com/v19.0/{INSTAGRAM_ID}/media_publish',
            json={'creation_id': d1['id'], 'access_token': META_TOKEN},
            timeout=30
        )
        d2 = r2.json()
        if 'error' in d2:
            raise Exception(d2['error']['message'])

        print(f'[INSTAGRAM] ✅ Posted! ID: {d2.get("id")}')
        return True
    except Exception as e:
        print(f'[ERROR] Instagram: {e}')
        return False

# ═══ POST TO FACEBOOK ═════════════════════════════════════════════════
def post_to_facebook(img_path, caption):
    """Post image to Facebook Page via Meta Graph API."""
    if not META_TOKEN or not FB_PAGE_ID:
        print('[SKIP] Facebook not configured')
        return False
    try:
        print('[FACEBOOK] Uploading post...')
        with open(img_path, 'rb') as f:
            r = requests.post(
                f'https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos',
                data={
                    'message': caption[:63206],
                    'access_token': META_TOKEN
                },
                files={'source': f},
                timeout=30
            )
        d = r.json()
        if 'error' in d:
            raise Exception(d['error']['message'])

        print(f'[FACEBOOK] ✅ Posted! ID: {d.get("id")}')
        return True
    except Exception as e:
        print(f'[ERROR] Facebook: {e}')
        return False

# ═══ POST TO YOUTUBE ══════════════════════════════════════════════════
def notify_youtube(title, caption):
    """Send YouTube community post notification."""
    if not YT_API_KEY or not YT_CHANNEL_ID:
        print('[SKIP] YouTube not configured')
        return False
    try:
        print('[YOUTUBE] Sending community post...')
        r = requests.post(
            f'https://www.googleapis.com/youtube/v3/communityPosts?part=snippet&key={YT_API_KEY}',
            json={'snippet': {'channelId': YT_CHANNEL_ID, 'text': f'🚨 {caption[:900]}'}},
            timeout=15
        )
        d = r.json()
        if 'error' in d:
            raise Exception(d['error']['message'])
        print(f'[YOUTUBE] ✅ Community post sent!')
        return True
    except Exception as e:
        print(f'[WARN] YouTube: {e}')
        return False

# ═══ GENERATE MUSIC ═══════════════════════════════════════════════════
def generate_music(cat, duration=15):
    """Generate WAV background music per news category."""
    sr = 44100
    frames = sr * duration
    freq_map = {
        'Cricket':  [220, 330, 440, 550],
        'Bollywood':[261, 329, 392, 523],
        'Politics': [174, 220, 261, 349],
        'World':    [196, 247, 294, 392],
        'Tech':     [440, 550, 660, 880],
        'Business': [220, 277, 330, 415],
    }
    freqs = freq_map.get(cat, freq_map['World'])
    samples = []
    for i in range(frames):
        t = i / sr
        s = sum(
            0.12 * math.sin(2 * math.pi * f * t) * math.exp(-t * 0.15)
            for f in freqs
        )
        # Add slight reverb
        s += 0.03 * math.sin(2 * math.pi * freqs[0] * 2 * t) * math.exp(-t * 0.5)
        samples.append(max(-32767, min(32767, int(s * 32767))))

    path = f'/tmp/music_{cat}.wav'
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))
    print(f'[MUSIC] ✅ Generated {cat} music: {path}')
    return path

# ═══ MAIN ════════════════════════════════════════════════════════════
def main():
    print('=' * 60)
    print('⚡ MINUTE NEWS AGENT — Starting cycle')
    print(f'   Platforms: Instagram + Facebook + YouTube')
    print(f'   Language:  Telugu + English')
    print(f'   Tone:      Classic Cinematic')
    print('=' * 60)

    # Fetch news
    articles = fetch_news()
    if not articles:
        print('[ERROR] No news found. Exiting.')
        return

    # Process top 4 articles
    for i, article in enumerate(articles[:4]):
        cat = detect_cat(article['title'])
        article['category'] = cat
        breaking = is_breaking(article['title'])

        print(f'\n[{i+1}/4] {"⚡ BREAKING: " if breaking else ""}{article["title"][:60]}...')
        print(f'      Category: {cat} | Source: {article["source"]["name"]}')

        # Generate image
        bg = None
        if breaking or img_count < GEMINI_DAILY_LIMIT:
            bg = generate_image_gemini(cat, article['title'])

        # Generate music
        try:
            music = generate_music(cat)
        except Exception as e:
            print(f'[WARN] Music: {e}')
            music = None

        # Build post for each platform
        for plat in ['instagram', 'facebook', 'youtube']:
            try:
                post_img = build_post(article, bg, plat)
                path = f'/tmp/minutenews_{plat}_{i}.jpg'
                post_img.save(path, quality=95, optimize=True)
                print(f'[BUILD] ✅ {plat} post saved: {PLATFORMS[plat]["ratio"]}')
            except Exception as e:
                print(f'[ERROR] Build {plat}: {e}')

        # Generate caption
        tmpl = CAPTIONS.get(cat, CAPTIONS['World'])
        caption = tmpl.format(title=article['title'], src=article['source']['name'])

        # Post to all platforms
        ig_path = f'/tmp/minutenews_instagram_{i}.jpg'
        fb_path = f'/tmp/minutenews_facebook_{i}.jpg'

        post_to_instagram(ig_path, caption)
        time.sleep(2)
        post_to_facebook(fb_path, caption)
        time.sleep(2)
        notify_youtube(article['title'], caption)

        print(f'[DONE] Article {i+1} complete!')
        time.sleep(3)

    print('\n' + '=' * 60)
    print('✅ MINUTE NEWS AGENT — Cycle complete!')
    print(f'   Images generated: {img_count}/{GEMINI_DAILY_LIMIT}')
    print('=' * 60)

if __name__ == '__main__':
    main()
