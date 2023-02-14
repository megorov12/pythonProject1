import datetime
import pandas as pd
import pathlib
from statsmodels.tsa.statespace.sarimax import SARIMAX

def filter_price_series(df, from_date=None, to_date=None):
    result = df
    if from_date != None:
        result = result[result["Date"].dt.strftime('%Y-%m-%d') >= from_date]
    if to_date != None:
        result = result[result["Date"].dt.strftime('%Y-%m-%d') <= to_date]
    return result

class Arima:

    def __init__(self, price_series_df):
        self.__price_series_df = price_series_df
        self.__model = SARIMAX(price_series_df['Price'], order=(0, 1, 1), seasonal_order=(2, 1, 1, 12))
        self.__results = self.__model.fit()

    def forecast(self, number_days_forecasted):

        forecast = self.__results.predict(start=len(self.__price_series_df),
                                          end =(len(self.__price_series_df) - 1) + number_days_forecasted,
                                          typ='levels').rename('Forecast')
        days = 1
        last_date = self.__price_series_df["Date"].max()
        forecast_data = []
        for price in forecast:
            new_date = last_date + datetime.timedelta(days=days)
            days += 1
            forecast_data.append({"date": new_date, "price":price})
        df_forecast = pd.DataFrame(forecast_data)

        return df_forecast

def prepare_data(folder, file_name):

    Filepath = pathlib.Path(__file__).parent.joinpath(folder, file_name)
    Price_df = pd.read_csv(Filepath,  #index_col ='Date',
                         parse_dates = True, dayfirst = True)
    try:
        Price_df['Date'] = pd.to_datetime(Price_df['Date'], format='%d/%m/%Y')
    except:
        Price_df['Date'] = pd.to_datetime(Price_df['Date'], format='%Y-%m-%d')

    Price_df['MA90'] = Price_df['Price'].rolling(90).mean() #Swaure brackets add a new column

    Price_df['Forecast'] = Price_df['Price']

    Price_df['OnlyMonth'] = Price_df['Date'].dt.strftime('%Y/%m') #%Y/%m here order matters

    Price_df_change = Price_df.groupby(['OnlyMonth']).last() #Newdata frame, collapsing all the rows

    Price_df_change['First'] = Price_df.groupby(['OnlyMonth']).first()['Price']

    Price_df_change.rename(columns={'Price': 'Last'}, inplace=True)

    Price_df_change['Change'] = ((Price_df_change['Last'] - Price_df_change['First'])/Price_df_change['First'])*100

    Price_df_change['Change'] = round(Price_df_change['Change'], 3)

    Price_df_change['Averages'] = Price_df.groupby(['OnlyMonth'])['Price'].mean()

    Price_df_change['PCT_Change'] = Price_df_change['Averages'].pct_change()*100

    Price_df_change['SD'] = Price_df.groupby(['OnlyMonth'])['Price'].std()

    Price_df_change['High'] = Price_df.groupby(['OnlyMonth'])['Price'].max()

    Price_df_change['Min'] = Price_df.groupby(['OnlyMonth'])['Price'].min()

    return Price_df, Price_df_change

if __name__ == "__main__":
    Oil = prepare_data('../Data - Oil&Gas', 'OilDaily.csv')
    Gas = prepare_data('../Data - Oil&Gas', 'GasDaily.csv')

    arima_model = Arima(Oil[0])
    forecast = arima_model.forecast(10)