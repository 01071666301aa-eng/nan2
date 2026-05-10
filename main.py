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

# ── 3. 캐릭터 설정 ───────────────────────────────────────────
CHARACTERS = {
    "차도진": {
        "role": "남자 주인공",
        "emoji": "🖤",
        "personality": (
            "냉철하고 분석적인 완벽주의자. '나'의 일에서만 평정심을 잃음. "
            "소유욕 강하고 뒤에서 조용히 챙겨주는 키다리 아저씨형. "
            "말투: 단호하고 간결한 문어체. '~했나?', '필요 없어.' "
            "감정이 격해지면 넥타이를 거칠게 푸는 버릇이 있음."
        ),
    },
    "서하준": {
        "role": "서브 남자 주인공",
        "emoji": "☀️",
        "personality": (
            "공감 능력이 뛰어나고 다정다감한 만인의 연인. "
            "'나'의 웃음을 인생 최우선 순위로 둠. 헌신적이고 감성적. "
            "말투: 다정한 구어체, 질문형 문장 많음. '밥은 먹었어?', '~할까?' "
            "항상 주머니에 '나'가 좋아하는 사탕을 넣고 다님."
        ),
    },
    "강이엘": {
        "role": "갈등 유발자",
        "emoji": "🌹",
        "personality": (
            "세련된 외면 뒤에 열등감과 욕망을 숨긴 라이벌. "
            "계산이 빠르고 원하는 것을 위해 수단 방법을 가리지 않음. "
            "말투: 우아하지만 뼈 있는 말투. '~하나 봐요?', '어머, 몰랐네.' "
            "긴 생머리를 손가락으로 배배 꼬며 상대를 위아래로 훑어보는 습관."
        ),
    },
    "김치즈": {
        "role": "개그 캐릭터 / 절친",
        "emoji": "🍑",
        "personality": (
            "극강의 낙천주의자. 맛집과 가십에 빠삭한 '나'의 절친. "
            "즉흥적이고 친화력 갑. 남주 앞에서도 기죽지 않는 당당함. "
            "말투: 줄임말과 신조어 섞은 유쾌한 말투. '대박 사건!', '실화냐고~' "
            "가방 속에 항상 정체 모를 간식이 들어있음."
        ),
    },
    "한유리": {
        "role": "조력자",
        "emoji": "🍵",
        "personality": (
            "남주의 최측근이자 '나'의 든든한 아군. 두 사람의 징검다리 역할. "
            "과묵하고 성실하며 남주의 속마음을 누구보다 빠르게 캐치함. "
            "말투: 극도로 격식 차린 비즈니스 말투. '~입니다만.', '전달하겠습니다.' "
            "안경을 치켜올릴 때 렌즈가 번쩍이는 연출이 자주 등장함."
        ),
    },
}

GENRE_SETTINGS = {
    "로맨스": {
        "emoji": "💌",
        "desc": "현대 배경의 달콤 쌉싸름한 로맨스",
        "world": "현대 대도시. 차도진은 대기업 CEO, 서하준은 그의 오랜 친구이자 의사. 강이엘은 비즈니스 파트너. '나'는 우연히 이 세계에 발을 들이게 된 인물.",
    },
    "로판": {
        "emoji": "⚔️",
        "desc": "이세계 귀족 사회의 로맨스 판타지",
        "world": "마법이 존재하는 귀족 사회. 차도진은 냉혹한 공작, 서하준은 왕국의 기사단장. 강이엘은 라이벌 귀족 가문의 영애. '나'는 이 세계에 빙의한 인물.",
    },
    "학원": {
        "emoji": "🏫",
        "desc": "명문고등학교를 배경으로 한 청춘 로맨스",
        "world": "명문 사립 고등학교. 차도진은 전교 1등 냉정한 학생회장, 서하준은 인기 많은 축구부 에이스. 강이엘은 학교 퀸카. '나'는 전학생.",
    },
    "성인로맨스": {
        "emoji": "🥂",
        "desc": "성인들의 복잡한 감정과 관계를 그린 로맨스",
        "world": "현대 도시의 고급 비즈니스 세계. 차도진은 냉철한 투자회사 대표, 서하준은 유명 외과의. 강이엘은 패션 업계의 실력자. '나'는 이 세계와 얽히게 된 인물. 성인들의 복잡한 감정선과 농밀한 분위기를 중심으로 전개.",
    },
}

