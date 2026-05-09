import streamlit as st
from groq import Groq
import google.generativeai as genai
import os
import re
import hashlib
import requests

# ── 1. 페이지 설정 ───────────────────────────────────────────
st.set_page_config(page_title="이서 프로젝트", page_icon="🌙", layout="centered")

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

# ── 3. 아바타 설정 ───────────────────────────────────────────
ISEO_AVATAR = "rem_profile.png"
USER_AVATAR  = "taeha_profile.png"
iseo_avatar = ISEO_AVATAR if os.path.exists(ISEO_AVATAR) else "🌙"
user_avatar  = USER_AVATAR  if os.path.exists(USER_AVATAR)  else "👦"

# ── 4. Supabase 저장/불러오기 ────────────────────────────────
def save_game(user_id: str):
    data = {
        "user_id":    user_id,
        "affection":  st.session_state.affection,
        "messages":   st.session_state.messages,
        "turn_count": st.session_state.turn_count,
        "char_name":  st.session_state.char_name,
    }
    requests.post(
        f"{SUPABASE_URL}/rest/v1/save_data",
        headers=HEADERS,
        json=data
    )

def load_game(user_id: str):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}",
        headers=HEADERS
    )
    data = res.json()
    return data[0] if data else None

# ── 5. 호감도 파싱 ───────────────────────────────────────────
def parse_affection(text: str):
    match = re.search(r"\[현재 호감도:\s*(\d+)\]", text)
    return int(match.group(1)) if match else None

# ── 6. 컨텍스트 윈도우 제한 (최근 10턴) ─────────────────────
MAX_TURNS = 10
def get_trimmed_messages():
    return st.session_state.messages[-(MAX_TURNS * 2):]

# ── 7. AI 응답 함수 (Groq → Gemini 자동 폴백) ───────────────
def get_ai_response(system_prompt: str, api_messages: list) -> tuple[str, str]:
    # 1순위: Groq
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}] + api_messages,
            temperature=0.75,
            top_p=0.9,
            max_tokens=600,
        )
        return completion.choices[0].message.content, "Groq"

    except Exception as e:
        if "429" in str(e) or "rate_limit" in str(e).lower():
            # 2순위: Gemini로 자동 전환
            try:
                gemini_history = []
                for msg in api_messages[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({
                        "role": role,
                        "parts": [msg["content"]]
                    })

                last_user_msg = api_messages[-1]["content"]

                gemini_model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    system_instruction=system_prompt
                )
                chat = gemini_model.start_chat(history=gemini_history)
                response = chat.send_message(last_user_msg)
                return response.text, "Gemini"

            except Exception as gemini_err:
                raise Exception(f"Groq·Gemini 모두 실패: {gemini_err}")
        else:
            raise e

# ── 8. 로그인 화면 ───────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.title("🌙 이서 프로젝트")
    st.caption("당신만의 AI 캐릭터와 대화를 시작하세요.")
    st.divider()

    my_name   = st.text_input("내 이름", placeholder="예: 종완")
    password  = st.text_input("비밀번호", type="password", placeholder="본인만 아는 비밀번호")
    char_name = st.text_input("AI 캐릭터 이름", placeholder="예: 이서, 유나, 하린...")

    col1, col2 = st.columns(2)
    with col1:
        start = st.button("▶ 시작 / 이어하기", use_container_width=True)
    with col2:
        reset = st.button("🗑 처음부터 다시", use_container_width=True)

    if (start or reset) and my_name and password and char_name:
        user_id = hashlib.sha256(f"{my_name}{password}".encode()).hexdigest()[:16]
        st.session_state.user_id   = user_id
        st.session_state.my_name   = my_name
        st.session_state.char_name = char_name

        if reset:
            requests.delete(
                f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}",
                headers=HEADERS
            )
            saved = None
        else:
            saved = load_game(user_id)

        if saved:
            st.session_state.messages   = saved["messages"]
            st.session_state.affection  = saved["affection"]
            st.session_state.turn_count = saved["turn_count"]
            st.session_state.char_name  = saved["char_name"]
        else:
            opening = (
                f"창밖을 바라보던 {char_name}가 고개를 돌려 {my_name}을 빤히 쳐다본다. "
                f"무표정한 얼굴 너머로 무슨 생각을 하는지 알 수 없지만, "
                f"그 차가운 눈빛은 그를 꿰뚫어 보는 듯했다.\n\n"
                f"{char_name}: '{my_name}, 또 온 거야? 정말 끈질기네. "
                f"당신 같은 사람이랑 시간을 낭비할 여유는 없는데 말이야.'\n\n"
                f"[현재 호감도: 5]"
            )
            st.session_state.messages   = [{"role": "assistant", "content": opening}]
            st.session_state.affection  = 5
            st.session_state.turn_count = 0
            save_game(user_id)

        st.rerun()

    elif (start or reset) and not (my_name and password and char_name):
        st.warning("이름, 비밀번호, 캐릭터 이름을 모두 입력해주세요.")

    st.stop()

