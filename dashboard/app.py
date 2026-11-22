import os
import time
import pandas as pd
import psycopg2
import plotly.express as px
import streamlit as st

# ---------------- Page ----------------
st.set_page_config(
    page_title="WikiPulse | Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Palette inspired by the reference: deep forest sidebar + sage cards.
GREEN = "#0B3025"
GREEN_DARK = "#06251C"
GREEN_MID = "#17634F"
TEAL = "#2F9D86"
TEAL_LIGHT = "#72BFAE"
SAGE = "#DCE5DE"
SAGE_LIGHT = "#EAF0EB"
PAGE = "#F5F7F3"
TEXT = "#172B23"
MUTED = "#78877E"
BORDER = "#DCE5DE"

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = [TEAL, GREEN_MID, TEAL_LIGHT, GREEN, "#A9C4B6"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display:none !important;
    height:0 !important;
    visibility:hidden !important;
}

.stApp { background:#F5F7F3; color:#172B23; }
.block-container { padding:1rem 2rem 2.5rem; max-width:1800px; }
[data-testid="stSidebar"] { background:#06251C; border-right:0; }
[data-testid="stSidebar"] > div:first-child { padding-top:.55rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption { color:#D2DFD8 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color:#FFFFFF !important; }
[data-testid="stSidebar"] hr { border-color:#24483B; }
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background:#143B2E; border-color:#315B4B; color:#FFFFFF;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color:#C5D5CC !important; font-size:12px; }
[data-testid="stSidebar"] .stToggle label p { color:#D2DFD8 !important; }
[data-testid="stSidebar"] .stButton button {
    background:#21866F; border:1px solid #21866F; color:#FFFFFF;
    border-radius:9px; font-weight:700; min-height:40px;
}
[data-testid="stSidebar"] .stButton button:hover { background:#2F9D86; border-color:#2F9D86; color:#FFFFFF; }
.brand { color:#FFFFFF; font-size:25px; font-weight:800; letter-spacing:-1px; }
.brand span { color:#72BFAE; }
.brand-sub { color:#9CB8AA; font-size:10px; letter-spacing:1px; margin-top:-3px; }
.side-label { color:#8EAA9C; font-size:10px; font-weight:800; letter-spacing:1.3px; margin:24px 0 9px; }
.main-heading { color:#0B3025; font-size:30px; font-weight:800; letter-spacing:-.8px; line-height:1.3; padding-top:5px; }
.main-subtitle { color:#78877E; font-size:12px; margin-top:1px; }
.live-pill { display:inline-block; background:#E1F0E9; color:#17634F; border:1px solid #C7E2D5; border-radius:25px; padding:7px 12px; font-size:10px; font-weight:800; }
[data-testid="stMetric"] {
    background:#DCE5DE; border:1px solid #D5E0D8; border-radius:15px;
    padding:15px 17px; min-height:105px; box-shadow:none;
}
[data-testid="stMetricLabel"] { color:#33483D !important; font-size:11px; font-weight:800; letter-spacing:.4px; }
[data-testid="stMetricValue"] { color:#21866F !important; font-size:28px; font-weight:800; }
[data-testid="stMetricDelta"] { color:#17634F !important; }
[data-testid="stPlotlyChart"] {
    background:#DCE5DE; border:1px solid #D5E0D8; border-radius:15px;
    padding:8px 8px 2px;
}
.panel-heading { color:#172B23; font-size:14px; font-weight:800; letter-spacing:.2px; margin:5px 0 9px; }
.activity-card {
    background:#DCE5DE; border:1px solid #D5E0D8; border-radius:15px;
    padding:14px 16px; min-height:190px;
}
.activity-row {
    display:flex; align-items:center; justify-content:space-between; gap:12px;
    padding:10px 0; border-bottom:1px solid #C8D6CD; font-size:12px; color:#20372C;
}
.activity-row:last-child { border-bottom:0; }
.activity-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:75%; }
.activity-meta { color:#667A6E; white-space:nowrap; font-size:10px; }
.type-row { display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #C8D6CD; font-size:12px; color:#20372C; }
.type-row:last-child { border-bottom:0; }
.type-name { display:flex; align-items:center; gap:8px; }
.type-dot { width:8px; height:8px; border-radius:50%; background:#21866F; display:inline-block; }
.type-count { font-weight:800; color:#17634F; }
[data-testid="stDataFrame"] { border:1px solid #D5E0D8; border-radius:12px; overflow:hidden; }
.stButton button { border-radius:9px; }
hr { border-color:#DCE5DE; }
#MainMenu, footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "wikipulse"),
    "user": os.getenv("DB_USER", "wikipulse"),
    "password": os.getenv("DB_PASSWORD", ""),
    "connect_timeout": 5,
}


def read_sql(query, params=None):
    with psycopg2.connect(**DB_CONFIG) as conn:
        return pd.read_sql_query(query, conn, params=params)


def chart_style(fig, height=280):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=12, t=12, b=8),
        paper_bgcolor="#DCE5DE",
        plot_bgcolor="#DCE5DE",
        font=dict(family="DM Sans", color="#20372C", size=11),
    )
    fig.update_xaxes(
        showgrid=True, gridcolor="#C8D6CD", zeroline=False,
        tickfont=dict(color="#40564A"),
        title_font=dict(color="#40564A")
    )
    fig.update_yaxes(
        showgrid=False, zeroline=False,
        tickfont=dict(color="#40564A"),
        title_font=dict(color="#40564A")
    )
    return fig


# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.markdown(
        '<div class="brand">Wiki<span>Pulse</span></div>'
        '<div class="brand-sub">GLOBAL WIKIPEDIA ACTIVITY</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">MONITORING</div>', unsafe_allow_html=True)
    st.markdown("◉ &nbsp; **Overview**")
    st.caption("Live activity dashboard")
    st.markdown('<div class="side-label">FILTERS</div>', unsafe_allow_html=True)

    try:
        wiki_options = read_sql(
            "SELECT DISTINCT wiki FROM wiki_events WHERE wiki IS NOT NULL ORDER BY wiki LIMIT 300"
        )["wiki"].dropna().tolist()
        type_options = read_sql(
            "SELECT DISTINCT event_type FROM wiki_events WHERE event_type IS NOT NULL ORDER BY event_type"
        )["event_type"].dropna().tolist()
    except Exception as exc:
        st.error(f"Database connection failed: {exc}")
        st.stop()

    selected_wikis = st.multiselect(
        "Wiki projects", wiki_options, key="wiki_filter", placeholder="All wikis"
    )
    selected_types = st.multiselect(
        "Event types", type_options, key="type_filter", placeholder="All event types"
    )

    st.markdown('<div class="side-label">DASHBOARD CONTROLS</div>', unsafe_allow_html=True)
    auto_refresh = st.toggle("Auto refresh every 10 seconds", value=True, key="auto_refresh")
    if st.button("↻  Refresh now", use_container_width=True):
        st.rerun()
    sidebar_updated = st.empty()
    if "next_refresh_at" not in st.session_state:
        st.session_state.next_refresh_at = time.time() + 10
    if "last_updated" not in st.session_state:
        st.session_state.last_updated = "Waiting for first update"
    st.markdown("---")
    st.caption("Pipeline")
    st.caption("Wikimedia → NiFi → Kafka → Spark")
    st.caption("Storage · PostgreSQL")

where_parts, filter_params = [], []
if selected_wikis:
    where_parts.append("wiki = ANY(%s)")
    filter_params.append(selected_wikis)
if selected_types:
    where_parts.append("event_type = ANY(%s)")
    filter_params.append(selected_types)
where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""


# Independent sidebar countdown (JavaScript); dashboard data refreshes separately.
with st.sidebar:
    if auto_refresh:
        st.components.v1.html("""
        <div style="background:#10382B;border:1px solid #315B4B;border-radius:12px;padding:12px;margin-top:10px;font-family:Arial,sans-serif;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
            <span style="color:#D8E7DF;font-size:11px;font-weight:700;">AUTO UPDATE</span>
            <span id="countdown" style="color:white;font-size:14px;font-weight:800;">00:10</span>
          </div>
          <div style="height:6px;background:#315B4B;border-radius:10px;margin:10px 0 8px;overflow:hidden;">
            <div id="progress" style="height:6px;width:0%;background:#55B99B;border-radius:10px;"></div>
          </div>
          <div style="color:#9CB8AA;font-size:10px;">Refreshing automatically every 10 seconds</div>
        </div>
        <script>
        let remaining = 10;
        const label = document.getElementById("countdown");
        const bar = document.getElementById("progress");
        setInterval(() => {
          remaining--;
          if (remaining <= 0) remaining = 10;
          label.textContent = "00:" + String(remaining).padStart(2, "0");
          bar.style.width = ((10 - remaining) * 10) + "%";
        }, 1000);
        </script>
        """, height=100)
    else:
        st.markdown("""
        <div style="background:#10382B;border:1px solid #315B4B;border-radius:12px;padding:12px;margin-top:10px;">
          <div style="color:#E2EAE5;font-size:12px;font-weight:800;">Ⅱ AUTO UPDATE PAUSED</div>
          <div style="color:#9CB8AA;font-size:10px;margin-top:6px;">Use Refresh Now to update manually.</div>
        </div>
        """, unsafe_allow_html=True)



@st.fragment(run_every=10 if auto_refresh else None)
def dashboard():
    try:
        # Header
        header_l, header_r = st.columns([5, 1])
        with header_l:
            st.markdown(
                '<div class="main-heading">Live Wikipedia Activity</div>'
                '<div class="main-subtitle">WikiPulse · Global real-time monitoring platform</div>',
                unsafe_allow_html=True,
            )
        with header_r:
            st.markdown('<div class="live-pill">● &nbsp; LIVE STREAMING</div>', unsafe_allow_html=True)

        # KPI row
        kpis = read_sql(f"""
            SELECT
                COUNT(*) AS total_events,
                COUNT(*) FILTER (WHERE event_time >= NOW() - INTERVAL '1 hour') AS last_hour,
                COUNT(*) FILTER (WHERE event_time >= NOW() - INTERVAL '1 minute') AS last_minute,
                COUNT(DISTINCT wiki) AS active_wikis,
                COUNT(DISTINCT username) AS unique_editors
            FROM wiki_events
            {where_clause}
        """, filter_params).iloc[0]

        st.markdown("<br>", unsafe_allow_html=True)
        a, b, c, d, e = st.columns(5, gap="medium")
        a.metric("TOTAL EVENTS", f"{int(kpis['total_events']):,}", help="All events matching the selected filters")
        b.metric("LAST HOUR", f"{int(kpis['last_hour']):,}", help="Events in the previous 60 minutes")
        c.metric("LAST MINUTE", f"{int(kpis['last_minute']):,}", help="Events in the previous 60 seconds")
        d.metric("ACTIVE WIKIS", f"{int(kpis['active_wikis']):,}", help="Distinct wiki projects")
        e.metric("UNIQUE EDITORS", f"{int(kpis['unique_editors']):,}", help="Distinct usernames")

        # Main charts: activity trend + top active wiki projects.
        st.markdown("<br>", unsafe_allow_html=True)
        chart_main, chart_side = st.columns([1.55, 1], gap="large")
        with chart_main:
            st.markdown('<div class="panel-heading">ACTIVITY DURING THE LAST HOUR</div>', unsafe_allow_html=True)
            activity = read_sql(f"""
                WITH minute_series AS (
                    SELECT generate_series(
                        date_trunc('minute', NOW()) - INTERVAL '59 minutes',
                        date_trunc('minute', NOW()),
                        INTERVAL '1 minute'
                    ) AS minute
                ),
                counts AS (
                    SELECT date_trunc('minute', event_time) AS minute, COUNT(*) AS total
                    FROM wiki_events
                    {where_clause}
                    {"AND" if where_clause else "WHERE"} event_time >= NOW() - INTERVAL '1 hour'
                    GROUP BY 1
                )
                SELECT m.minute, COALESCE(c.total, 0) AS total
                FROM minute_series m LEFT JOIN counts c ON m.minute = c.minute
                ORDER BY m.minute
            """, filter_params)
            line = px.line(activity, x="minute", y="total", markers=True)
            line.update_traces(line=dict(color=GREEN_MID, width=3), marker=dict(color=TEAL, size=5))
            line.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Events")
            chart_style(line, 300)
            st.plotly_chart(line, use_container_width=True, config={"displayModeBar": False})

        with chart_side:
            st.markdown('<div class="panel-heading">TOP 10 ACTIVE WIKIS</div>', unsafe_allow_html=True)
            top_wikis = read_sql(
                f"SELECT wiki, COUNT(*) AS total FROM wiki_events{where_clause} "
                "GROUP BY wiki ORDER BY total DESC LIMIT 10",
                filter_params,
            )
            if not top_wikis.empty:
                bars = px.bar(top_wikis.sort_values("total"), x="total", y="wiki", orientation="h")
                bars.update_traces(marker_color=TEAL)
                bars.update_layout(xaxis_title="Events", yaxis_title=None)
                chart_style(bars, 300)
                st.plotly_chart(bars, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No wiki activity for these filters.")

        # Bottom cards: recent activity + event type breakdown.
        st.markdown("<br>", unsafe_allow_html=True)
        recent_col, types_col = st.columns(2, gap="large")
        with recent_col:
            st.markdown('<div class="panel-heading">RECENT ACTIVITY</div>', unsafe_allow_html=True)
            recent = read_sql(f"""
                SELECT event_time, event_type, title, username, wiki
                FROM wiki_events
                {where_clause}
                ORDER BY event_time DESC
                LIMIT 5
            """, filter_params)
            if recent.empty:
                st.info("No recent events.")
            else:
                rows = []
                for _, row in recent.iterrows():
                    title = str(row["title"] or "Untitled")
                    user = str(row["username"] or "Unknown editor")
                    kind = str(row["event_type"] or "event")
                    when = pd.to_datetime(row["event_time"]).strftime("%H:%M:%S")
                    rows.append(
                        f'<div class="activity-row"><span class="activity-name">● &nbsp; '
                        f'<b>{kind.title()}</b> · {title} <span style="color:#667A6E">by {user}</span></span>'
                        f'<span class="activity-meta">{when}</span></div>'
                    )
                st.markdown('<div class="activity-card">' + "".join(rows) + '</div>', unsafe_allow_html=True)

        with types_col:
            st.markdown('<div class="panel-heading">EVENT TYPE BREAKDOWN</div>', unsafe_allow_html=True)
            event_types = read_sql(
                f"SELECT event_type, COUNT(*) AS total FROM wiki_events{where_clause} "
                "GROUP BY event_type ORDER BY total DESC LIMIT 6",
                filter_params,
            )
            if event_types.empty:
                st.info("No event type data.")
            else:
                type_rows = []
                for _, row in event_types.iterrows():
                    type_rows.append(
                        f'<div class="type-row"><span class="type-name"><span class="type-dot"></span>'
                        f'{row["event_type"]}</span><span class="type-count">{int(row["total"]):,}</span></div>'
                    )
                st.markdown('<div class="activity-card">' + "".join(type_rows) + '</div>', unsafe_allow_html=True)

        # Full recent events table remains available below the overview cards.
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("View latest events table", expanded=False):
            search = st.text_input(
                "Search events",
                placeholder="Search page title, editor, comment or event type...",
                key="events_search",
            )
            search_clause = ""
            search_params = list(filter_params)
            if search.strip():
                search_clause = (
                    (" AND " if where_clause else " WHERE ")
                    + "(title ILIKE %s OR username ILIKE %s OR comment ILIKE %s OR event_type ILIKE %s)"
                )
                term = f"%{search.strip()}%"
                search_params.extend([term, term, term, term])

            table = read_sql(f"""
                SELECT event_time, event_type, title, username, wiki,
                       CASE WHEN is_bot IS TRUE THEN 'Bot' ELSE 'Human / Other' END AS editor_type
                FROM wiki_events
                {where_clause}
                {search_clause}
                ORDER BY event_time DESC
                LIMIT 100
            """, search_params)
            st.dataframe(
                table, use_container_width=True, hide_index=True, height=350,
                column_config={
                    "event_time": st.column_config.DatetimeColumn("Time", format="DD MMM, HH:mm:ss"),
                    "event_type": st.column_config.TextColumn("Event", width="small"),
                    "title": st.column_config.TextColumn("Page title", width="large"),
                    "username": st.column_config.TextColumn("Editor", width="medium"),
                    "wiki": st.column_config.TextColumn("Wiki", width="small"),
                    "editor_type": st.column_config.TextColumn("Editor type", width="small"),
                },
            )

        st.session_state.last_updated = time.strftime("%H:%M:%S")
        st.session_state.next_refresh_at = time.time() + 10

    except Exception as exc:
        st.error("Could not load dashboard data.")
        st.exception(exc)


dashboard()
