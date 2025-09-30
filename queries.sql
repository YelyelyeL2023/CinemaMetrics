-- Basic check: View first 10 records from each table
SELECT * FROM movies_metadata LIMIT 10;

-- Query with filtering (WHERE) and sorting (ORDER BY)
-- Movies released after 2010, sorted by popularity descending
SELECT title, release_date, popularity, vote_average
FROM movies_metadata 
WHERE release_date > '2010-01-01' 
ORDER BY popularity DESC;

-- Aggregation (GROUP BY) with functions COUNT, AVG, MIN, MAX
-- Statistics by release year
SELECT 
    EXTRACT(YEAR FROM release_date) as release_year,
    COUNT(*) as movie_count,
    ROUND(AVG(vote_average)::numeric, 2) as avg_rating,
    MIN(budget) as min_budget,
    MAX(revenue) as max_revenue
FROM movies_metadata 
WHERE release_date IS NOT NULL
GROUP BY EXTRACT(YEAR FROM release_date)
ORDER BY release_year DESC;

-- JOIN between tables
-- Movie ratings with movie information
SELECT 
    m.title,
    m.release_date,
    ROUND(AVG(r.rating)::numeric, 2) as avg_user_rating,
    COUNT(r.rating) as rating_count
FROM movies_metadata m
JOIN ratings r ON m.id = r.movieid
GROUP BY m.id, m.title, m.release_date
HAVING COUNT(r.rating) >= 100
ORDER BY avg_user_rating DESC;

-- ============================================
--  10 Analytical Topics
-- ============================================

-- 1. Top 10 highest-grossing movies
-- Shows the most financially successful movies by revenue
SELECT 
    title,
    release_date,
    budget,
    revenue,
    (revenue - budget) as profit
FROM movies_metadata 
WHERE revenue > 0 AND budget > 0
ORDER BY revenue DESC 
LIMIT 10;

-- 2. Movies with highest return on investment (ROI)
-- Identifies movies that made the most money relative to their budget
SELECT 
    title,
    budget,
    revenue,
    ROUND((revenue::numeric / budget) * 100, 2) as roi_percentage
FROM movies_metadata 
WHERE budget > 1000000 AND revenue > budget
ORDER BY (revenue::numeric / budget) DESC 
LIMIT 15;

-- 3. Average rating by genre (using JSONB operations)
-- Shows which genres tend to have higher ratings
SELECT 
    genre_name,
    COUNT(*) as movie_count,
    ROUND(AVG(vote_average)::numeric, 2) as avg_rating
FROM movies_metadata m,
     jsonb_array_elements(m.genres) as genre,
     jsonb_extract_path_text(genre, 'name') as genre_name
WHERE genres IS NOT NULL AND vote_count >= 50
GROUP BY genre_name
HAVING COUNT(*) >= 20
ORDER BY avg_rating DESC;

-- 4. Most active users (by number of ratings)
-- Identifies users who have rated the most movies
SELECT 
    userid,
    COUNT(*) as ratings_given,
    ROUND(AVG(rating)::numeric, 2) as avg_rating_given,
    MIN(rating) as min_rating,
    MAX(rating) as max_rating
FROM ratings
GROUP BY userid
ORDER BY ratings_given DESC
LIMIT 20;

-- 5. Monthly movie release patterns
-- Shows which months have the most movie releases
SELECT 
    EXTRACT(MONTH FROM release_date) as release_month,
    TO_CHAR(TO_DATE(EXTRACT(MONTH FROM release_date)::text, 'MM'), 'Month') as month_name,
    COUNT(*) as movies_released,
    ROUND(AVG(vote_average)::numeric, 2) as avg_rating
FROM movies_metadata 
WHERE release_date IS NOT NULL
GROUP BY EXTRACT(MONTH FROM release_date)
ORDER BY release_month;

