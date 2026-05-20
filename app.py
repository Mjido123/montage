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
st.write("نسخة محمية 100% ضد أخطاء التحميل والمونتاج!")

# المفاتيح الخاصة بك
GROQ_API_KEY = "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"
PEXELS_API_KEY = "XnPWWkhbXhrbNJT5kxbteSdlK7MGQ48fUNGUkM5R3yy0XxePAg85oifm"

# إعداد Groq
client = Groq(api_key=GROQ_API_KEY)

def generate_script_and_keyword(idea_prompt):
    system_prompt = (
        "You are an expert video scriptwriter. Based on the user's idea, generate a response in strict JSON format.\n\n"
        "CRITICAL INSTRUCTIONS FOR THE 'script' KEY:\n"
        "1. Write a beautifully structured, highly engaging narrative for a 30-50 seconds Reel/Short.\n"
        "2. Use clear, correct, and professional Modern Standard Arabic (اللغة العربية الفصحى المبسطة).\n"
        "3. Absolute plain text ONLY. DO NOT use any markdown (no **, no *, no __), no bullet points, no symbols, and no quotation marks.\n"
        "4. It MUST be between 90 to 130 words long.\n\n"
        "CRITICAL INSTRUCTIONS FOR THE 'keyword' KEY:\n"
        "1. Provide exactly ONE single English word that captures the main visual theme (e.g., 'trading', 'success', 'office'). Lowercase only.\n\n"
        "Do not include any intro, outro, or markdown formatting outside the raw JSON object."
    )
    
    chat_completion = client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": idea_prompt}],
        model="llama-3.1-8b-instant",
        response_format={"type": "json_object"}
    )
    
    result = json.loads(chat_completion.choices[0].message.content.strip())
    
    raw_script = str(result.get('script', ''))
    clean_script = raw_script.replace('**', '').replace('*', '').replace('`', '').replace('"', '').replace("'", "")
    clean_keyword = str(result.get('keyword', 'video')).replace('"', '').replace("'", "").strip().lower()
    
    return clean_script, clean_keyword

async def generate_voiceover(text_script, selected_voice, output_audio_path="voiceover.mp3"):
    if os.path.exists(output_audio_path):
        try: os.remove(output_audio_path)
        except: pass
    communicate = edge_tts.Communicate(text_script, voice=selected_voice)
    await communicate.save(output_audio_path)

def download_pexels_videos(search_query, count=5):
    headers = {"Authorization": PEXELS_API_KEY.strip()}
    url = "https://api.pexels.com/v1/videos/search"
    query = search_query.strip()
    
    # محاولة أولى: بحث عمودي (Portrait)
    query_params = {"query": query, "per_page": count, "orientation": "portrait"}
    videos_list = []
    
    try:
        response = requests.get(url, headers=headers, params=query_params, timeout=12)
        if response.status_code == 200:
            videos_list = response.json().get('videos', [])
    except:
        pass
        
    # محاولة ثانية: يلا مالقاش، كيحيد فلتر العمودي باش يجيب أي حاجة واجدة تما
    if not videos_list:
        query_params.pop("orientation", None)
        try:
            response = requests.get(url, headers=headers, params=query_params, timeout=12)
            if response.status_code == 200:
                videos_list = response.json().get('videos', [])
        except:
            pass

    video_files = []
    if not os.path.exists("temp_clips"): 
        os.makedirs("temp_clips")

    # 🎯 الخطة الإستراتيجية البديلة: روابط فيديوهات ثابتة وعالية الجودة ف حالة فشل Pexels تماماً
    fallback_urls = [
        "https://assets.mixkit.co/videos/preview/mixkit-man-working-on-his-laptop-in-an-office-42322-large.mp4",
        "https://assets.mixkit.co/videos/preview/mixkit-financial-charts-on-a-computer-monitor-43184-large.mp4",
        "https://assets.mixkit.co/videos/preview/mixkit-business-charts-on-a-laptop-screen-43187-large.mp4",
        "https://assets.mixkit.co/videos/preview/mixkit-typing-on-a-computer-keyboard-43189-large.mp4",
        "https://assets.mixkit.co/videos/preview/mixkit-holding-a-smartphone-with-financial-data-43191-large.mp4"
    ]

    if videos_list:
        for i, video in enumerate(videos_list):
            video_files_list = video.get('video_files', [])
            best_video_url = None
            for v_file in video_files_list:
                if v_file.get('width') == 1080 or v_file.get('quality') == 'hd':
                    best_video_url = v_file.get('link')
                    break
            if not best_video_url and video_files_list: 
                best_video_url = video_files_list[0].get('link')

            if best_video_url:
                try:
                    video_data = requests.get(best_video_url, timeout=20).content
                    file_path = f"temp_clips/clip_{i+1}.mp4"
                    with open(file_path, 'wb') as f: f.write(video_data)
                    video_files.append(file_path)
                except: pass

    # يلا لسبب ما Pexels رجع خاوي، كيهز الفيديوهات البديلة مباشرة
    if not video_files:
        st.warning("⚠️ تم الانتقال للفيديوهات الاحتياطية لتأمين إنتاج المقطع...")
        for i, b_url in enumerate(fallback_urls[:count]):
            try:
                video_data = requests.get(b_url, timeout=20).content
                file_path = f"temp_clips/clip_fb_{i+1}.mp4"
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

