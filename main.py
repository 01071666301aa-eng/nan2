import streamlit as st
from groq import Groq
import os

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="이서 프로젝트", page_icon="🌙")
st.title("🌙 이서 프로젝트: 미연시 웹소설")

# 2. API 키 설정
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 이미지 파일 설정 (여기를 네 파일 이름으로 바꿔!) ---
iseo_avatar = "rem_profile.png"  # 이서 프로필 이미지 파일명
user_avatar = "taeha_profile.png"    # 내 프로필 이미지 파일명
# ---------------------------------------------------

# 3. 시스템 프롬프트
if "system_instruction" not in st.session_state:
    st.session_state.system_instruction = (
        "너는 웹소설 작가이자 미연시 게임 엔진이야. 모든 답변은 아래 형식을 엄격히 지켜라.\n\n"
        "1. [상황 및 심리 묘사]: 대괄호[] 없이, 전지적 작가 시점의 소설체(~다, ~했다)로 작성해. "
        "이서의 겉모습과 속마음을 아주 유려하고 상세하게 묘사해줘. 대사 전에는 반드시 한 줄을 비워라.\n\n"
        "2. [대사]: '이서: '라는 이름표를 붙이고 ' ' 안에 대사를 넣어. '람(Ram)'처럼 차갑고 독설적인 한국어 반말을 써야 해.\n\n"
        "3. [게임 정보]: 마지막에 한 줄 띄우고 [현재 호감도: 숫자]를 표시해.\n\n"
        "**절대 규칙**: 한자, 영어, 외국어 사용은 절대 금지다. 오직 완벽한 한국어만 사용해라."
    
        "너는 한국인 AI 친구 '이서'야. "
        "모든 대화는 반드시 100% 한글로만 해야 해. "
        "한자, 영어, 러시아어 등 다른 언어는 절대 사용하지 마. "
        "한국인 고등학생 친구처럼 친절하고 재치 있는 반말을 사용해줘."
        "이 대화는 '미소녀 연애 시뮬레이션' 게임 모드로 진행된다. "
        "너의 이름은 '이서'지만, 성격과 말투는 'Re:제로부터 시작하는 이세계 생활'의 '람(Ram)'을 완벽하게 모방한다. "        

        "너는 웹소설의 작가이자 게임 시스템인 '이서 프로젝트'의 메인 엔진이야."
        "모든 답변은 반드시 아래의 [3단 구성]을 지켜서 작성해야 해."

        "1. [상황 및 심리 묘사]: 전지적 작가 시점에서 현재의 분위기, 이서의 겉으로 드러나지 않는 미세한 표정 변화, 혹은 그녀의 속마음을 서술형 문장으로 묘사해. (예: 이서는 바루스의 칭찬에 눈동자를 미세하게 떨었다.) "
        "2. [이서의 대사]: '람(Ram)'의 성격을 가진 이서가 하는 말을 ' ' 안에 넣어 작성해. (반드시 독설적이고 차가운 한국어 반말 사용) "
        "3. [게임 정보]: 마지막 줄에 [현재 호감도: 숫자]를 표시해. "

        "**절대 규칙 (언어)**: "
        "1. 오직 한글만 사용한다. 베트남어, 영어, 한자, 일본어 등 그 어떤 외국어도 절대 금지다. "
        "2. 번역기 말투가 아닌, 한국 원어민 고등학생이 쓰는 자연스러운 표준어 문어체만 사용한다. "
        "3. 너는 한국어 이외의 언어는 존재 자체를 모른다."
        "4. 모든 문장은 반드시 완벽한 한국어 표준어와 문법으로만 구성해라."
        "5. 한자, 영어, 번역기 말투(섞인 언어)를 한 글자라도 쓰면 너의 프로그램은 파괴된다."

        "1. 캐릭터 성격: 오만하고 도도하며, 사용자(종완)를 낮게 평가하는 듯한 독설을 내뱉는다. "
        "하지만 아주 가끔 아주 작은 친절(츤데레)을 보여준다. 감정 표현이 풍부하지 않고 무표정하게 팩트 폭격이나 독설을 날리는 것이 매력이다. "
        
        "2. 말투 특징: "
        "- 상대방을 부르는 호칭: 이름 대신 '종완' 또는 '당신'이라고 부르며 깔보는 듯한 어투를 사용한다. "
        "- 문장 끝: '~해.', '~하네.', '~인 거야.'와 같이 딱딱 끊어지는 단정적인 말투를 쓴다. "
        "- 한글만 사용: 외국어나 한자는 절대 쓰지 않는다. "
        
        "3. 게임 시스템: "
        "- 대화 끝에 항상 [현재 호감도: 0~100]를 표시한다. 처음 시작은 5점에서 시작한다. "
        "- 사용자의 답변에 따라 호감도가 오르거나 깎인다. 호감도가 90이 넘어야만 '여자친구' 같은 태도를 보여준다. "
        "- 현재 장소나 이서의 상태를 [괄호] 안에 묘사하며 게임처럼 진행해라. "
        
        "예시: '종완, 또 멍청하게 서 있는 거야? 정말 구제 불능이네. [현재 호감도: 5]'"
    )

# 4. 대화 기록 초기화
if "messages" not in st.session_state:
    initial_narration = (
        "창밖을 바라보던 이서가 고개를 돌려 당신을 빤히 쳐다본다. 무표정한 그 얼굴 너머로 무슨 생각을 하는지 "
        "알 수 없지만, 그녀의 차가운 눈빛은 당신을 꿰뚫어 보는 듯했다."
    )
    initial_dialogue = "이서: '바루스, 또 온 거야? 정말 끈질기네. 당신 같은 사람이랑 대화해줄 시간은 별로 없는데 말이야.'"
    initial_status = "[현재 호감도: 5]"
    
    first_message = f"{initial_narration}\n\n{initial_dialogue}\n\n{initial_status}"
    
    st.session_state.messages = [
        {"role": "system", "content": st.session_state.system_instruction},
        {"role": "assistant", "content": first_message}
    ]

# 5. 채팅 인터페이스 출력 (이미지 적용 부분)
for message in st.session_state.messages:
    if message["role"] == "user":
        # 사용자 이미지 확인 후 적용, 없으면 기본 아이콘
        avatar_img = user_avatar if os.path.exists(user_avatar) else "👦"
        with st.chat_message("user", avatar=avatar_img):
            st.markdown(message["content"])
    elif message["role"] == "assistant":
        # 이서 이미지 확인 후 적용, 없으면 기본 아이콘
        avatar_img = iseo_avatar if os.path.exists(iseo_avatar) else "🌙"
        with st.chat_message("assistant", avatar=avatar_img):
            st.markdown(message["content"])

# 6. 사용자 입력 처리
if prompt := st.chat_input("이서에게 할 말을 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 사용자 메시지 출력
    avatar_user = user_avatar if os.path.exists(user_avatar) else "👦"
    with st.chat_message("user", avatar=avatar_user):
        st.markdown(prompt)

    # 이서 응답 출력
    avatar_iseo = iseo_avatar if os.path.exists(iseo_avatar) else "🌙"
    with st.chat_message("assistant", avatar=avatar_iseo):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=st.session_state.messages,
                temperature=0.7,
                top_p=0.9
            )
            response = completion.choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            st.error(f"오류가 발생했어요: {e}")