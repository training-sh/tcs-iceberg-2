SHOW TABLES FROM iceberg_polaris.movielens_classroom_s01_silver;
SHOW TABLES FROM iceberg_polaris.movielens_classroom_s01_gold;
SELECT count(*) AS movies FROM iceberg_polaris.movielens_classroom_s01_silver.movies;
SELECT count(*) AS ratings FROM iceberg_polaris.movielens_classroom_s01_silver.ratings;
SELECT count(*) AS movies, sum(rating_count) AS ratings
FROM iceberg_polaris.movielens_classroom_s01_gold.movie_stats;
SELECT count(*) AS days, sum(rating_count) AS ratings
FROM iceberg_polaris.movielens_classroom_s01_gold.daily_ratings;
SELECT * FROM iceberg_polaris.movielens_classroom_s01_gold.genre_stats ORDER BY genre;
SELECT title, rating_count, avg_rating
FROM iceberg_polaris.movielens_classroom_s01_gold.movie_stats
WHERE rating_count >= 100
ORDER BY avg_rating DESC, rating_count DESC, title LIMIT 10;
