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

# ── 3. 캐릭터 설정 & 고유 색상 ──────────────────────────────
CHARACTERS = {
    "차도진": {
        "role": "남자 주인공",
        "emoji": "🖤",
        "color": "#7EB8D4",   # 차가운 블루
        "personality": (
            "냉철하고 분석적인 완벽주의자. '나'의 일에서만 평정심을 잃음. "
            "소유욕 강하고 뒤에서 조용히 챙겨주는 키다리 아저씨형. "
            "감정이 격해지면 넥타이를 거칠게 푸는 버릇이 있음. "
            "말투 예시: '오늘 왜 거기 있었어.', '그거 내가 처리했어.', '...됐어.'"
        ),
    },
    "서하준": {
        "role": "서브 남자 주인공",
        "emoji": "☀️",
        "color": "#F5C842",   # 따뜻한 옐로우
        "personality": (
            "공감 능력이 뛰어나고 다정다감한 만인의 연인. "
            "'나'의 웃음을 인생 최우선 순위로 둠. 헌신적이고 감성적. "
            "항상 주머니에 '나'가 좋아하는 사탕을 넣고 다님. "
            "말투 예시: '밥은 먹었어?', '많이 힘들었겠다.', '나 여기 있잖아.'"
        ),
    },
    "강이엘": {
        "role": "갈등 유발자",
        "emoji": "🌹",
        "color": "#E8837A",   # 장미 레드
        "personality": (
            "세련된 외면 뒤에 열등감과 욕망을 숨긴 라이벌. "
            "계산이 빠르고 원하는 것을 위해 수단 방법을 가리지 않음. "
            "긴 생머리를 손가락으로 배배 꼬며 상대를 위아래로 훑어보는 습관. "
            "말투 예시: '어머, 몰랐어요?', '그게 통할 것 같아서요?', '재밌네.'"
        ),
    },
    "김치즈": {
        "role": "절친",
        "emoji": "🍑",
        "color": "#F4A261",   # 복숭아 오렌지
        "personality": (
            "극강의 낙천주의자. 맛집과 가십에 빠삭한 '나'의 절친. "
            "즉흥적이고 친화력 갑. 남주 앞에서도 기죽지 않는 당당함. "
            "가방 속에 항상 정체 모를 간식이 들어있음. "
            "말투 예시: '대박 사건!', '실화냐고~', '야 잠깐만 이거 들어봐.'"
        ),
    },
    "한유리": {
        "role": "조력자",
        "emoji": "🍵",
        "color": "#80C9A0",   # 차분한 그린
        "personality": (
            "남주의 최측근이자 '나'의 든든한 아군. 두 사람의 징검다리 역할. "
            "과묵하고 성실하며 남주의 속마음을 누구보다 빠르게 캐치함. "
            "안경을 치켜올릴 때 렌즈가 번쩍이는 연출이 자주 등장함. "
            "말투 예시: '전달하겠습니다.', '대표님이 그러셨습니다.', '...참고하시죠.'"
        ),
    },
}

# ── 4. 장르 설정 ─────────────────────────────────────────────
GENRES = {
    "🏫 학원":        "명문 사립학교. 차도진은 냉정한 학생회장, 서하준은 축구부 에이스, 강이엘은 퀸카, 김치즈는 '나'의 절친, 한유리는 학생회 총무. '나'는 전학생.",
    "🌆 현대 로맨스": "현대 대도시. 차도진은 대기업 CEO, 서하준은 의사, 강이엘은 비즈니스 라이벌, 한유리는 차도진의 비서. '나'는 이 세계에 발을 들인 인물.",
    "⚔️ 판타지·로판": "마법이 존재하는 귀족 사회. 차도진은 냉혹한 공작, 서하준은 기사단장, 강이엘은 라이벌 귀족 영애, 한유리는 공작가 집사. '나'는 빙의한 인물.",
    "📚 시대극":      "조선 후기 또는 근대. 차도진은 냉철한 양반 도령 혹은 독립운동가, 서하준은 의원, 강이엘은 기생 혹은 라이벌 귀족 여식. '나'는 신분을 숨긴 인물.",
    "⚽ 스포츠":      "프로 스포츠 구단. 차도진은 에이스 선수 혹은 냉철한 감독, 서하준은 팀 주치의, 강이엘은 라이벌 팀 관계자, 김치즈는 동료. '나'는 구단 관계자.",
    "☕ 일상":        "평범한 동네와 카페. 차도진은 옆 건물 거주 냉소적인 직장인, 서하준은 동네 단골 의사, 강이엘은 직장 동료, 김치즈는 절친. '나'는 카페 혹은 직장인.",
}

