#!/usr/bin/env python3
"""
India News Agent v4 — 24/7 GitHub Actions Backend
Platforms: Instagram + Facebook + YouTube (9:16 vertical auto-sizing)
Tone: Classic Cinematic (sepia/warm/film grain)
Music: AI-generated audio per news category
Notification: YouTube Community Posts
"""
import os,requests,json,time,math,wave,struct
from PIL import Image,ImageDraw,ImageFilter,ImageEnhance
from io import BytesIO
import google.generativeai as genai

GEMINI_KEY = os.environ.get('GEMINI_KEY','')
GNEWS_KEY  = os.environ.get('GNEWS_KEY','')
YT_API_KEY = os.environ.get('YT_API_KEY','')
YT_CHANNEL = os.environ.get('YT_CHANNEL','')

# Platform specs — all 9:16
PLATFORMS = {
  'instagram': {'w':1080,'h':1920,'ratio':'9:16','name':'Instagram Reels'},
  'facebook':  {'w':1080,'h':1920,'ratio':'9:16','name':'Facebook Reels'},
  'youtube':   {'w':1080,'h':1920,'ratio':'9:16','name':'YouTube Shorts'},
}

CAPTIONS = {
  'Cricket':  '🏏 క్రికెట్ అప్‌డేట్!\n\n{title}\n\n📺 {src}\n\n#Cricket #India #TeamIndia #IPL',
  'Bollywood':'🎬 బాలీవుడ్ వార్త!\n\n{title}\n\n📺 {src}\n\n#Bollywood #Cinema #Telugu',
  'Politics': '🏛️ రాజకీయ వార్త\n\n{title}\n\n📺 {src}\n\n#Politics #India #Breaking',
  'World':    '🌍 ప్రపంచ వార్త\n\n{title}\n\n📺 {src}\n\n#WorldNews #India',
  'Tech':     '💻 టెక్ వార్త\n\n{title}\n\n📺 {src}\n\n#Technology #India #Jio',
  'Business': '📈 వ్యాపార వార్త\n\n{title}\n\n📺 {src}\n\n#Business #India #Economy',
}

def fetch_news():
    articles=[]
    for topic in ['cricket india','bollywood','india politics','india world','india tech']:
        try:
            r=requests.get(f'https://gnews.io/api/v4/search?q={topic}&lang=en&country=in&max=2&token={GNEWS_KEY}',timeout=10)
            articles.extend(r.json().get('articles',[]))
        except: pass
    seen,unique=set(),[]
    for a in articles:
        if a['title'] not in seen: seen.add(a['title']);unique.append(a)
    return unique[:5]

def detect_cat(title):
    t=title.lower()
    if any(x in t for x in ['cricket','ipl','wicket','rohit','kohli']): return 'Cricket'
    if any(x in t for x in ['bollywood','film','movie','actor']): return 'Bollywood'
    if any(x in t for x in ['modi','parliament','election']): return 'Politics'
    if any(x in t for x in ['tech','jio','5g','6g','startup']): return 'Tech'
    return 'World'

def generate_image(prompt, cat):
    genai.configure(api_key=GEMINI_KEY)
    tone_suffix='classic film photography, warm sepia tones, vintage cinema, Kodachrome, 35mm grain, golden light'
    full_prompt=f'{prompt}, {tone_suffix}'
    model=genai.ImageGenerationModel('imagen-3.0-generate-001')
    result=model.generate_images(prompt=full_prompt,number_of_images=1,aspect_ratio='9:16')
    return result.images[0]._pil_image

def apply_classic_tone(img):
    # Sepia
    r,g,b=img.split() if img.mode=='RGB' else img.convert('RGB').split()
    img=Image.merge('RGB',(r,g,b))
    enhancer=ImageEnhance.Color(img)
    img=enhancer.enhance(0.75)
    enhancer=ImageEnhance.Contrast(img)
    img=enhancer.enhance(1.15)
    enhancer=ImageEnhance.Brightness(img)
    img=enhancer.enhance(0.92)
    return img

