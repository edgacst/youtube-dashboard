import streamlit as st
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="유튜브 채널분석 대시보드", layout="wide")

# CSS 커스터마이징
st.markdown("""
<style>
body {
    background-color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
}
.card {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    text-align: center;
    margin-bottom: 20px;
}
.card h4 {
    margin-bottom: 8px;
    color: #555;
}
.card h2 {
    margin: 0;
    color: #2b6cb0;
}

/* ✅ 툴바 숨기기 */
[data-testid="stToolbar"] {
    display: none;
}

</style>
""", unsafe_allow_html=True)

st.title("✨ 유튜브 채널분석 대시보드")

# -----------------------------
# 사이드바
# -----------------------------
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("API 키 입력", type="password")
    my_channel_id = st.text_input("내 채널 ID 입력")
    max_videos = st.slider("분석할 영상 개수", 5, 50, 15)
    st.markdown("---")
    st.write("🏆 경쟁 채널 분석")
    competitor_channel_url = st.text_input("경쟁 채널 URL")
    analyze_competitor = st.button("경쟁 채널 분석 시작")

# -----------------------------
# 유틸 함수
# -----------------------------
def parse_channel_id(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"channel/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None

def get_youtube_client(api_key: str):
    try:
        return build("youtube", "v3", developerKey=api_key)
    except Exception:
        st.error("YouTube 클라이언트를 초기화하지 못했습니다.")
        return None

@st.cache_data(show_spinner=False)
def get_channel_stats(_youtube, channel_id: str) -> dict | None:
    try:
        req = _youtube.channels().list(part="snippet,statistics", id=channel_id)
        res = req.execute()
        if not res.get("items"):
            return None
        item = res["items"][0]
        return {
            "title": item["snippet"]["title"],
            "subscribers": int(item["statistics"].get("subscriberCount", 0)),
            "views": int(item["statistics"].get("viewCount", 0)),
            "videos": int(item["statistics"].get("videoCount", 0)),
        }
    except HttpError:
        return None

@st.cache_data(show_spinner=False)
def get_video_data(_youtube, channel_id: str, max_results: int = 10) -> pd.DataFrame:
    videos = []
    try:
        req = _youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=max_results,
            order="date",
            type="video",
        )
        res = req.execute()
        for item in res.get("items", []):
            video_id = item["id"]["videoId"]
            stats_req = _youtube.videos().list(part="statistics,contentDetails", id=video_id)
            stats_res = stats_req.execute()
            if not stats_res.get("items"):
                continue
            stats_item = stats_res["items"][0]
            stats = stats_item.get("statistics", {})
            duration = stats_item.get("contentDetails", {}).get("duration", "")
            videos.append({
                "videoId": video_id,
                "title": item["snippet"]["title"],
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "publishedAt": item["snippet"]["publishedAt"],
                "duration": duration,
            })
    except HttpError:
        pass
    return pd.DataFrame(videos)

# -----------------------------
# 메인 실행
# -----------------------------
if not api_key:
    st.info("사이드바에서 API 키를 입력해주세요.")