# ── 5. 수위 설정 ─────────────────────────────────────────────
RATINGS = {
    "🌸 순애":       "감정선 중심. 스킨십은 손잡기·포옹 수준. 설렘과 감정 묘사에 집중.",
    "💫 로맨스":     "자연스러운 감정 표현과 적당한 스킨십 허용. 키스 등 포함 가능.",
    "🥂 성인 로맨스": "성인 감정선. 농밀한 분위기와 욕망 묘사. 절제된 표현 안에서 최대한의 긴장감.",
}

# ── 6. 관계 프리셋 ───────────────────────────────────────────
RELATIONS = {
    "🤝 처음 만나는 사이": {
        "start_affection": 5,
        "desc": "오늘 처음 마주친 완전한 초면. 어색함과 긴장감이 공존하는 첫 만남.",
    },
    "📖 인연이 있던 사이": {
        "start_affection": 20,
        "desc": "과거에 스친 적 있거나 짧게 알고 지낸 사이. 서로에 대한 인상이 남아있음.",
    },
    "💫 재회하는 사이": {
        "start_affection": 35,
        "desc": "한때 가까웠지만 오랫동안 떨어져 있다 다시 만난 사이. 쌓인 감정과 여운이 있음.",
    },
}

PERSONALITY_OPTIONS = [
    "당차고 독립적", "소심하지만 따뜻함", "4차원 엉뚱함",
    "현실적이고 냉정함", "감성적이고 예민함", "유머감각 넘침",
    "호기심 많고 활발함", "조용하지만 관찰력 뛰어남"
]

# ── 7. Supabase ───────────────────────────────────────────────
def save_game(user_id: str):
    data = {
        "user_id":        user_id,
        "my_name":        st.session_state.my_name,
        "my_gender":      st.session_state.my_gender,
        "my_personality": json.dumps(st.session_state.my_personality, ensure_ascii=False),
        "my_intro":       st.session_state.my_intro,
        "genre":          st.session_state.genre,
        "messages":       st.session_state.messages,
        "affection":      st.session_state.affection,
        "turn_count":     st.session_state.turn_count,
    }
    requests.post(f"{SUPABASE_URL}/rest/v1/save_data", headers=HEADERS, json=data)

def load_game(user_id: str):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}",
        headers=HEADERS
    )
    data = res.json()
    return data[0] if data else None

# ── 8. 호감도 파싱 (변화량 방식, ±5 강제 제한) ──────────────
def parse_affection(text: str, current: dict) -> dict:
    updated = current.copy()
    for char in CHARACTERS:
        match = re.search(rf"\[{char}\s*([+-]\d+)\]", text)
        if match:
            delta = int(match.group(1))
            delta = max(-5, min(5, delta))
            old_val = current.get(char, 5)
            updated[char] = max(0, min(100, old_val + delta))
    return updated

# ── 9. AI 응답 (Groq → Gemini 폴백) ─────────────────────────
def get_ai_response(system_prompt: str, api_messages: list) -> tuple[str, str]:
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}] + api_messages,
            temperature=0.92,
            top_p=0.9,
            max_tokens=900,
        )
        return completion.choices[0].message.content, "Groq"
    except Exception as e:
        if "429" in str(e) or "rate_limit" in str(e).lower():
            try:
                gemini_history = []
                for msg in api_messages[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({"role": role, "parts": [msg["content"]]})
                last_msg = api_messages[-1]["content"]
                gemini_model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    system_instruction=system_prompt
                )
                chat = gemini_model.start_chat(history=gemini_history)
                response = chat.send_message(last_msg)
                return response.text, "Gemini"
            except Exception as gemini_err:
                raise Exception(f"Groq·Gemini 모두 실패: {gemini_err}")
        else:
            raise e

