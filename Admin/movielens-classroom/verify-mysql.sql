USE movielens_classroom_s01;
SHOW TABLES;
SELECT count(*) AS movies, sum(rating_count) AS ratings FROM movie_stats;
SELECT count(*) AS days, sum(rating_count) AS ratings FROM daily_ratings;
SELECT * FROM genre_stats ORDER BY genre;
SELECT title, rating_count, avg_rating FROM movie_stats
WHERE rating_count >= 100
ORDER BY avg_rating DESC, rating_count DESC, title LIMIT 10;
