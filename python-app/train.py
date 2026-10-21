"""Train CineMatch's hybrid recommender on MovieLens-100k.

Produces artifacts in ./artifacts:
  movies.csv          movie metadata (id, title, year, genres)
  item_factors.npy    50-d latent vector per movie (SVD)
  item_genres.npy     19-d genre one-hot per movie
  popularity.npy      bayesian-average popularity score per movie
  metrics.json        holdout RMSE/MAE so results stay honest
Run:  python train.py
"""
import json, os
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
GENRES = ["unknown","Action","Adventure","Animation","Children's","Comedy","Crime",
          "Documentary","Drama","Fantasy","Film-Noir","Horror","Musical","Mystery",
          "Romance","Sci-Fi","Thriller","War","Western"]

def load():
    ratings = pd.read_csv(os.path.join(HERE,"data","u.data"), sep="\t",
                          names=["user","item","rating","ts"])
    cols = ["item","title","date","video_date","imdb"] + GENRES
    movies = pd.read_csv(os.path.join(HERE,"data","u.item"), sep="|",
                         encoding="latin-1", header=None, names=cols,
                         usecols=range(24))
    return ratings, movies

def main():
    ratings, movies = load()
    n_users = ratings.user.max(); n_items = ratings.item.max()
    print(f"ratings={len(ratings)} users={n_users} items={n_items}")

    tr, te = train_test_split(ratings, test_size=0.2, random_state=42)
    R = np.zeros((n_users, n_items), dtype=np.float32)
    R[tr.user.values-1, tr.item.values-1] = tr.rating.values
    # mean-center per user for SVD stability
    mask = R > 0
    umean = np.divide(R.sum(1), mask.sum(1), out=np.full(n_users, 3.5, np.float32), where=mask.sum(1)>0)
    Rc = np.where(mask, R - umean[:,None], 0).astype(np.float32)

    svd = TruncatedSVD(n_components=50, random_state=42)
    uf = svd.fit_transform(Rc)                    # users x 50
    vf = svd.components_.T                        # items x 50
    pred = np.clip(uf @ vf.T + umean[:,None], 1, 5)
    pr = pred[te.user.values-1, te.item.values-1]
    rmse = float(np.sqrt(((pr - te.rating.values)**2).mean()))
    mae  = float(np.abs(pr - te.rating.values).mean())
    print(f"holdout RMSE={rmse:.3f} MAE={mae:.3f}")

    # popularity: bayesian average (m=50) so 1-rating 5-star movies don't win
    g = ratings.groupby("item").rating
    cnt, avg = g.count(), g.mean()
    C = float(ratings.rating.mean()); m = 50
    pop = ((cnt*avg + m*C) / (cnt+m)).reindex(range(1, n_items+1), fill_value=C).values

    year = movies.date.str.extract(r"(\d{4})")[0].fillna("").values
    glist = movies[GENRES].apply(lambda r: ", ".join(GENRES[i] for i,v in enumerate(r) if v), axis=1)
    meta = pd.DataFrame({"item": movies.item, "title": movies.title.str.replace(r"\s*\(\d{4}\)$","",regex=True),
                         "year": year, "genres": glist, "n_ratings": cnt.reindex(range(1,n_items+1),fill_value=0).values})

    out = os.path.join(HERE,"artifacts"); os.makedirs(out, exist_ok=True)
    meta.to_csv(os.path.join(out,"movies.csv"), index=False)
    np.save(os.path.join(out,"item_factors.npy"), vf.astype(np.float32))
    np.save(os.path.join(out,"item_genres.npy"), movies[GENRES].values.astype(np.float32))
    np.save(os.path.join(out,"popularity.npy"), pop.astype(np.float32))
    json.dump({"rmse":round(rmse,3),"mae":round(mae,3),"n_ratings":int(len(ratings)),
               "n_movies":int(n_items),"k":50,"dataset":"MovieLens-100k (GroupLens)"},
              open(os.path.join(out,"metrics.json"),"w"), indent=2)
    print("artifacts written to", out)

if __name__ == "__main__":
    main()
