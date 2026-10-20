"""Poster & POS Material Effectiveness Survey - interactive Streamlit dashboard."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

def _ver(v):
    out = []
    for p in v.split(".")[:2]:
        out.append(int("".join(ch for ch in p if ch.isdigit()) or 0))
    return tuple(out)


# newer Streamlit wants width="stretch"; older versions only know use_container_width
W = {"width": "stretch"} if _ver(st.__version__) >= (1, 50) else {"use_container_width": True}
px.defaults.template = "plotly_white"
px.defaults.color_continuous_scale = "Blues"

DATA = Path(__file__).parent / "data" / "Poster_POS_Survey_Clean.xlsx"
BRANDS = ["PepsiCo", "Coca-Cola", "Nestlé", "Other"]
COLORS = {"PepsiCo": "#1F5FBF", "Coca-Cola": "#D7263D", "Nestlé": "#8C8C8C", "Other": "#F2A541",
          "Shopkeeper": "#2A9D8F", "Consumer": "#7A5CC7"}
PLACES = ["Shop front / signboard", "Glass door / window", "Above / behind counter", "Fridge / cooler",
          "Shelf / near products", "Inside wall", "Hanging from ceiling", "Floor standee",
          "Near cash counter", "Other"]
IMPROVE = ["Bigger size", "Brighter colours", "Better design / visuals", "Better placement",
           "Clearer message / offer", "Show price / discount", "Replace old / damaged", "More quantity",
           "Add lighting / LED", "Local language / appeal", "Other", "No improvement needed"]
SK_Q = {"Most attention": "SK Most Attention", "Most visible from outside": "SK Most Visible Outside",
        "Best placement": "SK Best Placement", "Best design": "SK Best Design",
        "Clearest message": "SK Clearest Message", "Most customer interest": "SK Most Customer Interest",
        "Drives purchase": "SK Drives Purchase"}
CS_Q = {"Noticed first": "CS Noticed First", "Easiest to notice": "CS Easiest To Notice",
        "Most attractive": "CS Most Attractive", "Easiest message": "CS Easiest Message",
        "Encourages purchase": "CS Encourages Purchase"}

st.set_page_config(page_title="POS Effectiveness Survey", page_icon="📊", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.2rem;max-width:1400px}
.banner{background:linear-gradient(120deg,#12356b 0%,#1F5FBF 55%,#2A9D8F 100%);color:#fff;padding:26px 32px;
  border-radius:16px;margin-bottom:18px;box-shadow:0 6px 18px rgba(31,95,191,.25)}
.banner h1{color:#fff;margin:0;font-size:1.9rem;padding:0}
.banner p{color:#dbe8ff;margin:6px 0 0;font-size:.95rem}
[data-testid=stMetric]{background:var(--secondary-background-color);padding:14px 16px;border-radius:12px;
  border-left:5px solid #1F5FBF;box-shadow:0 1px 4px rgba(0,0,0,.08)}
[data-testid=stMetricValue]{font-size:1.7rem;font-weight:700}
[data-testid=stMetricLabel]{opacity:.8}
.sec{display:flex;align-items:center;gap:12px;margin:2rem 0 .9rem;padding-bottom:8px;
  border-bottom:2px solid #1F5FBF}
.sec span{font-size:1.15rem;font-weight:700}
.sec small{opacity:.65;font-weight:400}
button[data-baseweb=tab]{font-weight:600;font-size:.95rem}
[data-testid=stSidebar] [data-testid=stExpander]{border-radius:10px}
</style>""", unsafe_allow_html=True)


def section(title, note=""):
    """Section header with a coloured rule under it."""
    n = f"<small>{note}</small>" if note else ""
    st.markdown(f'<div class="sec"><span>{title}</span>{n}</div>', unsafe_allow_html=True)


@st.cache_data
def load():
    return pd.read_excel(DATA, "Clean_Data"), pd.read_excel(DATA, "Cleaning_Log").astype(str)


df_all, clean_log = load()

# ---------------------------------------------------------------- sidebar filters
st.sidebar.markdown("## 🎛️ Filters")


def cb_group(title, options, prefix, expanded=True):
    """Checkbox filter group with All / None shortcuts; everything ticked by default."""
    with st.sidebar.expander(title, expanded=expanded):
        c1, c2 = st.columns(2)
        if c1.button("✔ All", key=f"{prefix}_all", **W):
            for o in options:
                st.session_state[f"{prefix}_{o}"] = True
        if c2.button("✖ None", key=f"{prefix}_none", **W):
            for o in options:
                st.session_state[f"{prefix}_{o}"] = False
        return [o for o in options if st.checkbox(str(o), value=True, key=f"{prefix}_{o}")]


