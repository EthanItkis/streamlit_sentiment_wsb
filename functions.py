import praw
import csv
from textblob import TextBlob
from ratelimit import limits, sleep_and_retry
import backoff
from typing import List, Dict
import re
import streamlit as st



reddit = praw.Reddit(user_agent=True, 
                        client_id="9SNfpLKTWS71R1vtp9FguA", 
                        client_secret="_LMOYTWYbc1oZKCd9jBhtVYMvtIzgQ", 
                        username="IceCreamHead300", 
                        password="Gwwg6479")








def get_public_stocks(file_path):
    stocks = {}
    all_tickers = []
    all_stocks = []
    with open(file_path, 'r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            all_tickers.append(row[0]) 
            all_stocks.append(row[1]) 
            ticker = row[0].strip()
            stocks[ticker.lower()] = ticker
            for stock in row[1].split():
                stock = stock.strip()
                stocks[stock.lower()] = stock  
    return stocks, all_tickers, all_stocks



@backoff.on_exception(backoff.expo, praw.exceptions.APIException, max_tries=5)
@sleep_and_retry
@limits(calls=30, period=60)
def top_post_urls(final_timeframe, amt_posts_queried):
    subreddit = reddit.subreddit("wallstreetbets")
    top_posts = subreddit.top(time_filter = final_timeframe, limit = amt_posts_queried)
    url_list = []
    for post in top_posts:
        url_list.append(post.shortlink)
    return url_list




def stock_discussed(url_list, every_stock, exclude_words):
    mentioned_stocks = []
    for url in url_list:

        post = reddit.submission(url=url)
        post_text = post.selftext + " " + post.title
        words = set(re.findall(r'\b\w+\b', post_text))  # Extract words ignoring punctuation
        stocks_in_post = [
            every_stock[word.lower()] for word in words
            if (len(word) >= 4 or (sum(1 for c in word if c.isupper()) >= 2))
            and word.lower() not in exclude_words
            and word.lower() in every_stock
            and not any(char.isdigit() for char in word)  # Exclude words with digits
        ]
        if stocks_in_post:
            mentioned_stocks.append({"url": url, "stocks": stocks_in_post})
    return mentioned_stocks




def get_context(mentioned_stocks):
    context_list = []
    for entry in mentioned_stocks:
        url = entry['url']
        stocks = entry['stocks']
        post = reddit.submission(url=url)
        post_text = post.selftext + " " + post.title

        overall_post_sentiment = TextBlob(post_text).sentiment.polarity
        if overall_post_sentiment >0.1:
            post_sentiment = "Positive"
        elif overall_post_sentiment < -0.1:
            post_sentiment = "Negative"
        else:
            post_sentiment = "Neutral"

        words = post_text.split()
        for stock in stocks:
            stock_lower = stock.lower()
            for i, word in enumerate(words):
                if word.lower() == stock_lower:
                    start = max(i - 7, 0)
                    end = min(i + 8, len(words))
                    context = words[start:end]
                    context_string = ' '.join(context)
                    context_list.append({"url": url, "stock": stock, "context": context_string, "post_sentiment":post_sentiment})
    return context_list



 
def post_sentiment(context_data, pos_file_path, neg_file_path):
    with open(pos_file_path, 'r') as file:
        positive_word_list = {line.strip() for line in file if line.strip()}

    with open(neg_file_path, 'r') as file:
        negative_word_list = {line.strip() for line in file if line.strip()}

    result = []

    for item in context_data:
        temp_item = item['context'].split()  
        positive_adj_count = 0
        negative_adj_count = 0

        for i, word in enumerate(temp_item):
            if word in positive_word_list:
                positive_adj_count += 1
            if word in negative_word_list:
                negative_adj_count += 1

        sentiment_val = positive_adj_count - negative_adj_count

        if sentiment_val == 0:
            sentiment = "Neutral Sentiment"
        elif sentiment_val == 1:
            sentiment = "Slightly Positive Sentiment"
        elif sentiment_val == 2:
            sentiment = "Positive Sentiment"
        elif sentiment_val == 3:
            sentiment = "Very Positive Sentiment"
        elif sentiment_val == 4:
            sentiment = "Overwhelmingly Positive Sentiment"
        elif sentiment_val == -1:
            sentiment = "Slightly Negative Sentiment"
        elif sentiment_val == -2:
            sentiment = "Negative Sentiment"
        elif sentiment_val == -3:
            sentiment = "Very Negative Sentiment"
        elif sentiment_val == -4:
            sentiment = "Overwhelmingly Negative Sentiment"

        final_sentiment = str(sentiment_val) + " -> " + sentiment
    
        result.append({"url": item['url'], "stock": item['stock'], "sentiment": final_sentiment, "post_sentiment":item['post_sentiment']})

    return result




def post_sentiment_version2(context_data: List[Dict[str, str]], pos_file_path: str, neg_file_path: str) -> List[Dict[str, str]]:
    with open(pos_file_path, 'r') as file:
        positive_word_list = {line.strip() for line in file if line.strip()}
    with open(neg_file_path, 'r') as file:
        negative_word_list = {line.strip() for line in file if line.strip()}
    result = []
    for item in context_data:
        context_text = item['context']
        temp_item = context_text.split()

        positive_adj_count = 0
        negative_adj_count = 0

        # Detect "more than" and adjust negative sentiment accordingly
        for i in range(len(temp_item) - 1):
            if temp_item[i].lower() == "more" and temp_item[i + 1].lower() == "than":
                halfway_index = len(temp_item) // 2
                if i < halfway_index:
                    negative_adj_count += 10  # Increase the negative count if "more than" is found before the halfway point
                elif i > (halfway_index-2):
                    positive_adj_count += 10
                break

        # Count positive and negative sentiment words
        for word in temp_item:
            if word in positive_word_list:
                positive_adj_count += 1
            if word in negative_word_list:
                negative_adj_count += 1

        # Calculate sentiment value
        sentiment_val_old = positive_adj_count - negative_adj_count
        blob = TextBlob(context_text)
        sentiment_val_new = blob.sentiment.polarity

        if sentiment_val_old == 0 and sentiment_val_new != 0:
            sentiment_val = sentiment_val_new * 2
        elif sentiment_val_new == 0 and sentiment_val_old != 0:
            sentiment_val = sentiment_val_old / 13
        elif sentiment_val_old != 0 and sentiment_val_new != 0:
            sentiment_val = ((sentiment_val_old / 13) + (sentiment_val_new * 2)) / 2
        else:
            sentiment_val = 0

        # Determine sentiment description based on sentiment value
        if sentiment_val == 0:
            sentiment = "Neutral Sentiment"
        elif sentiment_val > 0 and sentiment_val <= 0.1:
            sentiment = "Slightly Positive Sentiment"
        elif sentiment_val > 0.1 and sentiment_val <= .2:
            sentiment = "Positive Sentiment"
        elif sentiment_val > .2 and sentiment_val <= 0.3:
            sentiment = "Very Positive Sentiment"
        elif sentiment_val > 0.3:
            sentiment = "Overwhelmingly Positive Sentiment"
        elif sentiment_val < 0 and sentiment_val >= -0.1:
            sentiment = "Slightly Negative Sentiment"
        elif sentiment_val < -0.1 and sentiment_val >= -0.2:
            sentiment = "Negative Sentiment"
        elif sentiment_val < -0.2 and sentiment_val >= -0.3:
            sentiment = "Very Negative Sentiment"
        else:
            sentiment = "Overwhelmingly Negative Sentiment"

        final_sentiment = f"{sentiment_val} -> {sentiment}"
        result.append({"url": item['url'], "stock": item['stock'], "sentiment": final_sentiment, "post_sentiment": item['post_sentiment']})

    return result




def post_sentiment_version3(context_data: List[Dict[str, str]], pos_file_path: str, neg_file_path: str) -> List[Dict[str, str]]:
    result = []
    for item in context_data:
        context_text = item['context']
        temp_item = context_text.split()

        # Detect "more than" and adjust negative sentiment accordingly
        for i in range(len(temp_item) - 1):
            sentiment_val = 0

            if temp_item[i].lower() == "more" and temp_item[i + 1].lower() == "than":
                halfway_index = len(temp_item) // 2
                if i < halfway_index:
                    sentiment_val -= .2  # Increase the negative count if "more than" is found before the halfway point
                elif i > (halfway_index - 2):
                    sentiment_val += .2
                break

        blob = TextBlob(context_text)
        sentiment_val += blob.sentiment.polarity

        if sentiment_val == 0:
            sentiment = "Neutral Sentiment"
        elif sentiment_val > 0 and sentiment_val <= 0.1:
            sentiment = "Slightly Positive Sentiment"
        elif sentiment_val > 0.1 and sentiment_val <= 0.2:
            sentiment = "Positive Sentiment"
        elif sentiment_val > 0.2 and sentiment_val <= 0.3:
            sentiment = "Very Positive Sentiment"
        elif sentiment_val > 0.3:
            sentiment = "Overwhelmingly Positive Sentiment"
        elif sentiment_val < 0 and sentiment_val >= -0.1:
            sentiment = "Slightly Negative Sentiment"
        elif sentiment_val < -0.1 and sentiment_val >= -0.2:
            sentiment = "Negative Sentiment"
        elif sentiment_val < -0.2 and sentiment_val >= -0.3:
            sentiment = "Very Negative Sentiment"
        else:
            sentiment = "Overwhelmingly Negative Sentiment"

        final_sentiment = f"{sentiment_val} -> {sentiment}"
        result.append({"url": item['url'], "stock": item['stock'], "sentiment": final_sentiment, "post_sentiment": item['post_sentiment']})

    return result




def each_post_scrapper(sentiment_with_context):
    final_with_comment_sentiment = []
    for item in sentiment_with_context:
        post = reddit.submission(url=item['url'])

        overall_comment_sentiment = 0
        comment_count = 0

        for comment in post.comments:
            if isinstance(comment, praw.models.Comment):
                comment_text = comment.body
                comment_sentiment = TextBlob(comment_text).sentiment.polarity
                overall_comment_sentiment += comment_sentiment
                comment_count += 1

        # To avoid division by zero
        if comment_count > 0:
            overall_comment_sentiment /= comment_count
        else:
            overall_comment_sentiment = 0

        if overall_comment_sentiment > 0.1:
            written_comment_sentiment = "Positive"
        elif overall_comment_sentiment < -0.1:
            written_comment_sentiment = "Negative"
        else:
            written_comment_sentiment = "Neutral"

        final_with_comment_sentiment.append({
            "url": item['url'], 
            "stock": item['stock'], 
            "sentiment": item['sentiment'], 
            "post_sentiment": item['post_sentiment'], 
            "comment_sentiment": written_comment_sentiment
        })

    return final_with_comment_sentiment




def determine_agreement(comment_sentiment_included):
    agreement_sentiment = []
    for item in comment_sentiment_included:
        post_sentiment = item["sentiment"]
        comment_sentiment = item["comment_sentiment"]
        if "Positive" in post_sentiment:
            post_sentiment = "Positive"
        elif "Negative" in post_sentiment:
            post_sentiment = "Negative"
        else:
            post_sentiment = "Neutral"

        if post_sentiment == comment_sentiment:
            agreement = "Agree"
        elif post_sentiment != "Neutral" and comment_sentiment == "Neutral":
            agreement = "Neutral"
        else:
            agreement = "Disagree"

        agreement_sentiment.append({
            "url": item['url'],
            "stock": item['stock'],
            "sentiment": item['sentiment'],
            "post_sentiment": item['post_sentiment'],
            "comment_sentiment": item["comment_sentiment"],
            "comment_agreement": agreement
        })
    return agreement_sentiment





def name_adjuster(sentiment_with_context, all_tickers, stock_list):
    final_name_adjusted_list = []
    
    # List of redundant endings to remove
    redundant_endings = ["Common Stock"]
    
    for item in sentiment_with_context:
        stock = item['stock']
        index1 = index2 = -1
        
        # Find the stock index in all_tickers
        for i in range(len(all_tickers)):
            if stock.lower() == all_tickers[i].lower():
                index1 = i
                break
        
        # Find the stock index in stock_list
        for i in range(len(stock_list)):
            if stock.lower() in stock_list[i].lower():
                index2 = i
                break
        
        # Adjust the name if the stock is found in all_tickers
        if index1 != -1:
            new_name = stock_list[index1]
            for ending in redundant_endings:
                if new_name.endswith(ending):
                    new_name = new_name[:-len(ending)].strip()
            new_name = f"{new_name} - {all_tickers[index1]}"
        
        # Adjust the name if the stock is found in stock_list
        elif index2 != -1:
            new_name = stock_list[index2]
            for ending in redundant_endings:
                if new_name.endswith(ending):
                    new_name = new_name[:-len(ending)].strip()
            new_name = f"{new_name} - {all_tickers[index2]}"
        
        # Use the original name if no match is found
        else:
            new_name = stock
        
        final_name_adjusted_list.append({"url": item['url'], "stock": new_name, "sentiment": item['sentiment']})
    
    return final_name_adjusted_list





def create_recommendation(corrected_name_sentiment_data):
    stock_sentiment = {}
    for entry in corrected_name_sentiment_data:
        stock = entry['stock']
        sentiment_value, sentiment_description = entry['sentiment'].split(' -> ')
        sentiment_value = float(sentiment_value)
        url = entry['url']
        if stock not in stock_sentiment:
            stock_sentiment[stock] = {'total_sentiment': 0, 'mentions': 0, 'urls': set()}
        if url not in stock_sentiment[stock]['urls']:
            stock_sentiment[stock]['total_sentiment'] += sentiment_value
            stock_sentiment[stock]['mentions'] += 1
            stock_sentiment[stock]['urls'].add(url)
    final_recommendation = []
    for stock, data in stock_sentiment.items():
        average_sentiment_value = data['total_sentiment'] / (data['mentions'] *.8)
        if average_sentiment_value > 0.5:
            overall_sentiment = "Overwhelmingly Positive Sentiment"
        elif average_sentiment_value > 0.2:
            overall_sentiment = "Very Positive Sentiment"
        elif average_sentiment_value > 0.1:
            overall_sentiment = "Positive Sentiment"
        elif average_sentiment_value > 0:
            overall_sentiment = "Slightly Positive Sentiment"
        elif average_sentiment_value == 0:
            overall_sentiment = "Neutral Sentiment"
        elif average_sentiment_value > -0.1:
            overall_sentiment = "Slightly Negative Sentiment"
        elif average_sentiment_value > -0.2:
            overall_sentiment = "Negative Sentiment"
        elif average_sentiment_value > -0.5:
            overall_sentiment = "Very Negative Sentiment"
        else:
            overall_sentiment = "Overwhelmingly Negative Sentiment"
        final_recommendation.append({
            'stock': stock,
            'overall_sentiment': overall_sentiment,
            'urls': list(data['urls'])
            
        })
    return final_recommendation



