import yfinance as yf
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

def create_distributions(recommendations):
    overwhelmingly_recommended_stocks = []
    very_recommended_stocks = []
    recommended_stocks = []
    slightly_recommended_stocks = []
    neutral_stocks = []
    overwhelmingly_not_recommended_stocks = []
    very_not_recommended_stocks = []
    not_recommended_stocks = []
    slightly_not_recommended_stocks = []

    for item in recommendations:
        temp_sentiment = item['overall_sentiment']
        
        if temp_sentiment == "Overwhelmingly Positive Sentiment":
            overwhelmingly_recommended_stocks.append(item['stock'])
        elif temp_sentiment == "Very Positive Sentiment":
            very_recommended_stocks.append(item['stock'])
        elif temp_sentiment == "Positive Sentiment":
            recommended_stocks.append(item['stock'])
        elif temp_sentiment == "Slightly Positive Sentiment":
            slightly_recommended_stocks.append(item['stock'])
        elif temp_sentiment == "Neutral Sentiment":
            neutral_stocks.append(item['stock'])
        elif temp_sentiment == "Slightly Negative Sentiment":
            slightly_not_recommended_stocks.append(item['stock'])
        elif temp_sentiment == "Negative Sentiment":
            not_recommended_stocks.append(item['stock'])
        elif temp_sentiment == "Very Negative Sentiment":
            very_not_recommended_stocks.append(item['stock'])
        elif temp_sentiment == "Overwhelmingly Negative Sentiment":
            overwhelmingly_not_recommended_stocks.append(item['stock'])

    all_stocks = {
        "overwhelmingly_recommended": overwhelmingly_recommended_stocks,
        "very_recommended": very_recommended_stocks,
        "recommended": recommended_stocks,
        "slightly_recommended": slightly_recommended_stocks,
        "neutral": neutral_stocks,
        "overwhelmingly_not_recommended": overwhelmingly_not_recommended_stocks,
        "very_not_recommended": very_not_recommended_stocks,
        "not_recommended": not_recommended_stocks,
        "slightly_not_recommended": slightly_not_recommended_stocks
    }
    
    return all_stocks




def create_portfolio(all_stocks):
    weight_distribution = {
        'overwhelmingly_recommended': 50,
        'very_recommended': 25,
        'recommended': 15,
        'slightly_recommended': 5
    }

    portfolio = {}

    total_initial_weight = sum(weight for category, weight in weight_distribution.items() if all_stocks.get(category))

    scaling_factor = 100 / total_initial_weight if total_initial_weight != 0 else 0

    for category, initial_weight in weight_distribution.items():
        if category in all_stocks and all_stocks[category]:
            num_stocks = len(all_stocks[category])
            scaled_weight = (initial_weight * scaling_factor) / num_stocks
            for stock in all_stocks[category]:
                portfolio[stock] = scaled_weight

    return portfolio




def create_portfolio_eq(all_stocks):
    portfolio = {}

    all_stock_list = []
    for category, stocks in all_stocks.items():
        all_stock_list.extend(stocks)

    num_stocks = len(all_stock_list)
    if num_stocks == 0:
        return portfolio

    equal_weight = 100 / num_stocks

    for stock in all_stock_list:
        portfolio[stock] = equal_weight

    return portfolio




def graph(full_distributions, final_timeframe):
    today = datetime.today().date()  

    if final_timeframe == "week":
        other_time = today - timedelta(weeks=1)
    elif final_timeframe == "month":
        other_time = today - relativedelta(months=1)
    elif final_timeframe == "year":
        other_time = today - relativedelta(years=1)
    else:
        other_time = today - relativedelta(years=5)

    portfolio_df = pd.DataFrame()

    for stock, weight in full_distributions.items():
        temp_ticker = stock.split()
        ticker = temp_ticker[-1]

        stock_data = yf.download(ticker, start=str(other_time), end=str(today))

        if not stock_data.empty:
            weighted_stock_data = stock_data['Adj Close'] * (weight / 100)

            if portfolio_df.empty:
                portfolio_df = weighted_stock_data.to_frame(name=ticker)
            else:
                portfolio_df = portfolio_df.join(weighted_stock_data, how='outer', rsuffix='_'+ticker)

    portfolio_df['Portfolio Value'] = portfolio_df.sum(axis=1)

    voo_data = yf.download("VOO", start=str(other_time), end=str(today))

    if not voo_data.empty:
        voo_data['Normalized VOO'] = voo_data['Adj Close'] / voo_data['Adj Close'].iloc[0] * portfolio_df['Portfolio Value'].iloc[0]

    plt.figure(figsize=(10, 6))
    plt.plot(portfolio_df.index, portfolio_df['Portfolio Value'], label='WSB Portfolio Value')
    if not voo_data.empty:
        plt.plot(voo_data.index, voo_data['Normalized VOO'], label='VOO (Vanguard Index)')
    plt.xlabel('Date')
    plt.ylabel('Value')
    plt.title(f'Portfolio Value vs VOO Over Time ({final_timeframe})')
    plt.legend()
    plt.show()

    return portfolio_df




def streamlit_graph(full_distributions, final_timeframe):
    today = datetime.today().date()

    if final_timeframe == "week":
        other_time = today - timedelta(weeks=1)
    elif final_timeframe == "month":
        other_time = today - relativedelta(months=1)
    elif final_timeframe == "year":
        other_time = today - relativedelta(years=1)
    else:
        other_time = today - relativedelta(years=5)

    portfolio_df = pd.DataFrame()

    for stock, weight in full_distributions.items():
        ticker = stock.split()[-1] 

        stock_data = yf.download(ticker, start=str(other_time), end=str(today))

        if not stock_data.empty:
            weighted_stock_data = stock_data['Adj Close'] * (weight / 100)

            if portfolio_df.empty:
                portfolio_df = weighted_stock_data.to_frame(name=ticker)
            else:
                portfolio_df = portfolio_df.join(weighted_stock_data, how='outer', rsuffix='_'+ticker)

    if not portfolio_df.empty:
        portfolio_df['Portfolio Value'] = portfolio_df.sum(axis=1)
        
        if not portfolio_df['Portfolio Value'].empty:
            portfolio_df['Normalized Portfolio Value'] = (portfolio_df['Portfolio Value'] / portfolio_df['Portfolio Value'].iloc[0]) * 100
        else:
            st.write("Portfolio Value column is empty.")
            return portfolio_df
    else:
        st.write("There Are No Positive Stocks To Make A Portfolio Out Of.")
        return portfolio_df

    voo_data = yf.download("VOO", start=str(other_time), end=str(today))

    if not voo_data.empty:
        voo_data['Normalized VOO'] = (voo_data['Adj Close'] / voo_data['Adj Close'].iloc[0]) * 100

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(portfolio_df.index, portfolio_df['Normalized Portfolio Value'], label='Normalized Portfolio Value')
        ax.plot(voo_data.index, voo_data['Normalized VOO'], label='VOO (Vanguard Index)', linestyle='--')
        ax.set_xlabel('Date')
        ax.set_ylabel('Normalized Value')
        ax.set_title(f'Normalized Portfolio Value vs VOO Over Time ({final_timeframe})')
        ax.legend()
        st.pyplot(fig)
    else:
        st.write("VOO data is not available for the specified timeframe.")

    return portfolio_df