cities = sorted(df_all["City"].dropna().unique())
sel_city = cb_group("📍 City", cities, "city")
sel_type = cb_group("👥 Interview type", ["Shopkeeper", "Consumer"], "type")
flags = list(df_all["Duration Flag"].dropna().unique())
sel_flag = cb_group("⏱️ Interview duration", flags, "flag", expanded=False)
auditors = sorted(df_all["Auditor"].dropna().unique())
sel_aud = cb_group("🧑‍💼 Auditor", auditors, "aud", expanded=False)

df = df_all[df_all["City"].isin(sel_city) & df_all["Interview Type"].isin(sel_type)
            & df_all["Duration Flag"].isin(sel_flag) & df_all["Auditor"].isin(sel_aud)]
sk = df[df["Interview Type"] == "Shopkeeper"]
cs = df[df["Interview Type"] == "Consumer"]
st.sidebar.caption(f"{len(df)} of {len(df_all)} interviews selected")
if len(df) == 0:
    st.warning("No interviews match the current filters.")
    st.stop()


def pct(n, d):
    return 100 * n / d if d else 0.0


def share_chart(frame, col, title, order=None):
    s = frame[col].dropna()
    if s.empty:
        return None
    v = s.value_counts().rename_axis("Answer").reset_index(name="n")
    v["%"] = 100 * v["n"] / len(s)
    fig = px.bar(v, x="%", y="Answer", orientation="h", text=v["%"].map("{:.0f}%".format), title=f"{title} (n={len(s)})",
                 color="Answer", color_discrete_map=COLORS, hover_data={"n": True, "%": ":.1f"})
    fig.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"}, height=300,
                      margin=dict(l=0, r=10, t=40, b=0), xaxis_title=None, yaxis_title=None)
    return fig


def multi_share(frame, prefix, items, title, by=None):
    cols = [f"{prefix}{i}" for i in items if f"{prefix}{i}" in frame]
    sub = frame[cols].apply(pd.to_numeric, errors="coerce")
    sub.columns = [c.replace(prefix, "") for c in cols]
    out = (sub.mean() * 100).rename("%").reset_index().rename(columns={"index": "Item"})
    fig = px.bar(out, x="%", y="Item", orientation="h", text=out["%"].map("{:.0f}%".format), title=title)
    fig.update_traces(marker_color="#1F5FBF")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=380, margin=dict(l=0, r=10, t=40, b=0),
                      xaxis_title="% of respondents", yaxis_title=None)
    return fig


# ---------------------------------------------------------------- header + KPIs
st.markdown("""<div class="banner"><h1>📊 Poster &amp; POS Material Effectiveness Survey</h1>
<p>10 cities · fieldwork 15–20 October 2026 · use the checkboxes in the sidebar to slice by city, respondent type,
interview quality or auditor</p></div>""", unsafe_allow_html=True)

pep_shops = pct(sk["SK Displays PepsiCo"].sum(), len(sk))
coke_shops = pct(sk["SK Displays Coca-Cola"].sum(), len(sk))
noticed = pct((cs["CS Noticed Posters"] == "Yes").sum(), len(cs))
influ = pct((cs["CS Influenced (Yes/No)"] == "Yes").sum(), len(cs))
k = st.columns(6)
k[0].metric("Interviews", f"{len(df):,}")
k[1].metric("Shopkeepers / Consumers", f"{len(sk)} / {len(cs)}")
k[2].metric("Consumers who noticed POS", f"{noticed:.0f}%")
k[3].metric("Say POS influenced purchase", f"{influ:.0f}%")
k[4].metric("Shops displaying PepsiCo", f"{pep_shops:.0f}%")
k[5].metric("Shops displaying Coca-Cola", f"{coke_shops:.0f}%")

tabs = st.tabs(["Overview", "Presence", "Brand performance", "Quality ratings", "Placement",
                "Design preferences", "Improvements", "Voices", "Data & quality"])

