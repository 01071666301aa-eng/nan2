import streamlit as st
from groq import Groq
import google.generativeai as genai
import os
import re
import hashlib
import requests
import json

# ── 1. 페이지 설정 ───────────────────────────────────────────
st.set_page_config(page_title="당신의 이야기", page_icon="📖", layout="centered")

# ── 2. API 클라이언트 설정 ───────────────────────────────────
# Streamlit Cloud의 Secrets에서 키를 가져옵니다.
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

# ── 3. 장르 및 캐릭터 설정 데이터 ──────────────────────────────
GENRE_CONFIG = {
    "학원": {
        "emoji": "🏫",
        "sub_categories": ["재벌고 전학생", "학생회 라이벌", "비밀 연애", "삼각관계", "아이돌 학교", "기숙사 생활"],
        "base_world": "명문 사립 고등학교 배경의 풋풋하고 치열한 청춘 로맨스."
    },
    "판타지/로판": {
        "emoji": "⚔️",
        "sub_categories": ["빙의/회귀", "성녀와 기사", "폭군 황제", "마법 학교", "드래곤의 계약자"],
        "base_world": "검과 마법, 신화적 요소가 공존하는 이세계 귀족 사회 배경의 로맨스 판타지."
    },
    "현대 로맨스": {
        "emoji": "🌃",
        "sub_categories": ["사내 연애", "정략 결혼", "소꿉친구", "계약 연애", "원나잇 투 러브"],
        "base_world": "화려한 도시의 비즈니스와 일상 속에서 피어나는 현대적 로맨스."
    },
    "시대극": {
        "emoji": "🎎",
        "sub_categories": ["궁중 암투", "금지된 사랑", "자객과 공주", "몰락 귀족"],
        "base_world": "가상의 동양풍 시대 배경, 신분을 초월한 애절한 로맨스."
    },
    "스포츠": { "emoji": "⚽", "sub_categories": ["라이벌", "매니저와 선수", "재활기", "슬럼프"], "base_world": "땀과 열정, 승부욕이 뒤섞인 스포츠 현장의 로맨스." },
    "일상": { "emoji": "☕", "sub_categories": ["옆집 이웃", "카페 알바", "쉐어하우스", "힐링물"], "base_world": "잔잔한 일상 속에서 서서히 스며드는 따뜻한 로맨스." }
}

LEVEL_OPTIONS = {
    "순애": "🌸 설렘 위주의 풋풋하고 간지러운 분위기",
    "로맨스": "💫 감정선이 깊고 뜨거운 일반적인 로맨스",
    "성인로맨스": "🥂 농밀한 긴장감과 욕망, 수위 높은 묘사 중심"
}

CHARACTERS = {
    "차도진": {"role": "남자 주인공", "emoji": "🖤", "personality": "냉철한 완벽주의자. '나'에게만 평정심을 잃음. 소유욕이 강함."},
    "서하준": {"role": "서브 남주", "emoji": "☀️", "personality": "다정다감한 헌신남. '나'의 웃음이 최우선 순위."},
    "강이엘": {"role": "라이벌", "emoji": "🌹", "personality": "세련된 외면 뒤 열등감을 숨긴 계산적인 인물."},
    "김치즈": {"role": "절친", "emoji": "🍑", "personality": "낙천적인 맛집 박사. 당당하고 유머러스함."},
    "한유리": {"role": "조력자", "emoji": "🍵", "personality": "남주의 최측근이자 과묵하고 성실한 아군."}
}

# ── 4. 유틸리티 함수 (DB, 파싱, AI) ──────────────────────────
def save_game(user_id: str):
    data = {
        "user_id": user_id,
        "my_name": st.session_state.my_name,
        "my_gender": st.session_state.my_gender,
        "my_personality": json.dumps(st.session_state.my_personality, ensure_ascii=False),
        "genre": st.session_state.genre,
        "sub_genre": json.dumps(st.session_state.get("sub_genre", []), ensure_ascii=False),
        "level": st.session_state.get("level", "로맨스"),
        "messages": st.session_state.messages,
        "affection": st.session_state.affection,
        "turn_count": st.session_state.turn_count,
    }
    requests.post(f"{SUPABASE_URL}/rest/v1/save_data", headers=HEADERS, json=data)

def load_game(user_id: str):
    res = requests.get(f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}", headers=HEADERS)
    data = res.json()
    return data[0] if data else None

def parse_affection(text: str, current: dict) -> dict:
    updated = current.copy()
    for char in CHARACTERS:
        # 기호(+)가 없어도 파싱 가능하도록 개선
        match = re.search(rf"\[{char}\s*([+-]?\d+)\]", text)
        if match:
            delta = int(match.group(1))
            delta = max(-5, min(5, delta))
            updated[char] = max(0, min(100, current.get(char, 5) + delta))
    return updated

def get_ai_response(system_prompt: str, api_messages: list) -> tuple[str, str]:
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}] + api_messages,
            temperature=0.95, # 창의성 상향으로 반복 억제
            max_tokens=1000,
        )
        return completion.choices[0].message.content, "Groq"
    except Exception:
        # 폴백: Gemini
        gemini_model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_prompt)
        response = gemini_model.generate_content(api_messages[-1]["content"])
        return response.text, "Gemini"

def clean_text(text: str) -> str:
    return re.sub(r'', '', text, flags=re.DOTALL).strip()