-- 6. Production companies with most successful movies
-- Shows which production companies create the most profitable content
WITH company_stats AS (
    SELECT 
        company_name,
        COUNT(*) as movie_count,
        ROUND(AVG(revenue)::numeric, 0) as avg_revenue,
        ROUND(AVG(vote_average)::numeric, 2) as avg_rating,
        SUM(revenue) as total_revenue
    FROM movies_metadata m,
         jsonb_array_elements(m.production_companies) as company,
         jsonb_extract_path_text(company, 'name') as company_name
    WHERE production_companies IS NOT NULL 
      AND revenue > 0
    GROUP BY company_name
    HAVING COUNT(*) >= 5
)
SELECT * FROM company_stats
ORDER BY total_revenue DESC
LIMIT 15;

-- 7. Movie runtime analysis by decade
-- Shows how movie lengths have changed over time
SELECT 
    CONCAT(FLOOR(EXTRACT(YEAR FROM release_date) / 10) * 10, 's') as decade,
    COUNT(*) as movie_count,
    ROUND(AVG(runtime)::numeric, 1) as avg_runtime_minutes,
    MIN(runtime) as shortest_movie,
    MAX(runtime) as longest_movie
FROM movies_metadata 
WHERE release_date IS NOT NULL AND runtime > 0
GROUP BY FLOOR(EXTRACT(YEAR FROM release_date) / 10)
ORDER BY decade DESC;

-- 8. User rating distribution analysis
-- Shows how users typically rate movies
SELECT 
    rating,
    COUNT(*) as rating_count,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM ratings)) * 100, 2) as percentage
FROM ratings
WHERE rating IS NOT NULL
GROUP BY rating
ORDER BY rating DESC;

-- 9. Movies with biggest discrepancy between critic and user ratings
-- Compares IMDb ratings (vote_average) with user ratings from ratings table
SELECT 
    m.title,
    m.vote_average as imdb_rating,
    ROUND(AVG(r.rating)::numeric, 2) as user_rating,
    COUNT(r.rating) as user_rating_count,
    ROUND(ABS(m.vote_average - AVG(r.rating))::numeric, 2) as rating_difference
FROM movies_metadata m
JOIN ratings r ON m.id = r.movieid
WHERE m.vote_average IS NOT NULL 
  AND m.vote_count >= 100
GROUP BY m.id, m.title, m.vote_average
HAVING COUNT(r.rating) >= 50
ORDER BY rating_difference DESC
LIMIT 20;

-- 10. Language distribution and success metrics
-- Shows which languages produce the most successful movies
SELECT 
    original_language,
    COUNT(*) as movie_count,
    ROUND(AVG(vote_average)::numeric, 2) as avg_rating,
    ROUND(AVG(revenue)::numeric, 0) as avg_revenue,
    SUM(revenue) as total_revenue
FROM movies_metadata 
WHERE original_language IS NOT NULL 
  AND revenue > 0
GROUP BY original_language
HAVING COUNT(*) >= 10
ORDER BY total_revenue DESC
LIMIT 15;

-- ============================================
-- Bonus Analysis Queries
-- ============================================

-- Popular keywords analysis
-- Shows the most common keywords in movies
SELECT 
    keyword_name,
    COUNT(*) as frequency
FROM movies_metadata m
JOIN keywords k ON m.id = k.id,
     jsonb_array_elements(k.keywords) as keyword,
     jsonb_extract_path_text(keyword, 'name') as keyword_name
GROUP BY keyword_name
ORDER BY frequency DESC
LIMIT 20;

-- Movie series analysis (movies with collections)
-- Analyzes movies that belong to collections/series
SELECT 
    collection_name,
    COUNT(*) as movies_in_collection,
    ROUND(AVG(vote_average)::numeric, 2) as avg_collection_rating,
    SUM(revenue) as total_collection_revenue
FROM movies_metadata m,
     jsonb_extract_path_text(belongs_to_collection, 'name') as collection_name
WHERE belongs_to_collection IS NOT NULL
GROUP BY collection_name
HAVING COUNT(*) >= 2
ORDER BY total_collection_revenue DESC;
