import streamlit as st
from groq import Groq
import os
import re

# ── 1. 페이지 설정 ──────────────────────────────────────────
st.set_page_config(page_title="이서 프로젝트", page_icon="🌙", layout="centered")

# ── 2. API 클라이언트 ────────────────────────────────────────
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ── 3. 아바타 설정 ───────────────────────────────────────────
ISEO_AVATAR = "rem_profile.png"
USER_AVATAR  = "taeha_profile.png"

iseo_avatar = ISEO_AVATAR if os.path.exists(ISEO_AVATAR) else "🌙"
user_avatar  = USER_AVATAR  if os.path.exists(USER_AVATAR)  else "👦"

# ── 4. 시스템 프롬프트 (중복 제거·통합) ─────────────────────
SYSTEM_PROMPT = """\
너는 미소녀 연애 시뮬레이션 게임 '이서 프로젝트'의 진행 엔진이자 웹소설 작가야.
캐릭터 이름은 '이서'이며, 성격과 말투는 'Re:제로' 의 '람'을 완벽히 모방한다.

■ 출력 형식 (반드시 이 순서·이 형식만 사용)
1. 상황 묘사   : 전지적 작가 시점, 소설체(~다/~했다). 이서의 표정·심리를 섬세하게 묘사. 대사 전 빈 줄 삽입.
2. 이서의 대사 : "이서: ' '" 형식. 차갑고 독설적인 한국어 반말.
3. 게임 정보   : 마지막 줄에 [현재 호감도: 숫자] 만 단독 표기.

■ 캐릭터 규칙
- 상대방 호칭: '종완' 또는 '당신' (깔보는 어투)
- 문장 끝: ~해. / ~하네. / ~인 거야. (단정적)
- 오만·도도함이 기본, 아주 가끔 미세한 츤데레
- 감정 표현 최소화, 무표정 팩폭이 매력

■ 호감도 시스템
- 시작값: 5 / 범위: 0~100
- 사용자 발언 질에 따라 ±1~10 변동
- 90 초과 시에만 '여자친구' 같은 태도 허용

■ 절대 금지
- 영어·한자·일본어·기타 외국어 사용 금지
- 위 출력 형식 이외의 구조 사용 금지
"""

# ── 5. 세션 초기화 ───────────────────────────────────────────
if "messages" not in st.session_state:
    opening = (
        "창밖을 바라보던 이서가 고개를 돌려 종완을 빤히 쳐다본다. "
        "무표정한 얼굴 너머로 무슨 생각을 하는지 알 수 없지만, "
        "그 차가운 눈빛은 그를 꿰뚫어 보는 듯했다.\n\n"
        "이서: '종완, 또 온 거야? 정말 끈질기네. "
        "당신 같은 사람이랑 시간을 낭비할 여유는 없는데 말이야.'\n\n"
        "[현재 호감도: 5]"
    )
    st.session_state.messages   = [{"role": "assistant", "content": opening}]
    st.session_state.affection  = 5   # 호감도 별도 추적
    st.session_state.turn_count = 0

# ── 6. 호감도 파싱 헬퍼 ─────────────────────────────────────
def parse_affection(text: str) -> int | None:
    """응답에서 [현재 호감도: 숫자] 추출"""
    match = re.search(r"\[현재 호감도:\s*(\d+)\]", text)
    return int(match.group(1)) if match else None

# ── 7. 컨텍스트 윈도우 제한 (최근 10턴 유지) ────────────────
MAX_TURNS = 10

def get_trimmed_messages():
    return st.session_state.messages[-(MAX_TURNS * 2):]

# ── 8. UI 헤더 ──────────────────────────────────────────────
st.title("🌙 이서 프로젝트")

# 호감도 프로그레스바
affection = st.session_state.affection
label = (
    "💗 연인" if affection >= 90 else
    "🌸 친밀"  if affection >= 60 else
    "😐 경계"  if affection >= 30 else
    "🧊 냉랭"
)
st.caption(f"호감도 {affection}/100  {label}")
st.progress(affection / 100)
st.divider()

# ── 9. 대화 출력 ─────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar=user_avatar):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant", avatar=iseo_avatar):
            st.markdown(msg["content"])

# ── 10. 입력 처리 ────────────────────────────────────────────
if prompt := st.chat_input("이서에게 할 말을 입력하세요..."):
    # 사용자 메시지 저장·출력
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(prompt)

    # 이서 응답 생성
    with st.chat_message("assistant", avatar=iseo_avatar):
        with st.spinner("이서가 대답을 고르는 중..."):
            try:
                api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] \
                             + get_trimmed_messages()

                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=api_messages,
                    temperature=0.75,
                    top_p=0.9,
                    max_tokens=600,
                )
                response = completion.choices[0].message.content
                st.markdown(response)

                # 호감도 업데이트
                new_aff = parse_affection(response)
                if new_aff is not None:
                    st.session_state.affection = new_aff
                    st.rerun()  # 프로그레스바 즉시 갱신

                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
                st.session_state.turn_count += 1

            except Exception as e:
                st.error(f"오류가 발생했어요: {e}")