# ---------------------------------------------------------------- Overview
with tabs[0]:
    section("Interview coverage", "who we spoke to and what moved them")
    c1, c2 = st.columns([3, 2])
    cc = df.groupby(["City", "Interview Type"]).size().reset_index(name="n")
    fig = px.bar(cc, x="City", y="n", color="Interview Type", color_discrete_map=COLORS, barmode="stack",
                 title="Interviews by city", text="n")
    fig.update_layout(height=360, yaxis_title="Interviews", margin=dict(t=40, b=0))
    c1.plotly_chart(fig, **W)
    inf = cs["CS Purchase Influenced By"].dropna().value_counts().rename_axis("Answer").reset_index(name="n")
    fig = px.pie(inf, names="Answer", values="n", hole=.5, title=f"Which brand's POS influenced purchase? (consumers, n={inf.n.sum()})")
    fig.update_layout(height=360, margin=dict(t=40, b=0))
    c2.plotly_chart(fig, **W)
    section("Key takeaways", "recomputed for the current filters")
    top = lambda f, c: (f[c].dropna().value_counts(normalize=True).head(1) * 100)
    t1 = top(sk, "SK Drives Purchase"); t2 = top(cs, "CS Encourages Purchase")
    bullets = [f"**Presence:** PepsiCo is displayed in {pep_shops:.0f}% of shops vs Coca-Cola {coke_shops:.0f}%.",
               f"**Influence:** {influ:.0f}% of consumers say a poster/display influenced what they bought."]
    if len(t1): bullets.append(f"**Shopkeepers** most often say **{t1.index[0]}** drives purchase ({t1.iloc[0]:.0f}%).")
    if len(t2): bullets.append(f"**Consumers** most often say **{t2.index[0]}** encourages purchase ({t2.iloc[0]:.0f}%).")
    none_shops = pct(sk["SK Displays None"].sum(), len(sk))
    bullets.append(f"**White space:** {none_shops:.0f}% of shops have no beverage POS at all.")
    st.markdown("\n".join(f"- {b}" for b in bullets))

# ---------------------------------------------------------------- Presence
with tabs[1]:
    section("Who has material in the shop?", "multi-select, so totals exceed 100%")
    st.markdown("Shopkeepers: which companies' material is displayed. Consumers: which they noticed. Multi-select, so totals exceed 100%.")
    rows = []
    for b in BRANDS:
        rows.append({"Brand": b, "Group": "Shops displaying (shopkeepers)", "%": pct(sk[f"SK Displays {b}"].sum(), len(sk))})
        rows.append({"Brand": b, "Group": "Noticed by consumers", "%": pct(cs[f"CS Noticed {b}"].sum(), len(cs))})
    pr = pd.DataFrame(rows)
    fig = px.bar(pr, x="Brand", y="%", color="Group", barmode="group", text=pr["%"].map("{:.0f}%".format),
                 color_discrete_sequence=["#2A9D8F", "#7A5CC7"])
    fig.update_layout(height=380, margin=dict(t=20, b=0))
    st.plotly_chart(fig, **W)
    section("Coverage gaps and the photo audit", "by city, and what auditors actually photographed")
    c1, c2 = st.columns(2)
    g = sk.groupby("City").apply(lambda x: pd.Series({b: pct(x[f"SK Displays {b}"].sum(), len(x)) for b in BRANDS + ["None"]}),
                                 include_groups=False)
    hm = px.imshow(g.round(0), text_auto=".0f", aspect="auto", color_continuous_scale="Blues",
                   title="% of shops displaying, by city (None = no beverage POS)")
    hm.update_layout(height=420, margin=dict(t=40, b=0))
    c1.plotly_chart(hm, **W)
    aud = pd.read_excel(DATA, "Poster_Audit_Long")
    aud = aud[aud["Response ID"].isin(df["Response ID"])]
    ac = aud["Company"].value_counts().rename_axis("Company").reset_index(name="n")
    fig = px.pie(ac, names="Company", values="n", hole=.5, color="Company", color_discrete_map=COLORS,
                 title=f"Posters photographed by auditors (n={len(aud)})")
    fig.update_layout(height=420, margin=dict(t=40, b=0))
    c2.plotly_chart(fig, **W)
    og = aud["Other Group"].dropna().value_counts().rename_axis("Group").reset_index(name="n")
    if len(og):
        fig = px.bar(og, x="n", y="Group", orientation="h", title="'Other' posters: what are they?", text="n")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=300, margin=dict(t=40, b=0))
        st.plotly_chart(fig, **W)

