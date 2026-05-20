import os
import json
import asyncio
import requests
import streamlit as st
from groq import Groq
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

# إعدادات الصفحة
st.set_page_config(page_title="صانع الفيديوهات التلقائي 🎬", page_icon="🎬", layout="centered")

st.title("صانع الفيديوهات التلقائي بـ Python 🚀")
st.write("اكتب الفكرة ديالك وخلي الذكاء الاصطناعي يتكلف بالمونتاج والتحميل!")

# المفاتيح الخاصة بك
GROQ_API_KEY = "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"
PEXELS_API_KEY = "XnPWWkhbXhrbNJT5kxbteSdlK7MGQ48fUNGUkM5R3yy0XxePAg85oifm"

# إعداد Groq
client = Groq(api_key=GROQ_API_KEY)

def generate_script_and_keyword(idea_prompt):
    system_prompt = (
        "You are an expert video creator. Based on the user's idea, generate a response in strict JSON format. "
        "The JSON must contain exactly two keys with plain string values:\n"
        "1. 'script': A short narrative under 50 words for a 30-second Reel/Short in standard Arabic. No symbols.\n"
        "2. 'keyword': One single English word representing the visual theme (e.g., 'trading', 'success'). No spaces, no symbols.\n"
        "Do not include any text outside the raw JSON object."
    )
    chat_completion = client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": idea_prompt}],
        model="llama-3.1-8b-instant",
        response_format={"type": "json_object"}
    )
    result = json.loads(chat_completion.choices[0].message.content.strip())
    return str(result.get('script', '')), str(result.get('keyword', 'video')).strip()

async def generate_voiceover(text_script, output_audio_path="voiceover.mp3"):
    if os.path.exists(output_audio_path):
        try: os.remove(output_audio_path)
        except: pass
    communicate = edge_tts.Communicate(text_script, voice="ar-MA-MounaNeural")
    await communicate.save(output_audio_path)

def download_pexels_videos(search_query, count=3):
    headers = {"Authorization": PEXELS_API_KEY.strip()}
    url = "https://api.pexels.com/v1/videos/search"
    query_params = {"query": search_query, "per_page": count, "orientation": "portrait"}
    
    try:
        response = requests.get(url, headers=headers, params=query_params, timeout=15)
        if response.status_code != 200: return []
        data = response.json()
    except:
        return []
        
    video_files = []
    if not os.path.exists("temp_clips"): os.makedirs("temp_clips")

    videos_list = data.get('videos', [])
    for i, video in enumerate(videos_list):
        video_files_list = video.get('video_files', [])
        best_video_url = None
        for v_file in video_files_list:
            if v_file.get('width') == 1080 or v_file.get('quality') == 'hd':
                best_video_url = v_file.get('link')
                break
        if not best_video_url and video_files_list: best_video_url = video_files_list[0].get('link')

        if best_video_url:
            try:
                video_data = requests.get(best_video_url, timeout=30).content
                file_path = f"temp_clips/clip_{i+1}.mp4"
                with open(file_path, 'wb') as f: f.write(video_data)
                video_files.append(file_path)
            except: pass
    return video_files

def edit_and_render_video(video_files, voice_path, output_name="final_short.mp4"):
    voice = AudioFileClip(voice_path)
    total_duration = voice.duration
    duration_per_clip = total_duration / len(video_files)
    clips = []
    
    for vid in video_files:
        clip = VideoFileClip(vid).subclip(0, duration_per_clip)
        clip_resized = clip.fl_image(lambda image: image)
        clip_resized.size = (1080, 1920)
        clips.append(clip_resized)
        
    final_video_clips = concatenate_videoclips(clips, method="compose")
    final_short = final_video_clips.set_audio(voice)
    final_short.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", threads=4)
    
    for vid in video_files:
        try: os.remove(vid)
        except: pass

# --- واجهة الويب الإدخال ---
idea = st.text_input("ادخل فكرة الفيديو هنا:", placeholder="مثال: أهمية التداول وإدارة المخاطر...")

if st.button("إصدار المقطع النهائي 🚀", use_container_width=True):
    if not idea.strip():
        st.error("عافاك كتب شي فكرة الأول!")
    else:
        output_video = "my_awesome_short.mp4"
        
        with st.status("⏳ جاري العمل على الفيديو الخاص بك...", expanded=True) as status:
            try:
                status.write("🤖 جاري كتابة السكربت بالذكاء الاصطناعي...")
                script, keyword = generate_script_and_keyword(idea)
                st.write(f"📜 **السكربت:** {script}")
                st.write(f"🔑 **الكلمة المفتاحية:** {keyword}")
                
                status.write("🎙️ جاري تسجيل الصوت التلقائي...")
                asyncio.run(generate_voiceover(script, "voiceover.mp3"))
                
                status.write(f"🔍 جاري جلب الفيديوهات العمودية المناسبة من Pexels...")
                videos = download_pexels_videos(keyword, count=3)
                
                if videos:
                    status.write("🎬 جاري المونتاج والـ Rendering (ثواني فقط)...")
                    edit_and_render_video(videos, "voiceover.mp3", output_name=output_video)
                    status.update(label="🎉 مبروك! تم إنتاج الفيديو بنجاح!", state="complete", expanded=True)
                    
                    # عرض الفيديو في الموقع للتحميل
                    st.success("ها هو الفيديو ديالك واجد:")
                    with open(output_video, "rb") as file:
                        st.video(file)
                        st.download_button(
                            label="📥 تحميل الفيديو النهائي",
                            data=file,
                            file_name="reels_short.mp4",
                            mime="video/mp4"
                        )
                else:
                    status.update(label="❌ فشل في جلب الفيديوهات", state="error")
                    st.error("لم نجد فيديوهات مناسبة ف Pexels.")
            except Exception as e:
                status.update(label="❌ وقع خطأ غير متوقع", state="error")
                st.error(f"تفاصيل الخطأ: {str(e)}")