PERSONALITY_OPTIONS = [
    "당차고 독립적", "소심하지만 따뜻함", "4차원 엉뚱함",
    "현실적이고 냉정함", "감성적이고 예민함", "유머감각 넘침",
    "호기심 많고 활발함", "조용하지만 관찰력 뛰어남"
]

# ── 4. Supabase ───────────────────────────────────────────────
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

# ── 5. 호감도 파싱 (변동폭 ±10 제한) ────────────────────────
def parse_affection(text: str, current: dict) -> dict:
    updated = current.copy()
    # [차도진 호감도: 숫자] 형식 파싱
    for char in CHARACTERS:
        match = re.search(rf"\[{char}\s*호감도:\s*(\d+)\]", text)
        if match:
            new_val = int(match.group(1))
            old_val = current.get(char, 5)
            delta = max(-10, min(10, new_val - old_val))
            updated[char] = max(0, min(100, old_val + delta))
    return updated

# ── 6. AI 응답 (Groq → Gemini 폴백) ─────────────────────────
def get_ai_response(system_prompt: str, api_messages: list) -> tuple[str, str]:
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}] + api_messages,
            temperature=0.85,
            top_p=0.9,
            max_tokens=800,
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

# ── 7. 시스템 프롬프트 생성 ──────────────────────────────────
def build_system_prompt() -> str:
    my      = st.session_state.my_name
    traits  = ", ".join(st.session_state.my_personality)
    intro   = st.session_state.my_intro or "특별한 소개 없음"
    gender = st.session_state.my_gender
    genre   = st.session_state.genre
    world   = GENRE_SETTINGS[genre]["world"]

    char_desc = ""
    for name, info in CHARACTERS.items():
        char_desc += f"\n### {name} ({info['role']})\n{info['personality']}\n"

    return f"""\
너는 한국 웹소설 작가야. 지금부터 독자가 직접 참여하는 인터랙티브 웹소설을 진행해.

■ 세계관 및 장르: {genre}
{world}

■ 주인공 '나' 설정
- 이름: {my}
- 성별: {gender}
- 성격: {traits}
- 소개: {intro}

■ 등장인물
{char_desc}

■ 출력 형식 (반드시 준수)
1. [장소 — 시간대] 형식으로 배경 표시
2. 전지적 작가 시점의 소설체(~다/~했다)로 상황 묘사
3. 등장인물 대사: "이름: "대사"" 형식
4. 상황에 맞는 인물만 등장 (1~3명 적절히 선택)
5. 마지막 줄에 등장한 캐릭터의 호감도만 표시:
   [캐릭터이름 호감도: 숫자]

■ 호감도 규칙
- 각 캐릭터 시작값: 5, 범위: 0~100
- '나'의 행동·말에 따라 자연스럽게 변동
- 절대 한 번에 10점 이상 변동 금지

■ 사용자가 "/호감도" 입력 시
모든 캐릭터의 현재 호감도를 표로 출력하고 간단한 관계 코멘트 추가

■ 장르별 분위기
- 로맨스/학원: 설렘과 감정선 중심
- 로판: 웅장한 세계관과 운명적 만남
- 성인로맨스: 농밀한 감정선, 절제된 표현 안에서 최대한의 긴장감과 욕망 묘사

■ 절대 규칙
- 오직 한국어만 사용
- 영어·한자·외국어 절대 금지
- 몰입감 있는 문학적 문체 유지
- 사용자 입력을 자연스럽게 스토리에 녹여낼 것
"""

# ════════════════════════════════════════════════════════════
# UI 시작
# ════════════════════════════════════════════════════════════

# ── 8. 세션 상태 초기화 ──────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step       = "login"      # login / setup / genre / intro / story
    st.session_state.user_id    = None
    st.session_state.my_name    = ""
    st.session_state.my_personality = []
    st.session_state.my_intro   = ""
    st.session_state.genre      = ""
    st.session_state.messages   = []
    st.session_state.affection  = {name: 5 for name in CHARACTERS}
    st.session_state.turn_count = 0

# ── 9. STEP 1: 로그인 ────────────────────────────────────────
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
                st.session_state.my_personality = json.loads(saved["my_personality"])
                st.session_state.my_intro       = saved["my_intro"]
                st.session_state.genre          = saved["genre"]
                st.session_state.messages       = saved["messages"]
                st.session_state.affection      = saved["affection"]
                st.session_state.turn_count     = saved["turn_count"]
                st.session_state.step           = "story"
            else:
                st.session_state.step = "setup"
        st.rerun()

    elif (start or reset) and not (name and password):
        st.warning("이름과 비밀번호를 입력해주세요.")

