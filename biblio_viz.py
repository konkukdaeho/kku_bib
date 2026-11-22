import os
import pandas as pd
import altair as alt
import streamlit as st

# ------------------------------
# 1. 기본 설정과 데이터 (딕셔너리)
# ------------------------------
st.set_page_config(page_title="국가서지 2025 시각화", page_icon="📚", layout="wide")

# 이 파이썬 파일과 같은 폴더에 있는 CSV 파일
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biblio_data.csv")

# KDC(한국십진분류법) 주류 이름 - 앞에 숫자를 붙여야 그래프에서 순서대로 나옵니다
KDC_NAMES = {
    "0": "0 총류", "1": "1 철학", "2": "2 종교", "3": "3 사회과학", "4": "4 자연과학",
    "5": "5 기술과학", "6": "6 예술", "7": "7 언어", "8": "8 문학", "9": "9 역사",
}

# 번역원어 코드 -> 한글 이름
LANG_NAMES = {
    "eng": "영어", "jpn": "일본어", "chi": "중국어", "fre": "프랑스어", "ger": "독일어",
    "ita": "이탈리아어", "rus": "러시아어", "spa": "스페인어",
}

# 같은 출판사인데 이름이 다르게 적힌 경우를 하나로 합치기
PUBLISHER_FIX = {
    "Bookk(부크크)": "부크크",
    "시대에듀 시대고시기획": "시대에듀",
    "문피아(Munpia)": "문피아",
    "박문각(박문각출판)": "박문각",
    "지식과감성#": "지식과감성",
}


# ------------------------------
# 2. 데이터 불러오기와 가공
# ------------------------------
@st.cache_data
def load_data():
    """CSV를 읽어서 분석에 필요한 열만 가져오고, 새로운 열을 만듭니다."""
    use_cols = ["제목", "발행처", "발행년월일", "KDC", "수록매체유형",
                "번역", "번역원어", "이용대상"]
    try:
        df = pd.read_csv(CSV_FILE, encoding="cp949", dtype=str, usecols=use_cols)
    except UnicodeDecodeError:
        # 파일을 UTF-8로 다시 저장한 경우
        df = pd.read_csv(CSV_FILE, encoding="utf-8-sig", dtype=str, usecols=use_cols)

    df["KDC주류"] = df["KDC"].str[0]              # 청구기호 첫 글자 = 주류(0~9)
    df["발행월"] = df["발행년월일"].str[:7]         # 2025-03-15 -> 2025-03
    df["전자책"] = df["수록매체유형"] == "online resource"
    df["발행처"] = df["발행처"].replace(PUBLISHER_FIX)
    return df


def kdc_label(code):
    """'8' -> '8 문학' 처럼 이름을 붙여줍니다."""
    return KDC_NAMES.get(code, "기타")


def draw_donut(table, name_col, value_col):
    """도넛 그래프를 그리는 함수"""
    chart = alt.Chart(table).mark_arc(innerRadius=60).encode(
        theta=alt.Theta(value_col + ":Q"),
        color=alt.Color(name_col + ":N", sort=None, title=None),
        tooltip=[name_col, value_col],
    )
    st.altair_chart(chart, width="stretch")


# ------------------------------
# 3. 분석 화면 함수 (메뉴마다 하나씩)
# ------------------------------
def show_kdc(df):
    st.subheader("분야(KDC 주류)별 도서 수")
    data = df.dropna(subset=["KDC주류"])
    counts = data["KDC주류"].map(kdc_label).value_counts().sort_index()

    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(counts)
    with col2:
        table = counts.reset_index()
        table.columns = ["분야", "건수"]
        draw_donut(table, "분야", "건수")

    top = counts.idxmax()
    st.info(f"가장 많은 분야는 **{top}** ({counts.max():,}건, "
            f"{counts.max() / counts.sum() * 100:.1f}%) 입니다.")
    st.caption(f"※ KDC 번호가 없는 {len(df) - len(data):,}건은 제외했습니다.")