# ---------------------------------------------------------------- Brand performance
with tabs[2]:
    section("Who leads on each measure?", "share of respondents choosing each company")
    st.markdown("Share of respondents choosing each company as the leader on every question.")
    rows = []
    for lab, col in SK_Q.items():
        s = sk[col].dropna()
        for b, n in s.value_counts().items():
            rows.append({"Question": lab, "Answer": b, "%": 100 * n / len(s), "Group": f"Shopkeepers (n={len(s)})"})
    for lab, col in CS_Q.items():
        s = cs[col].dropna()
        for b, n in s.value_counts().items():
            rows.append({"Question": lab, "Answer": b, "%": 100 * n / len(s), "Group": f"Consumers (n={len(s)})"})
    bp = pd.DataFrame(rows)
    if bp.empty:
        st.info("No data for this selection.")
    else:
        for grp, sub in bp.groupby(bp["Group"].str.startswith("Shop")):
            name = "Shopkeepers" if grp else "Consumers"
            fig = px.bar(sub, y="Question", x="%", color="Answer", orientation="h", barmode="stack",
                         title=f"{name} – who leads?", color_discrete_map={**COLORS, "None / No difference": "#CFCFCF",
                                                                           "Not Seen / Cannot say": "#E6E6E6"},
                         text=sub["%"].map(lambda v: f"{v:.0f}%" if v >= 6 else ""))
            fig.update_layout(height=370, xaxis_title="% of respondents", yaxis_title=None, margin=dict(t=40, b=0),
                              legend_title=None)
            st.plotly_chart(fig, **W)
    section("Whose material needs the most improvement?", "shopkeepers")
    st.plotly_chart(share_chart(sk, "SK Needs Most Improvement", "Needs most improvement") or px.scatter(),
                    **W)

# ---------------------------------------------------------------- Ratings
with tabs[3]:
    section("Average quality scores", "1–5 scale")
    st.markdown("Average 1–5 score, only among respondents where the brand was present / noticed.")
    long = []
    for c in df.columns:
        if c.startswith("SK Rating ") or c.startswith("CS Rating "):
            who = "Shopkeeper" if c.startswith("SK") else "Consumer"
            dim, brand = c[len("SK Rating "):].split(" | ")
            vals = pd.to_numeric(df.loc[df["Interview Type"] == who, c], errors="coerce").dropna()
            if len(vals):
                long.append({"Respondent": who, "Dimension": dim, "Brand": brand, "Avg": vals.mean(), "n": len(vals)})
    rl = pd.DataFrame(long)
    if rl.empty:
        st.info("No ratings for this selection.")
    else:
        who = st.radio("Rated by", sorted(rl["Respondent"].unique()), horizontal=True)
        sub = rl[rl["Respondent"] == who]
        fig = px.bar(sub, x="Dimension", y="Avg", color="Brand", barmode="group", color_discrete_map=COLORS,
                     text=sub["Avg"].round(1), hover_data=["n"], range_y=[0, 5])
        fig.update_layout(height=420, margin=dict(t=20, b=0), yaxis_title="Average score (1–5)")
        st.plotly_chart(fig, **W)
        piv = sub.pivot(index="Dimension", columns="Brand", values="Avg").round(2)
        st.dataframe(piv, **W)
        st.caption("⚠️ The export did not carry the rating question headers. Shopkeeper dimensions are labelled "
                   "Appeal / Attraction / Placement / Message and consumer ones Rating 1 / Rating 2, as in the source file; "
                   "verify against the questionnaire before quoting individual dimensions. Small bases (e.g. Nestlé) are indicative only.")

# ---------------------------------------------------------------- Placement
with tabs[4]:
    section("Where material is placed vs. where it is noticed")
    c1, c2 = st.columns(2)
    p_rows = []
    for b in BRANDS:
        base = sk[sk[f"SK Displays {b}"] == 1]
        for pl in PLACES:
            col = f"SK Placement {b} | {pl}"
            if col in base and len(base):
                p_rows.append({"Brand": b, "Place": pl, "%": pct(pd.to_numeric(base[col], errors="coerce").sum(), len(base))})
    pdx = pd.DataFrame(p_rows)
    if len(pdx):
        fig = px.imshow(pdx.pivot(index="Place", columns="Brand", values="%").reindex(PLACES).round(0), text_auto=".0f",
                        aspect="auto", color_continuous_scale="Blues",
                        title="Where each brand's material is placed (% of shops displaying that brand)")
        fig.update_layout(height=450, margin=dict(t=40, b=0))
        c1.plotly_chart(fig, **W)
    c2.plotly_chart(multi_share(cs, "CS Noticed At | ", PLACES, f"Where consumers noticed POS (n={len(cs)})"),
                    **W)
    section("Preferred spots", "what each group says works best")
    c1, c2 = st.columns(2)
    for col, frame, title, holder in [("SK Pref Placement", sk, "Shopkeepers: most effective spot", c1),
                                      ("CS Pref Notice Place", cs, "Consumers: where most likely to notice", c2)]:
        f = share_chart(frame, col, title)
        if f: holder.plotly_chart(f, **W)

