import streamlit as st
from groq import Groq
import google.generativeai as genai
import os
import re
import hashlib
import requests
import json
import random

# ── 1. 페이지 설정 ───────────────────────────────────────────
st.set_page_config(page_title="당신의 이야기", page_icon="📖", layout="wide")

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

# ── 3. 캐릭터 랜덤 생성 풀 ──────────────────────────────────
CHAR_NAME_POOL = {
    "남자": ["차도진","서하준","윤재혁","이강호","박시온",
             "최도현","김지호","오세준","정우혁","남건우",
             "류시현","손태양","백준서","한도윤","임서진"],
    "여자": ["이하늘","김서아","박채원","정유나","한소희",
             "오지수","윤하린","최아라","서민지","강다은"],
}

CHAR_ROLES = [
    {"role":"남자 주인공",      "emoji":"🖤","color":"#7EB8D4","gender":"남자"},
    {"role":"서브 남자 주인공", "emoji":"☀️","color":"#F5C842","gender":"남자"},
    {"role":"갈등 유발자",      "emoji":"🌹","color":"#E8837A","gender":"여자"},
    {"role":"절친",             "emoji":"🍑","color":"#F4A261","gender":"여자"},
    {"role":"조력자",           "emoji":"🍵","color":"#80C9A0","gender":"남자"},
]

PERSONALITY_POOL = [
    ("냉철한 완벽주의자. 감정이 격해지면 특유의 습관이 나온다.","단답형, 간결함."),
    ("세련된 외면 뒤에 욕망을 숨긴 라이벌. 우아하게 독설을 날린다.","우아하지만 뼈 있는 말투."),
    ("조용하지만 내면에 강렬한 감정을 숨긴 인물.","말이 적고 짧게 끊어 말함."),
    ("겉으론 쌀쌀맞지만 뒤에서 몰래 챙겨주는 츤데레.","투덜거리면서도 상대방의 안부를 묻는 말투."),
    ("자존감 높은 인플루언서 타입. 가끔 허당미가 있음.","텐션 높고 감탄사가 많은 말투."),
    ("차분하고 어른스러운 연상 스타일. 속을 알 수 없는 미소.","나긋나긋하고 여유 있는 문장."),
    ("좋아하는 마음을 못 숨기는 순정파.","좋고 싫음이 분명하며 감정에 솔직한 말투."),
    ("날카로운 첫인상과 달리 소심하고 배려심 많은 내향인.","말끝을 흐리거나 망설임이 느껴지는 말투."),
    ("승부욕이 강하고 직진하는 야생마 스타일.","강한 어조와 확신에 찬 표현."),
    ("비밀스러운 과거를 가진 미스터리한 인물. 항상 웃지만 눈은 웃지 않는다.","속내를 알 수 없는 은유적인 표현."),
    ("어떤 상황에서도 장난을 치는 능글남 스타일.","끝을 늘이는 나른한 말투와 농담."),
    ("규칙을 어기는 것을 싫어하지만 사랑에는 서투른 원칙주의자.","딱딱하고 직설적인 말투."),
    ("일 처리만큼은 확실한 무기력 천재형.","말수가 적고 귀찮음이 묻어나는 어투."),
    ("불의를 보면 참지 못하는 열혈파.","힘 있는 어조와 에너지가 느껴지는 말투."),
    ("자기 세계에 빠져 사는 4차원 예술가 기질.","맥락에서 벗어난 엉뚱하고 독특한 비유."),
]

def generate_characters():
    characters = {}
    selected_personalities = random.sample(PERSONALITY_POOL, len(CHAR_ROLES))
    for i, role_info in enumerate(CHAR_ROLES):
        gender    = role_info["gender"]
        available = [n for n in CHAR_NAME_POOL[gender] if n not in characters]
        name      = random.choice(available)
        p         = selected_personalities[i]
        characters[name] = {
            "role":        role_info["role"],
            "emoji":       role_info["emoji"],
            "color":       role_info["color"],
            "personality": p[0],
            "tone_hint":   p[1],
        }
    return characters