def build_post(article, bg_img, plat='instagram'):
    W,H=PLATFORMS[plat]['w'],PLATFORMS[plat]['h']
    if bg_img:
        # Smart crop to 9:16
        bw,bh=bg_img.size
        target_r=W/H; src_r=bw/bh
        if src_r>target_r: new_w=int(bh*target_r); bg_img=bg_img.crop(((bw-new_w)//2,0,(bw+new_w)//2,bh))
        else: new_h=int(bw/target_r); bg_img=bg_img.crop((0,(bh-new_h)//2,bw,(bh+new_h)//2))
        img=bg_img.resize((W,H),Image.LANCZOS).convert('RGBA')
        img=apply_classic_tone(img.convert('RGB')).convert('RGBA')
    else:
        img=Image.new('RGBA',(W,H),(15,10,5,255))

    draw=ImageDraw.Draw(img)
    # Vignette
    vig=Image.new('RGBA',(W,H),(0,0,0,0))
    vd=ImageDraw.Draw(vig)
    for i in range(min(W,H)//2,0,-1):
        alpha=int((1-(i/(min(W,H)/2)))**2*140)
        vd.ellipse([W//2-i,H//2-i,W//2+i,H//2+i],fill=(0,0,0,alpha))
    img=Image.alpha_composite(img,vig)
    draw=ImageDraw.Draw(img)

    # Letterbox
    draw.rectangle([0,0,W,int(H*0.06)],fill=(0,0,0,220))
    draw.rectangle([0,int(H*0.94),W,H],fill=(0,0,0,220))
    # Gold line
    draw.rectangle([0,int(H*0.06),W,int(H*0.06)+4],fill=(201,150,58,255))
    # Gradient overlay
    for i in range(int(H*0.5)):
        alpha=int((i/(H*0.5))**2*220)
        draw.rectangle([0,H-int(H*0.5)+i,W,H-int(H*0.5)+i+1],fill=(0,0,0,alpha))
    # Category
    cat=article.get('category','News')
    draw.text((70,int(H*0.07)+20),f'📰 {cat.upper()}',fill=(201,150,58,255))
    # Headline
    title=article['title']
    words=title.split(); lines=[]; line=''
    for w in words:
        if len(line+' '+w)>32 and line: lines.append(line);line=w
        else: line=(line+' '+w).strip()
    if line: lines.append(line)
    y=int(H*0.75)
    for ln in lines[:4]:
        draw.text((60,y),ln,fill=(245,214,138,255))
        y+=int(H*0.065)
    draw.text((60,int(H*0.92)),f"📺 {article['source']['name']}",fill=(255,255,255,120))
    # Watermark
    draw.rectangle([0,int(H*0.96),W,int(H*0.96)+22],fill=(201,150,58,255))
    draw.text((W-350,int(H*0.96)+4),f"INDIA NEWS AGENT · {PLATFORMS[plat]['ratio']}",fill=(255,255,255,255))
    return img.convert('RGB')

def generate_music(cat, duration=15):
    """Generate WAV background music based on category"""
    sr=44100; frames=sr*duration
    freqs={'Cricket':[220,330,440],'Bollywood':[261,329,392],'Politics':[174,220,261],'World':[196,247,294],'Tech':[440,550,660],'Business':[220,277,330]}
    f=freqs.get(cat,freqs['World'])
    samples=[]
    for i in range(frames):
        t=i/sr
        s=sum(0.15*math.sin(2*math.pi*freq*t)*math.exp(-t*0.3) for freq in f)
        samples.append(int(s*32767))
    with wave.open(f'/tmp/music_{cat}.wav','w') as wf:
        wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(sr)
        wf.writeframes(struct.pack('<'+'h'*len(samples),*samples))
    return f'/tmp/music_{cat}.wav'

def notify_youtube(title, caption):
    if not YT_API_KEY or not YT_CHANNEL: return
    try:
        requests.post(f'https://www.googleapis.com/youtube/v3/communityPosts?part=snippet&key={YT_API_KEY}',
            json={'snippet':{'channelId':YT_CHANNEL,'text':f'🚨 {caption[:900]}'}},timeout=10)
        print(f'✅ YouTube notified: {title[:50]}')
    except Exception as e: print(f'YouTube: {e}')

def main():
    print('='*50);print('India News Agent v4');print('='*50)
    articles=fetch_news()
    print(f'Found {len(articles)} articles')
    for i,art in enumerate(articles[:4]):
        cat=detect_cat(art['title']); art['category']=cat
        print(f'\n[{i+1}] {art["title"][:60]}...')
        # Generate image
        try:
            bg=generate_image(f'{cat} India news scene',cat)
        except Exception as e:
            print(f'Gemini: {e}'); bg=None
        # Generate music
        try: music=generate_music(cat)
        except: music=None
        # Build & save posts for all 3 platforms
        for plat in ['instagram','facebook','youtube']:
            post=build_post(art,bg,plat)
            path=f'/tmp/post_{plat}_{i}.jpg'
            post.save(path,quality=95)
            print(f'✅ {plat} post saved: {PLATFORMS[plat]["ratio"]}')
        # Caption
        cap=CAPTIONS.get(cat,'📰 {title}\n{src}').format(title=art['title'],src=art['source']['name'])
        notify_youtube(art['title'],cap)
        time.sleep(2)
    print('\n✅ Cycle complete!')

if __name__=='__main__': main()