# ---------------------------------------------------------------- Design
with tabs[5]:
    section("Design element comparison", "pick an element below")
    st.markdown("What makes a poster work – shopkeepers and consumers side by side.")
    pairs = [("Size", "SK Pref Poster Size", "CS Pref Poster Size"), ("Orientation", "SK Pref Orientation", "CS Pref Orientation"),
             ("Design style", "SK Pref Design", "CS Pref Design"), ("Colour", "SK Pref Colour", "CS Pref Colour"),
             ("Product image", "SK Pref Image", "CS Pref Image"), ("Headline", "SK Pref Headline", "CS Pref Headline")]
    el = st.selectbox("Design element", [p[0] for p in pairs])
    _, a, b = next(p for p in pairs if p[0] == el)
    c1, c2 = st.columns(2)
    for col, frame, name, holder in [(a, sk, "Shopkeepers", c1), (b, cs, "Consumers", c2)]:
        f = share_chart(frame, col, name)
        if f: holder.plotly_chart(f, **W)
    section("Quantity, arrangement and information")
    c1, c2 = st.columns(2)
    f = share_chart(sk, "SK Pref Posters per Brand", "Shopkeepers: posters per brand")
    if f: c1.plotly_chart(f, **W)
    f = share_chart(cs, "CS Pref Arrangement", "Consumers: preferred arrangement")
    if f: c2.plotly_chart(f, **W)
    wants = ["Brand / product name", "Key benefit", "Price / discount", "Product features"]
    st.plotly_chart(multi_share(cs, "CS Wants Info | ", wants, f"Information consumers want on a poster (n={len(cs)})"),
                    **W)

# ---------------------------------------------------------------- Improvements
with tabs[6]:
    section("What respondents want improved")
    c1, c2 = st.columns(2)
    c1.plotly_chart(multi_share(sk, "SK Improve | ", IMPROVE, f"Shopkeepers: what to improve (n={len(sk)})"), **W)
    c2.plotly_chart(multi_share(cs, "CS Improve | ", IMPROVE, f"Consumers: what to improve (n={len(cs)})"), **W)
    section("Improvement requests by city", "% of respondents in each city")
    who = st.radio("Respondents", ["Shopkeeper", "Consumer"], horizontal=True, key="imp_who")
    pre = "SK Improve | " if who == "Shopkeeper" else "CS Improve | "
    f = df[df["Interview Type"] == who]
    g = f.groupby("City").apply(lambda x: pd.Series({i: 100 * pd.to_numeric(x[pre + i], errors="coerce").mean()
                                                     for i in IMPROVE if pre + i in x}), include_groups=False)
    fig = px.imshow(g.round(0), text_auto=".0f", aspect="auto", color_continuous_scale="Oranges")
    fig.update_layout(height=420, margin=dict(t=10, b=0))
    st.plotly_chart(fig, **W)

# ---------------------------------------------------------------- Voices
with tabs[7]:
    section("Open-ended responses", "search the comments")
    fields = {"Shopkeeper comments": "Comment (shopkeeper)", "Recommended poster (shopkeeper)": "Recommended Poster (shopkeeper)",
              "Consumer comments": "Comment (consumer)", "Consumer wishes": "Wish (consumer)"}
    pick = st.selectbox("Field", list(fields))
    q = st.text_input("Search text", placeholder="e.g. damaged, signboard, cooler")
    col = fields[pick]
    t = df[["City", "Store Name", "Auditor", col]].dropna(subset=[col])
    t = t[t[col].astype(str).str.strip() != ""]
    if q:
        t = t[t[col].astype(str).str.contains(q, case=False, na=False)]
    st.caption(f"{len(t)} responses")
    st.dataframe(t, **W, hide_index=True, height=480)

# ---------------------------------------------------------------- Data
with tabs[8]:
    section("Fieldwork quality")
    c1, c2 = st.columns(2)
    d = df["Duration Flag"].value_counts().rename_axis("Flag").reset_index(name="n")
    c1.plotly_chart(px.pie(d, names="Flag", values="n", hole=.5, title="Interview duration flags"), **W)
    ap = df.groupby("Auditor").size().reset_index(name="Interviews")
    fig = px.bar(ap, x="Interviews", y="Auditor", orientation="h", title="Interviews per auditor")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=420)
    c2.plotly_chart(fig, **W)
    section("Cleaning log")
    st.dataframe(clean_log, **W, hide_index=True)
    section("Filtered respondent data", "download below")
    st.dataframe(df, **W, height=360)
    st.download_button("Download filtered data (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       "pos_survey_filtered.csv", "text/csv")
