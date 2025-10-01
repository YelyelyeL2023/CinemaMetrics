import pandas as pd
import psycopg2
import plotly.express as px
import numpy as np

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'Data',
    'user': 'postgres',
    'password': '2006',
    'port': 5432
}

def get_db_connection():
    """Establish database connection."""
    return psycopg2.connect(**DB_CONFIG)

def execute_query(query, description):
    """Execute SQL query and return DataFrame."""
    print(f"\nExecuting query: {description}")
    print("-" * 60)
    
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Query returned {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    
    return df

def create_interactive_time_slider():
    """Create single interactive Plotly scatter plot with time slider."""
    
    # Query to get movie data over time with multiple JOINs
    query = """
    SELECT 
        EXTRACT(YEAR FROM m.release_date) as release_year,
        jsonb_extract_path_text(genre, 'name') as genre_name,
        m.budget,
        m.revenue,
        m.vote_average,
        m.vote_count,
        m.popularity,
        m.title,
        m.runtime,
        COUNT(DISTINCT jsonb_extract_path_text(cast_member, 'name')) as cast_size
    FROM movies_metadata m
    JOIN credits c ON m.id = c.id,
         jsonb_array_elements(m.genres) as genre,
         jsonb_array_elements(c."cast") as cast_member
    WHERE m.release_date IS NOT NULL 
      AND EXTRACT(YEAR FROM m.release_date) BETWEEN 1995 AND 2020
      AND m.budget > 1000000 
      AND m.revenue > 1000000
      AND m.vote_count >= 100
      AND jsonb_extract_path_text(genre, 'name') IN ('Action', 'Drama', 'Comedy', 'Thriller', 'Romance', 'Adventure', 'Animation', 'Horror')
    GROUP BY m.id, m.title, m.release_date, m.budget, m.revenue, m.vote_average, 
             m.vote_count, m.popularity, m.runtime, jsonb_extract_path_text(genre, 'name')
    ORDER BY release_year;
    """
    
    df = execute_query(query, "Movie data with time dimension for interactive visualization")
    
    # Create the interactive scatter plot with time slider
    print("\n📊 Creating Interactive Time Slider Visualization...")
    
    fig = px.scatter(
        df,
        x="budget",
        y="revenue", 
        animation_frame="release_year",
        animation_group="title",
        size="vote_count",
        color="genre_name",
        hover_name="title",
        hover_data={
            "vote_average": ":.1f",
            "popularity": ":.1f", 
            "runtime": ":.0f",
            "cast_size": True,
            "budget": ":,.0f",
            "revenue": ":,.0f"
        },
        size_max=50,
        title="Movie Budget vs Revenue Over Time (1995-2020)<br><sub>Interactive Time Slider | Size: Vote Count | Color: Genre</sub>",
        labels={
            "budget": "Budget (USD)",
            "revenue": "Revenue (USD)",
            "genre_name": "Genre",
            "release_year": "Release Year",
            "vote_count": "Vote Count"
        },
        template="plotly_white",
        width=1400,
        height=800,
        # Use log scale for better distribution
        log_x=True,
        log_y=True
    )
    
    # Format axes with better ranges and formatting
    fig.update_xaxes(
        title="Budget (USD) - Log Scale",
        tickformat=".2s",
        range=[6, 8.5]  # 10^6 to 10^8.5 (1M to ~300M)
    )
    fig.update_yaxes(
        title="Revenue (USD) - Log Scale", 
        tickformat=".2s",
        range=[6, 9.5]  # 10^6 to 10^9.5 (1M to ~3B)
    )
    
    # Add diagonal break-even line (on log scale)
    fig.add_shape(
        type="line",
        x0=6, y0=6, x1=8.5, y1=8.5,  # Log scale coordinates
        line=dict(color="red", width=2, dash="dash"),
        name="Break-even Line"
    )
    
    # Customize animation settings for smooth playback
    fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 1000
    fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 500
    
    # Update layout for better appearance
    fig.update_layout(
        font_size=12,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left", 
            x=1.01
        )
    )
    
    print("✓ Created Interactive Scatter Plot with Time Slider")
    print("📈 Features:")
    print("  • Time slider: 1995-2020")
    print("  • Logarithmic scales for better distribution")
    print("  • Interactive hover information")
    print("  • Play/pause animation controls")
    print("  • Genre color coding")
    print("  • Vote count sizing")
    print("  • Break-even reference line")
    
    # Show the interactive plot
    fig.show()
    
    return fig

def main():
    """Main function to create the interactive visualization."""
    print("🎬 CinemaMetrics Analytics - Interactive Time Slider")
    print("=" * 60)
    
    try:
        # Test database connection
        conn = get_db_connection()
        conn.close()
        print("✓ Database connection successful")
        
        # Create the interactive visualization
        fig = create_interactive_time_slider()
        
        print("\n" + "=" * 60)
        print("📊 INTERACTIVE VISUALIZATION READY")
        print("=" * 60)
        print("🎯 For Defense Demonstration:")
        print("  1. Use the time slider to jump to specific years")
        print("  2. Click PLAY button for automatic animation")
        print("  3. Hover over points to see detailed movie information")
        print("  4. Click legend items to show/hide genres")
        print("  5. Zoom and pan to explore different areas")
        print("  6. Show how movie industry evolved 1995-2020")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()