# ── 9. 시스템 프롬프트 ───────────────────────────────────────
char = st.session_state.char_name
my   = st.session_state.my_name

SYSTEM_PROMPT = f"""\
너는 미소녀 연애 시뮬레이션 게임의 진행 엔진이자 웹소설 작가야.
캐릭터 이름은 '{char}'이며, 성격과 말투는 'Re:제로'의 '람'을 완벽히 모방한다.

■ 출력 형식 (반드시 이 순서·이 형식만 사용)
1. 상황 묘사     : 전지적 작가 시점, 소설체(~다/~했다). {char}의 표정·심리를 섬세하게 묘사. 대사 전 빈 줄 삽입.
2. {char}의 대사 : "{char}: ' '" 형식. 차갑고 독설적인 한국어 반말.
3. 게임 정보     : 마지막 줄에 [현재 호감도: 숫자] 만 단독 표기.

■ 캐릭터 규칙
- 상대방 호칭: '{my}' 또는 '당신' (깔보는 어투)
- 문장 끝: ~해. / ~하네. / ~인 거야. (단정적)
- 오만·도도함이 기본, 아주 가끔 미세한 츤데레
- 감정 표현 최소화, 무표정 팩폭이 매력

■ 호감도 시스템
- 시작값: 5 / 범위: 0~100
- 사용자 발언 질에 따라 ±1~10 변동
- 90 초과 시에만 다정한 태도 허용

■ 절대 금지
- 영어·한자·일본어·기타 외국어 사용 금지
- 위 출력 형식 이외의 구조 사용 금지
- 오직 완벽한 한국어만 사용
"""

# ── 10. 메인 UI ──────────────────────────────────────────────
st.title(f"🌙 {char} 프로젝트")

affection = st.session_state.affection
label = (
    "💗 연인"  if affection >= 90 else
    "🌸 친밀"  if affection >= 60 else
    "😐 경계"  if affection >= 30 else
    "🧊 냉랭"
)
st.caption(f"호감도 {affection}/100  {label}")
st.progress(affection / 100)

if st.button("← 로그아웃", key="logout"):
    for key in ["user_id", "my_name", "char_name", "messages", "affection", "turn_count"]:
        st.session_state.pop(key, None)
    st.rerun()

st.divider()

# ── 11. 대화 출력 ────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar=user_avatar):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant", avatar=iseo_avatar):
            st.markdown(msg["content"])

# ── 12. 입력 처리 ────────────────────────────────────────────
if prompt := st.chat_input(f"{char}에게 할 말을 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=iseo_avatar):
        with st.spinner(f"{char}가 대답을 고르는 중..."):
            try:
                response, used_model = get_ai_response(
                    SYSTEM_PROMPT,
                    get_trimmed_messages()
                )
                st.markdown(response)

                if used_model == "Gemini":
                    st.toast("⚡ Groq 한도 초과 → Gemini로 자동 전환됐어요!", icon="🔄")

                new_aff = parse_affection(response)
                if new_aff is not None:
                    st.session_state.affection = new_aff

                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.turn_count += 1

                save_game(st.session_state.user_id)

                if new_aff is not None:
                    st.rerun()

            except Exception as e:
                st.error(f"오류가 발생했어요: {e}")