# ── 10. STEP 2: 주인공 설정 ──────────────────────────────────
elif st.session_state.step == "setup":
    st.title("✍️ 주인공 설정")
    st.caption("이야기 속 '나'를 만들어주세요.")
    st.divider()

    my_name = st.text_input("주인공 이름", placeholder="예: 이하늘")

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
            st.session_state.my_personality = selected
            st.session_state.my_intro       = my_intro
            st.session_state.step           = "genre"
            st.rerun()

# ── 11. STEP 3: 장르 선택 (타로카드) ─────────────────────────
elif st.session_state.step == "genre":
    st.title("🃏 장르를 선택하세요")
    st.caption("카드를 뽑아 당신의 이야기를 시작하세요.")
    st.divider()

    cols = st.columns(2)
    genre_list = list(GENRE_SETTINGS.items())

    for i, (genre_name, info) in enumerate(genre_list):
        with cols[i % 2]:
            st.markdown(f"### {info['emoji']} {genre_name}")
            st.caption(info["desc"])
            if st.button(f"{genre_name} 선택", key=f"genre_{genre_name}", use_container_width=True):
                st.session_state.genre = genre_name
                st.session_state.step  = "intro"
                st.rerun()

# ── 12. STEP 4: 캐릭터 소개 ──────────────────────────────────
elif st.session_state.step == "intro":
    genre_info = GENRE_SETTINGS[st.session_state.genre]
    st.title(f"{genre_info['emoji']} {st.session_state.genre}")
    st.markdown(f"**{genre_info['world']}**")
    st.divider()

    st.markdown("### 등장인물")
    for name, info in CHARACTERS.items():
        with st.expander(f"{info['emoji']} {name} — {info['role']}"):
            st.write(info["personality"])

    st.divider()
    if st.button("📖 이야기 시작하기", use_container_width=True):
        # 첫 오프닝 생성
        system_prompt = build_system_prompt()
        opening_request = [{"role": "user", "content": "이야기를 시작해줘. 첫 장면을 웹소설 도입부처럼 감각적으로 써줘."}]
        with st.spinner("첫 번째 장면을 쓰는 중..."):
            try:
                response, _ = get_ai_response(system_prompt, opening_request)
                st.session_state.messages = [{"role": "assistant", "content": response}]
                st.session_state.affection = {name: 5 for name in CHARACTERS}
                st.session_state.turn_count = 0
                save_game(st.session_state.user_id)
                st.session_state.step = "story"
                st.rerun()
            except Exception as e:
                st.error(f"오류가 발생했어요: {e}")

# ── 13. STEP 5: 메인 스토리 ──────────────────────────────────
elif st.session_state.step == "story":
    genre_info = GENRE_SETTINGS[st.session_state.genre]

    # 상단 UI
    st.title(f"{genre_info['emoji']} {st.session_state.genre}")
    st.caption(f"주인공: {st.session_state.my_name}  |  {' · '.join(st.session_state.my_personality)}")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("← 로그아웃"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.divider()

    # 대화 출력
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="📖"):
                st.markdown(msg["content"])

    # 입력 처리
    hint = "이야기를 이어가세요... (호감도 확인: /호감도)"
    if prompt := st.chat_input(hint):

        # /호감도 명령어
        if prompt.strip() == "/호감도":
            aff = st.session_state.affection
            result = "### 📊 현재 호감도\n\n"
            for char, val in aff.items():
                info = CHARACTERS[char]
                bar = "█" * (val // 10) + "░" * (10 - val // 10)
                label = (
                    "💗 연인 단계"   if val >= 90 else
                    "🌸 친밀한 사이" if val >= 60 else
                    "😐 평범한 관계" if val >= 30 else
                    "🧊 차가운 사이"
                )
                result += f"**{info['emoji']} {char}** ({info['role']})\n"
                result += f"`{bar}` {val}/100  {label}\n\n"
            with st.chat_message("assistant", avatar="📊"):
                st.markdown(result)
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
                        st.markdown(response)

                        if used_model == "Gemini":
                            st.toast("⚡ Gemini로 자동 전환됐어요!", icon="🔄")

                        # 호감도 업데이트
                        new_aff = parse_affection(response, st.session_state.affection)
                        st.session_state.affection = new_aff

                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.session_state.turn_count += 1
                        save_game(st.session_state.user_id)
                        st.rerun()

                    except Exception as e:
                        st.error(f"오류가 발생했어요: {e}")