else:
    youtube = get_youtube_client(api_key)
    if youtube is None:
        st.stop()

    # 내 채널 ID가 있으면 내 채널 분석
    if my_channel_id:
        channel_stats = get_channel_stats(youtube, my_channel_id)
        if channel_stats:
            video_df = get_video_data(youtube, my_channel_id, max_results=max_videos)
            # 내 채널 탭 UI 실행
        else:
            st.warning("내 채널 정보를 가져오지 못했습니다.")

    # 경쟁 채널만 조회
    if analyze_competitor and competitor_channel_url:
        competitor_id = parse_channel_id(competitor_channel_url)
        if competitor_id:
            comp_stats = get_channel_stats(youtube, competitor_id)
            if comp_stats:
                st.subheader("⚔️ 경쟁 채널 분석")
                st.write(comp_stats)
            else:
                st.error("경쟁 채널 정보를 가져오지 못했습니다.")

                st.stop()

    video_df = get_video_data(youtube, my_channel_id, max_results=max_videos)
    if video_df.empty:
        st.warning("분석할 영상 데이터가 없습니다.")
        st.stop()



    # -----------------------------
    # 탭 레이아웃
    # -----------------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 성과 분석", 
        "🧠 추천/알림", 
        "📑 리포트/시청자", 
        "⚔️ 경쟁 채널"
    ])

    with tab1:
        st.subheader("📈 성과 분석 (카드형 UI)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='card'><h4>구독자 수</h4><h2>{channel_stats['subscribers']:,}</h2></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='card'><h4>총 조회수</h4><h2>{channel_stats['views']:,}</h2></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='card'><h4>영상 개수</h4><h2>{channel_stats['videos']:,}</h2></div>", unsafe_allow_html=True)

        st.markdown("#### 🎥 영상별 성과")
        st.dataframe(video_df[["title", "views", "likes", "comments", "publishedAt"]], use_container_width=True)

        st.markdown("#### 📊 조회수/좋아요/댓글 시각화")
        fig = px.bar(
            video_df, 
            x="title", 
            y=["views","likes","comments"], 
            barmode="group", 
            title="영상별 성과 비교",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🧠 AI 추천 & 🔔 알림")
        avg_views = video_df["views"].mean()
        alert_videos = video_df[(video_df["views"] > avg_views*1.3) | (video_df["views"] < avg_views*0.7)]
        if not alert_videos.empty:
            st.warning("성과 변동이 큰 영상 발견!")
            st.dataframe(alert_videos[["title","views","likes","comments"]])

    with tab3:
        st.subheader("📑 리포트 & 👥 시청자 분석")
        video_df["engagement"] = (video_df["likes"] + video_df["comments"]) / video_df["views"]
        st.dataframe(video_df[["title","views","likes","comments","engagement"]])

    with tab4:
        st.subheader("⚔️ 경쟁 채널 비교")
        if analyze_competitor:
            competitor_id = parse_channel_id(competitor_channel_url)
            if not competitor_id:
                st.error("올바른 채널 URL을 입력하세요")
            else:
                comp_stats = get_channel_stats(youtube, competitor_id)
                if comp_stats is None:
                    st.error("경쟁 채널 정보를 가져오지 못했습니다.")
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"<div class='card'><h4>내 채널 구독자</h4><h2>{channel_stats['subscribers']:,}</h2></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='card'><h4>내 채널 조회수</h4><h2>{channel_stats['views']:,}</h2></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='card'><h4>내 채널 영상 개수</h4><h2>{channel_stats['videos']:,}</h2></div>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"<div class='card'><h4>경쟁 채널 구독자</h4><h2>{comp_stats['subscribers']:,}</h2></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='card'><h4>경쟁 채널 조회수</h4><h2>{comp_stats['views']:,}</h2></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='card'><h4>경쟁 채널 영상 개수</h4><h2>{comp_stats['videos']:,}</h2></div>", unsafe_allow_html=True)

                    st.subheader("📊 채널 차이")
                    st.markdown(f"<div class='card'><h4>구독자 차이</h4><h2>{channel_stats['subscribers'] - comp_stats['subscribers']:,}</h2></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='card'><h4>조회수 차이</h4><h2>{channel_stats['views'] - comp_stats['views']:,}</h2></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='card'><h4>영상 개수 차이</h4><h2>{channel_stats['videos'] - comp_stats['videos']:,}</h2></div>", unsafe_allow_html=True)

                    comp_videos = get_video_data(youtube, competitor_id, max_results=max_videos)
                    if not comp_videos.empty:
                        comp_view_df = pd.DataFrame({
                            "채널": ["내 채널"] * len(video_df) + ["경쟁 채널"] * len(comp_videos),
                            "title": pd.concat([video_df["title"], comp_videos["title"]], ignore_index=True),
                            "views": pd.concat([video_df["views"], comp_videos["views"]], ignore_index=True),
                        })
                        fig_compare = px.bar(
                            comp_view_df, x="title", y="views", color="채널",
                            title="영상별 조회수 비교", barmode="group", height=500,
                            color_discrete_sequence=["#2b6cb0", "#ff7f0e"]  # 내 채널 파랑, 경쟁 채널 주황
                        )
                        st.plotly_chart(fig_compare, use_container_width=True)

