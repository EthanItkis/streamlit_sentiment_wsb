import streamlit as st
import os
import functions
import portfolio
import time


# Getting Exclude Words
with open("exclude_words.txt", 'r') as file:
    exclude_words = {line.strip() for line in file if line.strip()}

# Streamlit Data Collection
st.title("r/WallStreetBets Stock Sentiment")

amt_posts_queried_input = st.selectbox(
    'How Many Posts Would You Like To Query? (This is before querying so result will be less)',
    [20, 25, 30, 35, 40, 45, 50])

top_post_timeframe_input = st.selectbox(
    'What Time Frame Of Top Posts Would You Like To Query?',
    ["This Week", "This Month", "This Year", "All Time"])

# Button to trigger code execution
if st.button("Run Analysis"):
    
    progress_bar = st.progress(0, text= "Calculating...")  # Initialize the progress bar

    # Store user inputs
    amt_posts_queried = amt_posts_queried_input
    top_post_timeframe = top_post_timeframe_input

    # Execute the rest of the code
    timeframe_mapping = {
        "This Week": "week",
        "This Month": "month",
        "This Year": "year",
        "All Time": "all"
    }
    final_timeframe = timeframe_mapping[top_post_timeframe]

    progress_bar.progress(5, text= "Calculating...")  # Update progress bar

    file_name = 'screen.csv'
    file_path = os.path.abspath(file_name)
    every_stock, ticker_list, stock_list = functions.get_public_stocks(file_path)

    progress_bar.progress(10, text= "Calculating...")  # Update progress bar

    positive_file_dir = "positive_words.txt"
    negative_file_dir = "negative_words.txt"

    list_of_top_urls = functions.top_post_urls(final_timeframe, amt_posts_queried)

    progress_bar.progress(15, text= "Calculating...\t(This part will take a little bit)")

    mentioned_stocks = functions.stock_discussed(list_of_top_urls, every_stock, exclude_words)

    progress_bar.progress(70, text= "Calculating...\t(Almost done)")

    context_data = functions.get_context(mentioned_stocks)

    progress_bar.progress(85, text= "Calculating...")  # Update progress bar

    sentiment_with_context = functions.post_sentiment_version2(context_data, positive_file_dir, negative_file_dir)
    
    progress_bar.progress(90, text= "Calculating...")
    # comment_sentiment_included = functions.each_post_scrapper(sentiment_with_context)
    # comment_agreement_included = functions.determine_agreement(comment_sentiment_included)

    corrected_name_sentiment_data = functions.name_adjuster(sentiment_with_context, ticker_list, stock_list)

    progress_bar.progress(95, text= "Calculating...")

    recommendations = functions.create_recommendation(corrected_name_sentiment_data)

    progress_bar.progress(100)
    progress_bar.empty() 

    # Display recommendations
    st.header("Stock Recommendations")
    st.write("\n")
    st.write("\n")
    st.write("\n")
    st.write("\n")

    # Create columns for stock recommendations
    recommendation_columns = st.columns(3)

    for i, entry in enumerate(recommendations):
        col = recommendation_columns[i % 3]  # Distribute items across three columns
        with col:
            col.write(f"Stock: {entry['stock']}")
            col.write(f"Overall: {entry['overall_sentiment']}")
            # col.write(f"Comment Agreement: {entry['comment_agreement']}")     -  Doesn't work properly yet
            col.write("URLs:")
            for url in entry['urls']:
                col.write(f"  - {url}")
            col.write("---")


    all_stocks_eq = portfolio.create_distributions(recommendations)
    full_distributions_eq = portfolio.create_portfolio_eq(all_stocks_eq)
    st.write("\n")
    st.header("Equal Weight Portfolio Analysis")
    st.write("\n")
    portfolio_df_eq = portfolio.streamlit_graph(full_distributions_eq, final_timeframe)


    all_stocks = portfolio.create_distributions(recommendations)
    full_distributions = portfolio.create_portfolio(all_stocks)
    st.header("Sentiment Based Portfolio Analysis")
    st.write("\n")
    portfolio_df = portfolio.streamlit_graph(full_distributions, final_timeframe)