# ── 5. 프롬프트 엔진 (반복 문제 해결) ──────────────────────────
def build_system_prompt() -> str:
    s = st.session_state
    sub_txt = ", ".join(s.get("sub_genre", []))
    
    char_info = ""
    for name, info in CHARACTERS.items():
        a = s.affection.get(name, 5)
        tone = "친근한 반말" if a >= 60 else "격식 있는 말투"
        char_info += f"- {name}: {info['personality']} (현재 호감도: {a}, 말투: {tone})\n"

    return f"""
너는 한국 최고의 웹소설 작가야. 독자가 주인공인 인터랙티브 소설을 집필해줘.

[세계관 및 설정]
- 장르: {s.genre} (로맨스 전제)
- 세부 키워드: {sub_txt}
- 수위: {s.level} ({LEVEL_OPTIONS.get(s.level, "")})
- 주인공: {s.my_name} ({s.my_gender}), 성격: {", ".join(s.my_personality)}

[등장인물]
{char_info}

■ 절대 규칙
- 오직 완벽한 한국어만 사용
- 영어·한자·러시아어·일본어 등 외국어 한 글자도 절대 금지
- 몰입감 있는 문학적 문체 유지
- 사용자 입력을 자연스럽게 스토리에 녹여낼 것
- 본인을 3인칭 시점으로 부르지 않았으면 좋겠어
- 똑같은 단어를 지속적으로 반복하는 행위 금지

■ 문장 품질 규칙
- 같은 단어를 한 문단에서 2회 이상 반복 금지
- 같은 장소 표현 반복 금지. 한 번 쓴 장소명은 이후 생략하거나 다르게 표현
- 나쁜 예: "서재 안에서 회의를 하는 동안 차도진은 서재 안에서 그녀를 기다렸다. 차도진은 그녀의 마음을 읽는 차도진이었다."
- 좋은 예: "밀폐된 서재 너머로 낮은 목소리들이 흘러나왔다. 도진은 문가에 기댄 채 묵묵히 시간을 죽였다. 이따금씩 문 쪽을 향하는 그의 서늘한 눈빛만이 초조함을 드러낼 뿐이었다."
"""

# ── 6. UI 로직 ───────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.update({
        "step": "login", "messages": [], "affection": {n: 5 for n in CHARACTERS}, "turn_count": 0
    })

# STEP: 로그인
if st.session_state.step == "login":
    st.title("📖 당신의 이야기")
    name = st.text_input("이름")
    password = st.text_input("비밀번호", type="password")
    if st.button("시작하기") and name and password:
        user_id = hashlib.sha256(f"{name}{password}".encode()).hexdigest()[:16]
        st.session_state.user_id = user_id
        saved = load_game(user_id)
        if saved:
            st.session_state.update(saved)
            st.session_state.step = "story"
        else: st.session_state.step = "setup"
        st.rerun()

# STEP: 주인공 설정
elif st.session_state.step == "setup":
    st.title("✍️ 주인공 설정")
    st.session_state.my_name = st.text_input("주인공 이름", "예진")
    st.session_state.my_gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    st.session_state.my_personality = st.multiselect("성격 (최대 3개)", ["당차고 독립적", "따뜻함", "냉정함", "유머러스"], max_selections=3)
    if st.button("다음"): st.session_state.step = "genre_select"; st.rerun()

# STEP: 장르 및 세부 설정 (제안해주신 UI 구조)
elif st.session_state.step == "genre_select":
    st.title("🎭 장르 및 세부 설정")
    
    # 대분류
    genre = st.selectbox("대분류 (로맨스 기본 포함)", list(GENRE_CONFIG.keys()))
    
    # 소분류 (키워드)
    st.markdown(f"**{genre}** 세부 키워드 선택")
    sub_categories = GENRE_CONFIG[genre]["sub_categories"]
    cols = st.columns(3)
    selected_subs = []
    for i, sub in enumerate(sub_categories):
        with cols[i%3]:
            if st.checkbox(sub): selected_subs.append(sub)
    
    # 수위
    st.divider()
    level = st.select_slider("수위 선택", options=list(LEVEL_OPTIONS.keys()), value="로맨스")
    st.caption(LEVEL_OPTIONS[level])
    
    if st.button("이야기 시작하기"):
        st.session_state.update({"genre": genre, "sub_genre": selected_subs, "level": level})
        # 오프닝 생성 로직 호출 후 story 단계로 이동
        st.session_state.step = "story"
        st.rerun()

# STEP: 메인 스토리
elif st.session_state.step == "story":
    st.title(f"{st.session_state.genre} - {st.session_state.level}")
    
    # 메시지 출력
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(clean_text(m["content"]))
    
    # 오프닝이 없을 경우 자동 생성
    if not st.session_state.messages:
        with st.spinner("첫 장면을 쓰는 중..."):
            res, _ = get_ai_response(build_system_prompt(), [{"role": "user", "content": "이야기 시작"}])
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.rerun()

    # 입력창
    if prompt := st.chat_input("행동이나 대사를 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("작가님이 집필 중..."):
                res, model = get_ai_response(build_system_prompt(), st.session_state.messages[-10:])
                st.markdown(clean_text(res))
                if model == "Gemini": st.toast("Gemini 엔진이 도움을 주었습니다.")
                
        st.session_state.affection = parse_affection(res, st.session_state.affection)
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.session_state.turn_count += 1
        save_game(st.session_state.user_id)