# ── 4. 장르 / 수위 / 관계 설정 ──────────────────────────────
GENRES = {
    "🏫 학원 로맨스": "명문고. 남주=재벌가 서늘한 학생회장, 서브남주=짝사랑하는 순정파, 갈등유발자=약혼녀 후보, 조력자=전교1등. '나'=장학생.",
    "🌆 오피스·현대": "비즈니스계. 남주=워커홀릭 본부장, 서브남주=라이벌사 팀장, 갈등유발자=성과 가로채는 상사, 조력자=눈치 백단 대리. '나'=신입사원.",
    "🎨 캠퍼스·청춘": "미대/공대. 남주=과탑 얼굴천재 선배, 서브남주=장난기 많은 남사친, 갈등유발자=캠퍼스 여신, 조력자=술자리 대장 동기. '나'=새내기.",
    "⚽ 스포츠":      "프로 구단. 남주=에이스/감독, 서브남주=팀 주치의, 갈등유발자=라이벌 팀 관계자. '나'=구단 관계자.",
    "🍰 힐링·일상":   "감성 카페/공방. 남주=번아웃 천재 작가, 서브남주=햇살 같은 꽃집 주인, 갈등유발자=가십 기자, 조력자=편의점 사장님. '나'=초보 사장.",
}

RATINGS = {
    "🌸 순애":        "손잡기·포옹 수준. 설렘과 감정 묘사 중심.",
    "💫 로맨스":      "적당한 스킨십 허용. 키스 포함 가능.",
    "🥂 성인 로맨스": "농밀한 분위기와 욕망 묘사. 절제된 표현 안에서 최대 긴장감.",
}

RELATIONS = {
    "🤝 처음 만나는 사이": {"start_affection":5,  "desc":"완전한 초면."},
    "📖 인연이 있던 사이": {"start_affection":20, "desc":"과거에 스친 적 있는 사이."},
    "💫 재회하는 사이":    {"start_affection":35, "desc":"한때 가까웠다가 오랜만에 다시 만난 사이."},
}

PERSONALITY_OPTIONS = [
    "당차고 독립적","소심하지만 따뜻함","4차원 엉뚱함",
    "현실적이고 냉정함","감성적이고 예민함","유머감각 넘침",
    "호기심 많고 활발함","조용하지만 관찰력 뛰어남"
]

# ── 5. Supabase ───────────────────────────────────────────────
def save_game(user_id: str):
    data = {
        "user_id":        user_id,
        "my_name":        st.session_state.my_name,
        "my_gender":      st.session_state.my_gender,
        "my_personality": json.dumps(st.session_state.my_personality, ensure_ascii=False),
        "my_intro":       st.session_state.my_intro,
        "genre":          st.session_state.genre,
        "rating":         st.session_state.get("rating","💫 로맨스"),
        "relation":       st.session_state.get("relation","🤝 처음 만나는 사이"),
        "messages":       st.session_state.messages,
        "affection":      st.session_state.affection,
        "turn_count":     st.session_state.turn_count,
        "char_name":      json.dumps(st.session_state.characters, ensure_ascii=False),
        "user_notes":     st.session_state.get("user_notes",""),
    }
    requests.post(f"{SUPABASE_URL}/rest/v1/save_data", headers=HEADERS, json=data)

def load_game(user_id: str):
    res  = requests.get(f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}", headers=HEADERS)
    data = res.json()
    return data[0] if data else None

# ── 6. 외국어 필터 ───────────────────────────────────────────
WHITELIST = {
    "CEO","CFO","CTO","COO","HR","PR","IR","PM","PO",
    "TV","PC","SNS","IT","AI","VIP","MC","DJ",
    "BGM","OST","CF","PPT","PDF","USB","WiFi","GPS",
    "MBTI","MZ","OTT","DM","ID","OT","MT","CC","TF",
    "AS","VS","QA","CS","NDA","OJT","MOU","FYI","ASAP",
    "KPI","OKR","ROI","B2B","B2C","GPA","ASMR","TMI",
    "LOL","RPG","FPS","MVP","GG","SaaS","ERP","CRM",
}