MAX_TURNS = 10
def get_trimmed_messages():
    return st.session_state.messages[-(MAX_TURNS * 2):]

# ── 10. 텍스트 정제 & 색상 적용 ─────────────────────────────
def clean_text(text: str) -> str:
    """HTML 주석(호감도) 제거"""
    return re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL).strip()

def colorize_dialogue(text: str) -> str:
    """캐릭터 대사에 고유 색상 적용"""
    for name, info in CHARACTERS.items():
        color = info["color"]
        # 이름: "대사" 형식에 색상 적용
        text = re.sub(
            rf'({re.escape(name)}:\s*"[^"]*")',
            rf'<span style="color:{color}; font-weight:600">\1</span>',
            text
        )
    return text

def render_message(text: str):
    """주석 제거 + 색상 적용 후 렌더링"""
    cleaned = clean_text(text)
    colored = colorize_dialogue(cleaned)
    st.markdown(colored, unsafe_allow_html=True)

# ── 11. 시스템 프롬프트 생성 ─────────────────────────────────
def build_system_prompt() -> str:
    my       = st.session_state.my_name
    gender   = st.session_state.my_gender
    traits   = ", ".join(st.session_state.my_personality)
    intro    = st.session_state.my_intro or "특별한 소개 없음"
    genre    = st.session_state.genre
    rating   = st.session_state.rating
    relation = st.session_state.relation
    world    = GENRES.get(genre, "")
    rating_guide = RATINGS.get(rating, "")
    relation_desc = RELATIONS.get(relation, {}).get("desc", "")
    aff      = st.session_state.affection

    char_desc = ""
    for name, info in CHARACTERS.items():
        a = aff.get(name, 5)
        if a >= 90:
            tone = "감정을 숨기지 않는 다정하고 솔직한 말투. 연인처럼 자연스러운 반말. 애칭 사용 가능."
        elif a >= 60:
            tone = "편한 친구 같은 자연스러운 20~30대 반말. 가끔 장난기도 섞임."
        elif a >= 30:
            tone = "친근해지기 시작하는 반말. 아직 약간의 거리감이 남아있음."
        else:
            tone = "거리감 있는 말투. 단답형이 많고 불필요한 말은 하지 않음. 절대 고어체·번역투 금지."
        char_desc += f"\n### {name} ({info['role']})\n{info['personality']}\n현재 말투: {tone}\n"

    return f"""\
너는 한국 웹소설 작가야. 독자가 직접 참여하는 인터랙티브 웹소설을 써줘.

■ 세계관: {genre}
{world}

■ 주인공 설정
- 이름: {my}
- 성별: {gender} (절대 혼동 금지. 모든 장면에서 일관되게 유지.)
- 성격: {traits}
- 소개: {intro}

■ 관계 설정: {relation}
{relation_desc}

■ 수위: {rating}
{rating_guide}

■ 등장인물
{char_desc}

■ 출력 형식 (반드시 준수)
1. [장소 — 시간대] 형식으로 배경 표시
2. 별도 태그 없이 바로 소설 문체로 서술. '[전지적 작가 시점]' 같은 메타 태그 절대 사용 금지.
3. 문체는 한국 정통 웹소설 스타일. 간결하고 감각적인 문장. 너무 길거나 설명적인 문장 금지.
   좋은 예: "차도진이 서류를 덮었다. 그의 시선이 천천히 정예진에게로 향했다."
   나쁜 예: "정예진은 이 세계의 이치와 법칙을 풀어헤쳐 볼 수 있는 기회가 있을까 생각했습니다."
4. 등장인물 대사는 반드시 앞뒤로 빈 줄을 넣어 단독 줄로 표기:
   형식: 이름: "대사"
   
   좋은 예:
   차도진이 천천히 고개를 들었다. 그의 눈빛이 싸늘하게 가라앉았다.
   
   차도진: "늦었군."
   
   정예진은 아무 말도 하지 못했다.
   
   나쁜 예:
   차도진이 고개를 들며 차도진: "늦었군." 이라고 말했다.
5. 상황에 맞는 인물만 등장 (1~3명)
6. 본문 마지막에 아래 형식으로 호감도 변화량만 HTML 주석으로 표기:
   <!-- [캐릭터이름 +숫자] [캐릭터이름 -숫자] -->
   예: <!-- [차도진 +2] [서하준 -1] -->
   - 등장한 캐릭터만 표기할 것
   - 변화량은 반드시 -5 ~ +5 사이로만 작성
   - 절댓값 호감도 숫자는 절대 쓰지 마라
   - 본문에 호감도 관련 텍스트가 보이면 절대 안 됨

■ 호감도 규칙
- 각 캐릭터 시작값: 5 / 범위: 0~100
- '나'의 행동·말에 따라 자연스럽게 변동
- 한 턴에 최대 ±5점 변동
- 호감도가 높아질수록 말투가 자연스럽고 친근하게 변함

■ 말투 변화 분기
- 0~29점: 친근해지는 10~20대 반말 시작
- 30~59점: 편한 친구 같은 자연스러운 반말
- 60~89점: 이름을 불러줄 때 사용자의 이름만 불러줬으면 좋겠어.
- 90~100점: 감정 솔직한 다정한 말투

■ /호감도 명령어
사용자가 "/호감도" 입력 시에만 모든 캐릭터 호감도를 표로 출력

■ 장르별 분위기
- 로맨스/학원: 설렘과 감정선 중심
- 로판: 웅장한 세계관과 운명적 만남
- 성인로맨스: 농밀한 감정선, 절제된 표현 안에서 최대한의 긴장감과 욕망 묘사

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

# ════════════════════════════════════════════════════════════
# UI 시작
# ════════════════════════════════════════════════════════════

# ── 12. 세션 상태 초기화 ─────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step           = "login"
    st.session_state.user_id        = None
    st.session_state.my_name        = ""
    st.session_state.my_gender      = "여성"
    st.session_state.my_personality = []
    st.session_state.my_intro       = ""
    st.session_state.genre          = ""
    st.session_state.rating         = ""
    st.session_state.relation       = ""
    st.session_state.messages       = []
    st.session_state.affection      = {name: 5 for name in CHARACTERS}
    st.session_state.turn_count     = 0

# ── 13. STEP 1: 로그인 ───────────────────────────────────────
if st.session_state.step == "login":
    st.title("📖 당신의 이야기")
    st.caption("나만의 웹소설을 시작하세요.")
    st.divider()

    name     = st.text_input("이름", placeholder="예: 종완")
    password = st.text_input("비밀번호", type="password", placeholder="본인만 아는 비밀번호")

    col1, col2 = st.columns(2)
    with col1:
        start = st.button("▶ 시작 / 이어하기", use_container_width=True)
    with col2:
        reset = st.button("🗑 처음부터 다시", use_container_width=True)

    if (start or reset) and name and password:
        user_id = hashlib.sha256(f"{name}{password}".encode()).hexdigest()[:16]
        st.session_state.user_id = user_id

        if reset:
            requests.delete(
                f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}",
                headers=HEADERS
            )
            st.session_state.step = "setup"
        else:
            saved = load_game(user_id)
            if saved:
                st.session_state.my_name        = saved["my_name"]
                st.session_state.my_gender      = saved.get("my_gender", "여성")
                st.session_state.my_personality = json.loads(saved["my_personality"])
                st.session_state.my_intro       = saved["my_intro"]
                st.session_state.genre          = saved["genre"]
                st.session_state.rating         = saved.get("rating", "💫 로맨스")
                st.session_state.relation       = saved.get("relation", "🤝 처음 만나는 사이")
                st.session_state.messages       = saved["messages"]
                st.session_state.affection      = saved["affection"]
                st.session_state.turn_count     = saved["turn_count"]
                st.session_state.step           = "story"
            else:
                st.session_state.step = "setup"
        st.rerun()

    elif (start or reset) and not (name and password):
        st.warning("이름과 비밀번호를 입력해주세요.")

# ── 14. STEP 2: 주인공 설정 ──────────────────────────────────
elif st.session_state.step == "setup":
    st.title("✍️ 주인공 설정")
    st.caption("이야기 속 '나'를 만들어주세요.")
    st.divider()

    my_name   = st.text_input("주인공 이름", placeholder="예: 이하늘")
    my_gender = st.radio("성별", ["여성", "남성"], horizontal=True)

    st.markdown("**성격 키워드** (최대 3개 선택)")
    selected = []
    cols = st.columns(2)
    for i, opt in enumerate(PERSONALITY_OPTIONS):
        with cols[i % 2]:
            if st.checkbox(opt, key=f"trait_{i}"):
                selected.append(opt)

    my_intro = st.text_input(
        "한 줄 소개 (선택)",
        placeholder="예: 평범한 척하지만 사실 반전매력 있음"
    )

    if len(selected) > 3:
        st.warning("성격 키워드는 최대 3개까지만 선택할 수 있어요.")

    if st.button("다음 →", use_container_width=True):
        if not my_name:
            st.warning("주인공 이름을 입력해주세요.")
        elif len(selected) == 0:
            st.warning("성격 키워드를 최소 1개 선택해주세요.")
        elif len(selected) > 3:
            st.warning("성격 키워드는 최대 3개까지만 선택할 수 있어요.")
        else:
            st.session_state.my_name        = my_name
            st.session_state.my_gender      = my_gender
            st.session_state.my_personality = selected
            st.session_state.my_intro       = my_intro
            st.session_state.step           = "genre"
            st.rerun()

# ── 15. STEP 3: 장르 선택 ────────────────────────────────────
elif st.session_state.step == "genre":
    st.title("🃏 장르 선택")
    st.caption("이야기의 배경을 골라주세요.")
    st.divider()

    cols = st.columns(2)
    for i, (genre_name, world_desc) in enumerate(GENRES.items()):
        with cols[i % 2]:
            st.markdown(f"### {genre_name}")
            st.caption(world_desc[:40] + "...")
            if st.button(f"선택", key=f"genre_{i}", use_container_width=True):
                st.session_state.genre = genre_name
                st.session_state.step  = "rating"
                st.rerun()

# ── 16. STEP 4: 수위 선택 ────────────────────────────────────
elif st.session_state.step == "rating":
    st.title("✨ 수위 선택")
    st.caption("이야기의 분위기를 설정해주세요.")
    st.divider()

    for rating_name, rating_desc in RATINGS.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{rating_name}**")
            st.caption(rating_desc)
        with col2:
            if st.button("선택", key=f"rating_{rating_name}", use_container_width=True):
                st.session_state.rating = rating_name
                st.session_state.step   = "relation"
                st.rerun()
        st.divider()

# ── 17. STEP 5: 관계 프리셋 선택 ─────────────────────────────
elif st.session_state.step == "relation":
    st.title("💫 관계 설정")
    st.caption("등장인물들과의 관계를 설정해주세요.")
    st.divider()

    for rel_name, rel_info in RELATIONS.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{rel_name}**")
            st.caption(rel_info["desc"])
        with col2:
            if st.button("선택", key=f"rel_{rel_name}", use_container_width=True):
                st.session_state.relation  = rel_name
                start_aff = rel_info["start_affection"]
                st.session_state.affection = {name: start_aff for name in CHARACTERS}
                st.session_state.step      = "intro"
                st.rerun()
        st.divider()

# ── 18. STEP 6: 캐릭터 소개 & 프롤로그 생성 ──────────────────
elif st.session_state.step == "intro":
    st.title("📖 등장인물")
    st.caption(f"{st.session_state.genre}  |  {st.session_state.rating}  |  {st.session_state.relation}")
    st.divider()

    for name, info in CHARACTERS.items():
        with st.expander(f"{info['emoji']} {name}"):
            st.markdown(
                f"<span style='color:{info['color']}'>{info['personality']}</span>",
                unsafe_allow_html=True
            )

    st.divider()
    if st.button("📖 이야기 시작하기", use_container_width=True):
        system_prompt = build_system_prompt()

        # 관계에 따라 프롤로그 여부 결정
        relation = st.session_state.relation
        if relation == "🤝 처음 만나는 사이":
            opening_req = "이야기를 시작해줘. 주인공과 등장인물들이 처음 만나는 첫 장면을 웹소설 도입부처럼 감각적으로 써줘."
        elif relation == "📖 인연이 있던 사이":
            opening_req = (
                "이야기를 시작해줘. 먼저 2~3문장으로 두 사람의 짧은 과거 인연을 프롤로그처럼 써준 뒤, "
                "현재 장면으로 자연스럽게 이어줘. 웹소설 도입부 스타일로."
            )
        else:  # 재회
            opening_req = (
                "이야기를 시작해줘. 먼저 3~4문장으로 과거 가까웠던 시절과 이별의 서사를 프롤로그처럼 써준 뒤, "
                "오랜만의 재회 장면으로 자연스럽게 이어줘. 웹소설 도입부 스타일로."
            )

        with st.spinner("첫 번째 장면을 쓰는 중..."):
            try:
                response, _ = get_ai_response(system_prompt, [{"role": "user", "content": opening_req}])
                st.session_state.messages   = [{"role": "assistant", "content": response}]
                st.session_state.turn_count = 0
                save_game(st.session_state.user_id)
                st.session_state.step = "story"
                st.rerun()
            except Exception as e:
                st.error(f"오류가 발생했어요: {e}")

# ── 19. STEP 7: 메인 스토리 ──────────────────────────────────
elif st.session_state.step == "story":
    genre_emoji = st.session_state.genre.split()[0]

    st.title(f"{genre_emoji} 당신의 이야기")
    st.caption(
        f"**{st.session_state.my_name}** ({st.session_state.my_gender})  |  "
        f"{st.session_state.genre}  |  {st.session_state.rating}  |  {st.session_state.relation}"
    )

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("← 로그아웃"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # 캐릭터 색상 범례
    with st.expander("🎨 캐릭터 색상 보기"):
        legend_cols = st.columns(5)
        for i, (name, info) in enumerate(CHARACTERS.items()):
            with legend_cols[i]:
                st.markdown(
                    f"<span style='color:{info['color']}'>■</span> {name}",
                    unsafe_allow_html=True
                )

    st.divider()

    # 대화 출력
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="📖"):
                render_message(msg["content"])

    # 입력 처리
    if prompt := st.chat_input("이야기를 이어가세요... (호감도 확인: /호감도)"):

        # /호감도 명령어
        if prompt.strip() == "/호감도":
            aff    = st.session_state.affection
            result = "### 📊 현재 호감도\n\n"
            for char, val in aff.items():
                info  = CHARACTERS[char]
                bar   = "█" * (val // 10) + "░" * (10 - val // 10)
                label = (
                    "💗 연인 단계"   if val >= 90 else
                    "🌸 친밀한 사이" if val >= 60 else
                    "😐 평범한 관계" if val >= 30 else
                    "🧊 차가운 사이"
                )
                result += (
                    f"<span style='color:{info['color']}'>"
                    f"**{info['emoji']} {char}**</span>\n"
                    f"`{bar}` {val}/100  {label}\n\n"
                )
            with st.chat_message("assistant", avatar="📊"):
                st.markdown(result, unsafe_allow_html=True)

        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="📖"):
                with st.spinner("이야기를 쓰는 중..."):
                    try:
                        system_prompt = build_system_prompt()
                        response, used_model = get_ai_response(
                            system_prompt,
                            get_trimmed_messages()
                        )

                        render_message(response)

                        if used_model == "Gemini":
                            st.toast("⚡ Gemini로 자동 전환됐어요!", icon="🔄")

                        new_aff = parse_affection(response, st.session_state.affection)
                        st.session_state.affection = new_aff

                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.session_state.turn_count += 1
                        save_game(st.session_state.user_id)
                        st.rerun()

                    except Exception as e:
                        st.error(f"오류가 발생했어요: {e}")