def show_month(df):
    st.subheader("월별 발행 건수")
    months = df["발행월"].dropna()
    months = months[months.str.match(r"2025-\d\d")]     # '2025---' 같은 값 제외
    monthly = months.value_counts().sort_index()

    st.line_chart(monthly)
    st.info(f"가장 많이 발행된 달은 **{monthly.idxmax()}** ({monthly.max():,}건) 입니다.")
    st.caption("※ 10월 이후 건수가 줄어드는 것은 자료 수집 시점의 영향일 수 있어요.")


def show_ebook(df):
    st.subheader("종이책 vs 전자책")
    kinds = df["전자책"].map({True: "전자책", False: "종이책"}).value_counts()
    table = kinds.reset_index()
    table.columns = ["구분", "건수"]

    col1, col2 = st.columns(2)
    with col1:
        draw_donut(table, "구분", "건수")
    with col2:
        data = df.dropna(subset=["KDC주류"])
        ratio = data["전자책"].groupby(data["KDC주류"].map(kdc_label)).mean() * 100
        st.write("분야별 전자책 비율 (%)")
        st.bar_chart(ratio.round(1))

    st.info(f"전체 {len(df):,}건 중 전자책은 **{df['전자책'].sum():,}건** "
            f"({df['전자책'].mean() * 100:.1f}%) 입니다.")


def show_translation(df):
    st.subheader("번역서 비율")
    data = df.dropna(subset=["KDC주류", "번역"])        # 번역 여부가 기록된 책만
    ratio = (data["번역"] == "Y").groupby(data["KDC주류"].map(kdc_label)).mean() * 100

    col1, col2 = st.columns(2)
    with col1:
        st.write("분야별 번역서 비율 (%)")
        st.bar_chart(ratio.round(1))
    with col2:
        st.write("번역서의 원어 TOP 5")
        langs = df["번역원어"].dropna().map(lambda x: LANG_NAMES.get(x, "기타")).value_counts()
        st.bar_chart(langs.head(5))

    st.info(f"번역서 비율이 가장 높은 분야는 **{ratio.idxmax()}** ({ratio.max():.1f}%) 입니다.")


def show_publisher(df):
    st.subheader("출판사 TOP 10")
    n = st.slider("표시할 출판사 수", 5, 20, 10)
    top = df["발행처"].dropna().value_counts().head(n).reset_index()
    top.columns = ["출판사", "건수"]

    chart = alt.Chart(top).mark_bar().encode(
        x=alt.X("건수:Q"),
        y=alt.Y("출판사:N", sort="-x", title=None),
        tooltip=["출판사", "건수"],
    )
    st.altair_chart(chart, width="stretch")
    st.caption("※ 같은 출판사의 다른 표기(예: Bookk(부크크))는 하나로 합쳤습니다.")


# ------------------------------
# 4. 메인 화면
# ------------------------------
st.title("📚 국가서지 2025 데이터 시각화")
st.caption("국립중앙도서관 「대한민국 국가서지 2025 ① 일반도서」(전자책 포함) 서지정보 데이터")

if not os.path.exists(CSV_FILE):
    st.error("biblio_data.csv 파일을 이 파이썬 파일과 같은 폴더에 넣어주세요.")
    st.stop()

df = load_data()

c1, c2, c3 = st.columns(3)
c1.metric("전체 도서", f"{len(df):,}건")
c2.metric("전자책", f"{df['전자책'].sum():,}건")
c3.metric("번역서", f"{(df['번역'] == 'Y').sum():,}건")

menu = st.sidebar.radio(
    "보고 싶은 분석을 고르세요",
    ["분야(KDC)별 도서 수", "월별 발행 추이", "종이책 vs 전자책", "번역서 비율", "출판사 TOP 10"],
)

st.divider()

if menu == "분야(KDC)별 도서 수":
    show_kdc(df)
elif menu == "월별 발행 추이":
    show_month(df)
elif menu == "종이책 vs 전자책":
    show_ebook(df)
elif menu == "번역서 비율":
    show_translation(df)
else:
    show_publisher(df)
