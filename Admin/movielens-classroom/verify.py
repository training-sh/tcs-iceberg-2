"""Independent CSV reference versus live Trino/Iceberg/MySQL results; run from the exercise directory."""
import collections
import csv
import datetime
import json
from pathlib import Path
import subprocess


def main():
    source = Path.home() / "data" / "movielens-small"
    with (source / "movies.csv").open(encoding="utf-8", newline="") as file:
        movies = {int(r["movieId"]): r for r in csv.DictReader(file)}
    daily = collections.Counter()
    genres = collections.Counter()
    movie_counts = collections.Counter()
    movie_sums = collections.Counter()
    movie_users = collections.defaultdict(set)
    ratings = 0
    with (source / "ratings.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            ratings += 1
            movie_id = int(row["movieId"])
            movie_counts[movie_id] += 1
            movie_sums[movie_id] += float(row["rating"])
            movie_users[movie_id].add(int(row["userId"]))
            date = datetime.datetime.fromtimestamp(int(row["timestamp"]), datetime.timezone.utc).date().isoformat()
            daily[date] += 1
            for genre in movies[int(row["movieId"])]["genres"].split("|"):
                genres[genre] += 1
    expected = {"movies": len(movies), "ratings": ratings, "days": len(daily),
                "daily": dict(daily), "genres": dict(genres),
                "movie_stats": {key: (movie_counts[key], movie_sums[key] / movie_counts[key] if movie_counts[key] else None,
                                      len(movie_users[key])) for key in movies}}
    # Query from the existing Jupyter container so service DNS resolves. Uses Python standard library.
    code = "expected=" + repr(expected) + "\n" + '''
import urllib.request,time,json
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def query(sql):
    request=urllib.request.Request('http://trino:8080/v1/statement',data=sql.encode(),headers={'X-Trino-User':'team','X-Trino-Session':'query_max_run_time=2m'})
    rows=[]; deadline=time.monotonic()+150; next_uri=None
    try:
        while True:
            with opener.open(request,timeout=20) as response:page=json.load(response)
            next_uri=page.get('nextUri')
            if 'error' in page:raise RuntimeError('Trino verification statement failed')
            rows.extend(page.get('data',[]))
            if not next_uri:return rows
            if time.monotonic()>deadline:raise TimeoutError('Verification query timeout')
            request=urllib.request.Request(next_uri)
    finally:
        if next_uri:
            try:opener.open(urllib.request.Request(next_uri,method='DELETE'),timeout=5).close()
            except OSError:pass
silver='iceberg_polaris.movielens_classroom_s01_silver'
assert query('SELECT count(*) FROM '+silver+'.movies')==[[expected['movies']]]
assert query('SELECT count(*) FROM '+silver+'.ratings')==[[expected['ratings']]]
for schema in ('iceberg_polaris.movielens_classroom_s01_gold','mysql.movielens_classroom_s01'):
    assert query('SELECT count(*),sum(rating_count) FROM '+schema+'.movie_stats')==[[expected['movies'],expected['ratings']]], schema
    rows=query('SELECT movieId,rating_count,avg_rating,distinct_users FROM '+schema+'.movie_stats')
    assert len(rows)==len(expected['movie_stats'])
    seen=set()
    for movie_id,count,average,users in rows:
        assert movie_id not in seen
        seen.add(movie_id)
        ref_count,ref_average,ref_users=expected['movie_stats'][movie_id]
        assert (count,users)==(ref_count,ref_users),(schema,movie_id)
        if ref_average is None: assert average is None
        else: assert abs(average-ref_average)<=0.00000051,(schema,movie_id)
    actual_daily=dict(query('SELECT CAST(rating_date AS VARCHAR),rating_count FROM '+schema+'.daily_ratings'))
    assert actual_daily==expected['daily'],schema+' daily reference differs'
    actual_genres=dict(query('SELECT genre,rating_count FROM '+schema+'.genre_stats'))
    assert actual_genres==expected['genres'],schema+' genre reference differs'
    print('REFERENCE_PASS',schema,json.dumps({'movies':expected['movies'],'ratings':expected['ratings'],'days':expected['days'],'genres':len(expected['genres'])}))
print('END_TO_END_REFERENCE_PASS')
'''
    subprocess.run(["oc", "exec", "-i", "-n", "bigdata", "spark-master-0", "-c", "jupyter", "--", "python3", "-"],
                   input=code, text=True, check=True)


if __name__ == "__main__":
    main()