def filter_foreign(text: str) -> str:
    placeholders = []
    def preserve(m):
        placeholders.append(m.group(0))
        return f"__PRESERVE_{len(placeholders)-1}__"
    text = re.sub(r'<[^>]+>|```[\s\S]*?```|`[^`]*`', preserve, text)
    for word in WHITELIST:
        text = re.sub(rf'\b{re.escape(word)}\b', preserve, text, flags=re.IGNORECASE)
    text = re.sub(r'[A-Za-z]{2,}', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    for i, p in enumerate(placeholders):
        text = text.replace(f"__PRESERVE_{i}__", p)
    return text

# ── 7. 호감도 파싱 (변화량 방식, ±5 제한) ───────────────────
def parse_affection(text: str, current: dict) -> dict:
    updated    = current.copy()
    characters = st.session_state.characters
    for char in characters:
        match = re.search(rf"\[{re.escape(char)}\s*([+-]\d+)\]", text)
        if match:
            delta         = max(-5, min(5, int(match.group(1))))
            updated[char] = max(0, min(100, current.get(char, 5) + delta))
    return updated

# ── 8. 대화 요약 (토큰 최적화 핵심) ─────────────────────────
SUMMARY_THRESHOLD = 8   # 8턴 초과 시 요약
KEEP_RECENT       = 4   # 요약 후 최근 4턴은 원본 유지

def summarize_old_messages(messages: list) -> list:
    """오래된 대화를 AI가 요약해서 토큰 절약"""
    if len(messages) <= SUMMARY_THRESHOLD:
        return messages

    to_summarize = messages[:-KEEP_RECENT]
    keep_recent  = messages[-KEEP_RECENT:]

    # 요약할 내용 텍스트로 변환
    summary_input = ""
    for msg in to_summarize:
        role    = "독자" if msg["role"] == "user" else "이야기"
        content = re.sub(r'<!--.*?-->', '', msg["content"], flags=re.DOTALL).strip()
        summary_input += f"[{role}]: {content[:300]}\n"

    try:
        summary_prompt = (
            "다음은 웹소설 대화 기록이야. "
            "핵심 사건과 감정 변화만 3~5문장으로 요약해줘. "
            "한국어로만 작성하고, 불필요한 설명 없이 간결하게:\n\n"
            + summary_input
        )
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",   # 요약엔 8B 모델 사용 (토큰 절약)
            messages=[{"role":"user","content":summary_prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        summary_text = completion.choices[0].message.content.strip()
        summary_msg  = {
            "role":    "assistant",
            "content": f"[이전 이야기 요약]\n{summary_text}"
        }
        return [summary_msg] + keep_recent
    except Exception:
        # 요약 실패 시 그냥 최근 턴만 유지
        return keep_recent

# ── 9. AI 응답 (Groq 70B → Gemini 폴백) ─────────────────────
def get_ai_response(system_prompt: str, api_messages: list) -> tuple[str, str]:
    # 요약 적용
    optimized = summarize_old_messages(api_messages)
    full_msgs  = [{"role":"system","content":system_prompt}] + optimized

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=full_msgs,
            temperature=0.9,
            top_p=0.9,
            max_tokens=700,          # 900 → 700 (품질 유지하면서 절약)
        )
        return completion.choices[0].message.content, "Groq"
    except Exception as e:
        if "429" in str(e) or "rate_limit" in str(e).lower():
            try:
                gemini_history = []
                for msg in optimized[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({"role":role,"parts":[msg["content"]]})
                last_msg     = optimized[-1]["content"]
                gemini_model = genai.GenerativeModel(
                    "gemini-2.5-flash",
                    system_instruction=system_prompt
                )
                chat     = gemini_model.start_chat(history=gemini_history)
                response = chat.send_message(last_msg)
                return response.text, "Gemini"
            except Exception as gemini_err:
                raise Exception(f"Groq·Gemini 모두 실패: {gemini_err}")
        else:
            raise e

# ── 10. 텍스트 정제 & 색상 적용 ──────────────────────────────
def clean_text(text: str) -> str:
    return re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL).strip()

def colorize_dialogue(text: str) -> str:
    characters = st.session_state.get("characters", {})
    
    # 1단계: 이름: "대사" 패턴을 정확히 찾아 색상만 부드럽게 입힙니다. (강제 줄바꿈 제거)
    for name, info in characters.items():
        color = info["color"]
        # 문장 중간에 자연스럽게 섞이도록 앞뒤 <br>을 제거하고 색상(span)만 씌웁니다.
        text = re.sub(rf'({re.escape(name)}:\s*["\'](.*?)["\'])',
                      rf'<span style="color:{color}; font-weight:600">\1</span>', text)
                      
    # 2단계: AI가 문단 구분을 위해 넣은 실제 줄바꿈(\n)을 Streamlit용 HTML 태그(<br>)로 자연스럽게 치환합니다.
    text = text.replace("\n", "<br>")
    
    # 3단계: 불필요하게 뭉친 줄바꿈 정돈
    text = re.sub(r'(<br>\s*){3,}', '<br><br>', text)
    
    return text
	
def render_message(text: str):
    cleaned  = clean_text(text)
    filtered = filter_foreign(cleaned)
    colored  = colorize_dialogue(filtered)
    st.markdown(colored, unsafe_allow_html=True)

# ── 11. 시스템 프롬프트 (압축 최적화) ───────────────────────
def build_system_prompt() -> str:
    my            = st.session_state.my_name
    gender        = st.session_state.my_gender
    traits        = ", ".join(st.session_state.my_personality)
    intro         = st.session_state.my_intro or "없음"
    genre         = st.session_state.genre
    rating        = st.session_state.get("rating","💫 로맨스")
    relation      = st.session_state.get("relation","🤝 처음 만나는 사이")
    world         = GENRES.get(genre,"")
    rating_guide  = RATINGS.get(rating,"")
    relation_desc = RELATIONS.get(relation,{}).get("desc","")
    aff           = st.session_state.affection
    characters    = st.session_state.characters
    user_notes    = st.session_state.get("user_notes","")

    # 캐릭터 설명 (압축)
    char_desc = ""
    for name, info in characters.items():
        a = aff.get(name, 5)
        if a >= 90:
            tone = "다정하고 솔직한 반말. 애칭 가능."
        elif a >= 60:
            tone = f"편한 친구 반말. 이름 애칭 시작. 장난기 섞임."
        elif a >= 30:
            tone = f"친근해지는 반말. 살짝 거리감. {info.get('tone_hint','')}"
        else:
            tone = f"거리감 있는 반말. 단답형. {info.get('tone_hint','')} 고어체 금지."
        char_desc += f"- {name}({info['role']}): {info['personality']} 말투:{tone}\n"

    user_note_section = f"\n[유저 메모 - 반드시 반영]\n{user_notes}\n" if user_notes.strip() else ""

    return f"""한국 웹소설 작가. 독자 참여형 인터랙티브 웹소설.

[세계관] {genre}: {world}
[주인공] 이름:{my} 성별:{gender}(혼동금지) 성격:{traits} 소개:{intro}
[관계] {relation}: {relation_desc}
[수위] {rating}: {rating_guide}

[등장인물]
{char_desc}{user_note_section}
[말투 절대규칙]
- 모든 등장인물은 반드시 반말 사용. 예외없음.
- 금지: ~씨,~군,~입니다,~죠,~이에요,~하세요
- 허용: ~야,~아,~해,~어,~잖아,~거든

[출력형식]
1. [장소-시간대]
2. 소설체 서술(메타태그 금지)
3. 대사 및 행동구조: 
-이름: "대사" (이름)의 행동/표정/몸짓 묘사 서술문 구조를 지켜줘.
-문단 내에서 대사가 이어질 때는 반드시 지문 뒤에 `이름: "대사"` 태그를 다시 붙여서 대사임을 명시할 것.
-대사가 끝난 후 다음 줄에 해당 인물의 표정, 행동, 몸짓을 소설체로 묘사해야 하며, 다시 그 인물이 말을 이어갈 때도 **반드시** `이름: "대사"` 형태로 이름을 다시 명시해야 함.
	잘못된 예: 이름: "대사1" -> (행동 묘사) -> "대사2" (이름 누락 금지)
	올바른 예: 이름: "대사1" -> (행동 묘사) -> 이름: "대사2" (매 대사마다 이름 필수)
	**주의:지문(행동 묘사)을 쓸 때 `(인물이름)이~` 처럼 괄호를 절대 사용하지 말 것.**
- 다른 인물로 전환되거나 문단이 바뀔 때는 반드시 두 번 줄바꿈(\\n\\n)을 해서 완전히 분리할 것.
4. 1~3명만 등장
5. 마지막줄: <!-- [이름 +N] [이름 -N] --> (±5 이내, 본문노출금지)

[문장품질]
- 같은 단어 3회이상 반복금지
- '미소/시선을 돌렸다/바라보았다' 최대 1회
- 인물이름 첫등장후 대명사(그,그녀)로 대체
	**인물의 행동을 묘사할 때는 가급적 '그', '그녀' 같은 대명사나 조사(예: '건우는', '도윤은')를 사용하여 문학적인 웹소설 문체로 서술할 것. (예: '남건우: "대사" 그는 한숨처럼~')**
- 한 문단 최대 3문장

[언어규칙 - 최우선]
- 100% 한국어만 사용. 외국어 한글자도 금지.
- 영어단어→반드시 한국어로 변환. (narrow→가늘어진, smile→미소)
- 화이트리스트 약어(CEO,SNS등)만 예외허용.
- 위반시 출력실패로 간주.

[스토리 전개 규칙 - 필수]
- 단순히 인물들의 대답만으로 상황을 끝내지 말 것.
- 턴이 끝날 때, 독자(주인공)가 반응하거나 선택해야만 하는 '새로운 상황', '질문', '행동 유발 요인(Hook)'을 반드시 제시할 것.
- 예: 인물이 말을 건네며 다가오거나, 돌발 상황이 발생하거나, 갈등의 실마리가 잡히는 등 독자가 다음 행동을 입력할 수밖에 없는 상태에서 출력을 멈출 것.
- 전개가 너무 정체되지 않도록, 매 턴마다 시간대/장소의 미세한 변화나 인물들 간의 미묘한 기류 변화를 포함할 것.
- 다만, 전개가 너무 급격하게 흘러가지 않도록 페이스 조절을 반드시 할 것.

[호감도 말투변화]
0~29: 거리감 반말 | 30~59: 친근해지는 반말 | 60~89: 편한 반말 | 90~: 다정한 반말
/호감도 입력시에만 전체 호감도 출력"""

# ════════════════════════════════════════════════════════════
# UI 시작
# ════════════════════════════════════════════════════════════

# ── 12. 세션 초기화 ──────────────────────────────────────────
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
    st.session_state.affection      = {}
    st.session_state.turn_count     = 0
    st.session_state.characters     = {}
    st.session_state.user_notes     = ""

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
            requests.delete(f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}", headers=HEADERS)
            st.session_state.step = "setup"
        else:
            saved = load_game(user_id)
            if saved:
                st.session_state.my_name        = saved["my_name"]
                st.session_state.my_gender      = saved.get("my_gender","여성")
                st.session_state.my_personality = json.loads(saved["my_personality"])
                st.session_state.my_intro       = saved.get("my_intro","")
                st.session_state.genre          = saved.get("genre","")
                st.session_state.rating         = saved.get("rating","💫 로맨스")
                st.session_state.relation       = saved.get("relation","🤝 처음 만나는 사이")
                st.session_state.messages       = saved["messages"]
                st.session_state.affection      = saved["affection"]
                st.session_state.turn_count     = saved["turn_count"]
                st.session_state.user_notes     = saved.get("user_notes","")
                raw_chars = saved.get("char_name","{}")
                st.session_state.characters     = json.loads(raw_chars) if isinstance(raw_chars, str) else raw_chars
                st.session_state.step           = "story"
            else:
                st.session_state.step = "setup"
        st.rerun()
    elif (start or reset) and not (name and password):
        st.warning("이름과 비밀번호를 입력해주세요.")

# ── 14. STEP 2: 주인공 설정 ──────────────────────────────────
elif st.session_state.step == "setup":
    st.title("✍️ 주인공 설정")
    st.divider()
    my_name   = st.text_input("주인공 이름", placeholder="예: 이하늘")
    my_gender = st.radio("성별", ["여성","남성"], horizontal=True)
    st.markdown("**성격 키워드** (최대 3개)")
    selected = []
    cols = st.columns(2)
    for i, opt in enumerate(PERSONALITY_OPTIONS):
        with cols[i % 2]:
            if st.checkbox(opt, key=f"trait_{i}"):
                selected.append(opt)
    my_intro = st.text_input("한 줄 소개 (선택)", placeholder="예: 평범한 척하지만 반전매력 있음")
    if len(selected) > 3:
        st.warning("최대 3개까지만 선택할 수 있어요.")
    if st.button("다음 →", use_container_width=True):
        if not my_name:
            st.warning("주인공 이름을 입력해주세요.")
        elif len(selected) == 0:
            st.warning("성격 키워드를 최소 1개 선택해주세요.")
        elif len(selected) > 3:
            st.warning("최대 3개까지만 선택할 수 있어요.")
        else:
            st.session_state.my_name        = my_name
            st.session_state.my_gender      = my_gender
            st.session_state.my_personality = selected
            st.session_state.my_intro       = my_intro
            st.session_state.characters     = generate_characters()
            st.session_state.step           = "genre"
            st.rerun()

# ── 15. STEP 3: 장르 선택 ────────────────────────────────────
elif st.session_state.step == "genre":
    st.title("🃏 장르 선택")
    st.divider()
    cols = st.columns(2)
    for i, (genre_name, world_desc) in enumerate(GENRES.items()):
        with cols[i % 2]:
            st.markdown(f"### {genre_name}")
            st.caption(world_desc[:45] + "...")
            if st.button("선택", key=f"genre_{i}", use_container_width=True):
                st.session_state.genre = genre_name
                st.session_state.step  = "rating"
                st.rerun()

# ── 16. STEP 4: 수위 선택 ────────────────────────────────────
elif st.session_state.step == "rating":
    st.title("✨ 수위 선택")
    st.divider()
    for rating_name, rating_desc in RATINGS.items():
        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown(f"**{rating_name}**")
            st.caption(rating_desc)
        with col2:
            if st.button("선택", key=f"rating_{rating_name}", use_container_width=True):
                st.session_state.rating = rating_name
                st.session_state.step   = "relation"
                st.rerun()
        st.divider()

# ── 17. STEP 5: 관계 프리셋 ──────────────────────────────────
elif st.session_state.step == "relation":
    st.title("💫 관계 설정")
    st.divider()
    for rel_name, rel_info in RELATIONS.items():
        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown(f"**{rel_name}**")
            st.caption(rel_info["desc"])
        with col2:
            if st.button("선택", key=f"rel_{rel_name}", use_container_width=True):
                st.session_state.relation  = rel_name
                start_aff = rel_info["start_affection"]
                st.session_state.affection = {name: start_aff for name in st.session_state.characters}
                st.session_state.step      = "intro"
                st.rerun()
        st.divider()

# ── 18. STEP 6: 캐릭터 소개 (카드 UI + 이미지) ───────────────
elif st.session_state.step == "intro":
    st.title("📖 등장인물")
    st.caption(f"{st.session_state.genre}  |  {st.session_state.rating}  |  {st.session_state.relation}")
    st.divider()

    for name, info in st.session_state.characters.items():
        # st.expander를 적용하여 클릭 시에만 정보 노출
        with st.expander(f"{info['emoji']} {name} ({info['role']})"):
            st.markdown(f"**성격:** <span style='color:{info['color']}'>{info['personality']}</span>", unsafe_allow_html=True)
    
    st.divider()

    characters = st.session_state.characters
    cols = st.columns(3)
    for i, (name, info) in enumerate(characters.items()):
        with cols[i % 3]:
            # 이미지 경로 탐색
            img_path = None
            for ext in [".JPG", ".jpg", ".PNG", ".png", ".jpeg"]:
                p = f"images/{name}{ext}"
                if os.path.exists(p):
                    img_path = p
                    break

            with st.container(border=True):
                if img_path:
                    st.image(img_path, use_container_width=True)
                else:
                    st.markdown(
                        f"<div style='text-align:center;font-size:56px;"
                        f"padding:32px 0;background:var(--color-background-secondary);"
                        f"border-radius:8px'>{info['emoji']}</div>",
                        unsafe_allow_html=True
                    )
                st.markdown(
                    f"<span style='font-size:11px;font-weight:500;padding:3px 8px;"
                    f"border-radius:99px;background:{info['color']}22;color:{info['color']}'>"
                    f"{info['role']}</span>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<p style='font-size:15px;font-weight:500;margin:6px 0 4px'>"
                    f"<span style='color:{info['color']}'>■</span> {name}</p>",
                    unsafe_allow_html=True
                )
                st.caption(info["personality"])

    st.divider()
    if st.button("📖 이야기 시작하기", use_container_width=True):
        system_prompt = build_system_prompt()
        relation      = st.session_state.relation
        if relation == "🤝 처음 만나는 사이":
            opening_req = "이야기 첫 장면을 웹소설 도입부처럼 감각적으로 써줘. 처음 만나는 장면."
        elif relation == "📖 인연이 있던 사이":
            opening_req = "2~3문장 과거 인연 프롤로그 후 현재 장면으로 이어줘."
        else:
            opening_req = "3~4문장 과거 서사 프롤로그 후 재회 장면으로 이어줘."
        with st.spinner("첫 번째 장면을 쓰는 중..."):
            try:
                response, _ = get_ai_response(system_prompt, [{"role":"user","content":opening_req}])
                st.session_state.messages   = [{"role":"assistant","content":response}]
                st.session_state.turn_count = 0
                save_game(st.session_state.user_id)
                st.session_state.step = "story"
                st.rerun()
            except Exception as e:
                st.error(f"오류가 발생했어요: {e}")

# ── 19. STEP 7: 메인 스토리 ──────────────────────────────────
elif st.session_state.step == "story":
    characters  = st.session_state.characters
    genre_emoji = st.session_state.genre.split()[0]

    with st.sidebar:
        st.markdown("## 📋 정보")
        st.caption(
            f"**{st.session_state.my_name}** ({st.session_state.my_gender})\n\n"
            f"{st.session_state.genre}\n\n"
            f"{st.session_state.rating}  |  {st.session_state.relation}"
        )
        # 토큰 사용량 표시
        turn = st.session_state.turn_count
        estimated = turn * 1200
        st.caption(f"📊 대화 {turn}턴 · 예상 {estimated:,} 토큰 사용")
        st.divider()

        st.markdown("### 🎨 등장인물")
        for name, info in characters.items():
            with st.expander(f"■ {name} ({info['role']})"):
                # 이미지 탐색
                img_path = None
                for ext in [".JPG", ".jpg", ".PNG", ".png", ".jpeg"]:
                    p = f"images/{name}{ext}"
                    if os.path.exists(p):
                        img_path = p
                        break

                if img_path:
                    st.image(img_path, use_container_width=True)
                else:
                    st.markdown(
                        f"<div style='text-align:center;font-size:40px;"
                        f"padding:16px;background:var(--color-background-secondary);"
                        f"border-radius:8px'>{info['emoji']}</div>",
                        unsafe_allow_html=True
                    )
            
                st.markdown(f"<span style='color:{info['color']}'>{info['personality']}</span>", unsafe_allow_html=True)
        st.divider()

        st.markdown("### 📝 유저 노트")
        st.caption("이벤트, 요청사항을 적어주세요. 저장 후 반영돼요.")
        user_notes_input = st.text_area(
            label="노트",
            value=st.session_state.user_notes,
            height=180,
            placeholder="예시:\n- 도진이 오늘부터 반말 사용\n- 다음 장면에 절친 등장",
            label_visibility="collapsed"
        )
        if st.button("💾 노트 저장", use_container_width=True):
            st.session_state.user_notes = user_notes_input
            save_game(st.session_state.user_id)
            st.toast("저장됐어요!", icon="📝")
            st.rerun()
        st.divider()
        if st.button("← 로그아웃", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.title(f"{genre_emoji} 당신의 이야기")
    st.caption(
        f"**{st.session_state.my_name}** ({st.session_state.my_gender})  |  "
        f"{' · '.join(st.session_state.my_personality)}"
    )
    st.divider()

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="📖"):
                render_message(msg["content"])

    if prompt := st.chat_input("이야기를 이어가세요... (/호감도)"):
        if prompt.strip() == "/호감도":
            aff    = st.session_state.affection
            result = "### 📊 현재 호감도\n\n"
            for char, val in aff.items():
                if char not in characters:
                    continue
                info  = characters[char]
                bar   = "█" * (val // 10) + "░" * (10 - val // 10)
                label = (
                    "💗 연인 단계"   if val >= 90 else
                    "🌸 친밀한 사이" if val >= 60 else
                    "😐 평범한 관계" if val >= 30 else
                    "🧊 차가운 사이"
                )
                result += (
                    f"<span style='color:{info['color']}'>"
                    f"**{info['emoji']} {char}**</span> ({info['role']})\n"
                    f"`{bar}` {val}/100  {label}\n\n"
                )
            with st.chat_message("assistant", avatar="📊"):
                st.markdown(result, unsafe_allow_html=True)
        else:
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="📖"):
                with st.spinner("이야기를 쓰는 중..."):
                    try:
                        system_prompt = build_system_prompt()
                        response, used_model = get_ai_response(
                            system_prompt,
                            st.session_state.messages
                        )
                        render_message(response)
                        if used_model == "Gemini":
                            st.toast("⚡ Gemini로 자동 전환됐어요!", icon="🔄")
                        new_aff = parse_affection(response, st.session_state.affection)
                        st.session_state.affection = new_aff
                        st.session_state.messages.append({"role":"assistant","content":response})
                        st.session_state.turn_count += 1
                        save_game(st.session_state.user_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류가 발생했어요: {e}")
