"""CineMatch - hybrid movie recommender (Streamlit).
Run:  streamlit run app.py
Model: 50-factor SVD over MovieLens-100k + genre content blend.
"""
import json, os
import numpy as np
import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="CineMatch - Movie Recommender", page_icon="🎬", layout="wide")

@st.cache_data
def load_artifacts():
    a = os.path.join(HERE, "artifacts")
    movies = pd.read_csv(os.path.join(a, "movies.csv"))
    movies["year"] = movies["year"].apply(lambda y: str(int(float(y))) if str(y) not in ("", "nan") else "?")
    F = np.load(os.path.join(a, "item_factors.npy"))
    G = np.load(os.path.join(a, "item_genres.npy"))
    pop = np.load(os.path.join(a, "popularity.npy"))
    metrics = json.load(open(os.path.join(a, "metrics.json")))
    Fn = F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)
    Gn = G / (np.linalg.norm(G, axis=1, keepdims=True) + 1e-9)
    return movies, F, Fn, G, Gn, pop, metrics

movies, F, Fn, G, Gn, pop, metrics = load_artifacts()
N = len(movies)

st.title("🎬 CineMatch")
st.caption("Hybrid recommender trained on 100,000 real ratings (MovieLens-100k) - "
           "50-factor matrix factorization blended with genre similarity.")

with st.sidebar:
    st.header("Your taste")
    well_rated = movies[movies.n_ratings >= 60]
    picks = st.multiselect("Movies you love (pick 3+ for best results)",
                           options=well_rated.title.tolist(), max_selections=15,
                           placeholder="Start typing a movie title...")
    n_recs = st.slider("Number of recommendations", 5, 30, 10)
    alpha = st.slider("Taste vs. genre blend", 0.0, 1.0, 0.7,
                      help="1.0 = pure collaborative (your taste), 0.0 = pure genre match")
    st.divider()
    st.subheader("Honest limits")
    st.caption(f"Trained on MovieLens-100k (movies up to 1998, {metrics['n_movies']:,} titles). "
               f"Holdout RMSE {metrics['rmse']} - about one star of typical error. "
               "New releases are not in this dataset; the live demo on GitHub Pages covers "
               "a broader catalog with a lighter in-browser model.")

def profile_scores(titles):
    idx = movies.index[movies.title.isin(titles)].to_numpy()
    if len(idx) == 0:
        return None, idx
    prof_c = Fn[idx].mean(0)
    prof_g = Gn[idx].mean(0)
    collab = Fn @ prof_c
    content = Gn @ prof_g
    score = alpha * collab + (1 - alpha) * content
    score += 0.05 * (pop - pop.mean())  # tiny popularity prior
    score[idx] = -9  # never recommend what you already picked
    return score, idx

def explain(rec_i, liked_idx):
    sims = Fn[liked_idx] @ Fn[rec_i]
    j = liked_idx[int(np.argmax(sims))]
    return movies.iloc[j].title

if len(picks) < 1:
    st.info("Pick a few movies you love in the sidebar and CineMatch builds your taste profile live.")
    st.subheader("Popular right now (all-time, in this dataset)")
    top = movies.assign(pop=pop).sort_values("pop", ascending=False).head(12)
    cols = st.columns(4)
    for c, (_, m) in zip(cols * 3, top.iterrows()):
        c.markdown(f"**{m.title}** ({m.year})  \n{m.genres}  \n⭐ {m['pop']:.2f}")
else:
    score, liked_idx = profile_scores(picks)
    rec_ids = np.argsort(-score)[:n_recs]
    st.subheader(f"Top {n_recs} for you")
    cols = st.columns(3)
    for k, i in enumerate(rec_ids):
        m = movies.iloc[i]
        cols[k % 3].markdown(
            f"**{m.title}** ({m.year})  \n{m.genres}  \n"
            f"Match {max(0, min(99, int((score[i] + 1) / 2 * 100)))}% - "
            f"because you liked *{explain(i, liked_idx)}*")
    st.divider()
    st.subheader("Your genre mix")
    liked_genres = G[liked_idx].sum(0)
    labels = [l.split("|")[0] for l in open(os.path.join(HERE, "data", "u.genre"), encoding="latin-1").read().splitlines() if l]
    gdf = pd.DataFrame({"genre": labels, "weight": liked_genres}).sort_values("weight", ascending=False)
    gdf = gdf[gdf.weight > 0].head(10)
    st.bar_chart(gdf.set_index("genre"))
    with st.expander("Explore: movies similar to one you like"):
        base = st.selectbox("Base movie", picks)
        bi = movies.index[movies.title == base][0]
        sim = Fn @ Fn[bi]; sim[bi] = -9
        for i in np.argsort(-sim)[:8]:
            m = movies.iloc[i]
            st.write(f"**{m.title}** ({m.year}) - {m.genres} · similarity {sim[i]:.2f}")