# --- واجهة الويب (Streamlit UI) ---

idea = st.text_input("ادخل فكرة الفيديو ديالك هنا:", placeholder="مثال: أهمية الصبر والانضباط في تداول أسواق المال...")

voice_options = {
    "🎙️ منى (امرأة - لهجة مغربية) 🇲🇦": "ar-MA-MounaNeural",
    "🎙️ جمال (راجل - لهجة مغربية) 🇲🇦": "ar-MA-JamalNeural",
    "🎙️ حامد (راجل - لغة عربية فصحى) 🇸🇦": "ar-SA-HamedNeural",
    "🎙️ زارية (امرأة - لغة عربية فصحى) 🇸🇦": "ar-SA-ZariyahNeural"
}

selected_voice_label = st.selectbox("اختار المعلق الصوتي (Voice):", list(voice_options.keys()))
chosen_voice_code = voice_options[selected_voice_label]

if st.button("إصدار المقطع النهائي 🚀", use_container_width=True):
    if not idea.strip():
        st.error("عافاك كتب شي فكرة الأول!")
    else:
        output_video = "my_awesome_short.mp4"
        
        with st.status("⏳ جاري توليد مقطع احترافي ونقي...", expanded=True) as status:
            try:
                status.write("🤖 جاري كتابة السكربت وتنظيفه تلقائياً...")
                script, keyword = generate_script_and_keyword(idea)
                
                st.info(f"📜 **السكربت المولد:**\n\n{script}")
                st.caption(f"🔑 **الكلمة المفتاحية للبحث:** {keyword}")
                
                status.write("🎙️ جاري تسجيل الصوت التلقائي...")
                asyncio.run(generate_voiceover(script, chosen_voice_code, "voiceover.mp3"))
                
                status.write(f"🔍 جاري معالجة وجلب الكليبات المونتاجية...")
                # طلب 5 كليبات لتسريع العملية وتأمينها
                videos = download_pexels_videos(keyword, count=5)
                
                if videos:
                    status.write("🎬 جاري المونتاج والـ Rendering النهائي...")
                    edit_and_render_video(videos, "voiceover.mp3", output_name=output_video)
                    status.update(label="🎉 مبروك! تم إنتاج الفيديو بنجاح واكتملت المعالجة!", state="complete", expanded=True)
                    
                    st.success("ها هو الفيديو ديالك جاهز للتحميل:")
                    with open(output_video, "rb") as file:
                        st.video(file)
                        st.download_button(
                            label="📥 تحميل الفيديو النهائي (MP4)",
                            data=file,
                            file_name="perfect_short.mp4",
                            mime="video/mp4"
                        )
                else:
                    status.update(label="❌ فشل تام في جلب أي فيديو", state="error")
                    st.error("لم نتمكن من جلب فيديوهات أساسية أو احتياطية. يرجى مراجعة الشبكة.")
            except Exception as e:
                status.update(label="❌ وقع خطأ في المعالجة", state="error")
                st.error(f"تفاصيل الخطأ: {str(e)}")
