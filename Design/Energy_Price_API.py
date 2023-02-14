from datetime import datetime
import csv
import dash
from Design.data import prepare_data, filter_price_series, Arima
from flask import Flask, jsonify, request
import hashlib
from main import server

#server = Flask("__name__")
#app1 = dash.Dash(server=server)

class API_Data_Model:
    def __init__(self, usersfile):
        self.__usersfile = usersfile
        self.__load_users(usersfile)
        self.__load_terminology()
        self.__sessions = {}
        self.__energy_data = {}

    def get_session_owner(self,session_id):
        if session_id in self.__sessions.keys():
            return self.__sessions[session_id]
        return "Error"

    def __load_users(self, usersfile):
        users = csv.DictReader(open(usersfile))
        self.__password_hashes = {}
        for user in users:
            self.__password_hashes[user["Username"]] = user["Password"]

    def __load_terminology(self):
        self.__terminology = {"MA90": "Moving Average over the last 90 days",
                       "Forecast": "ARIMA used: more info on https://www.investopedia.com/terms/a/autoregressive-integrated-moving-average-arima.asp about how this works",
                       "GasPrice": "Daily market averages",
                       "OilPrice": "Daily market averages", }

    def load_energy_data_set(self, name, filename, directory = None):
        prices_df = prepare_data(directory, filename)[0]
        prediction_model = Arima(prices_df)
        self.__energy_data[name] = {"df":prices_df, "model":prediction_model}

    def get_energy_prices_df(self, name):
        if name in self.__energy_data.keys():
            return self.__energy_data[name]["df"]

    def get_energy_prices_model(self, name):
        if name in self.__energy_data.keys():
            return self.__energy_data[name]["model"]

    def check_session_is_valid(self, session_id):
        if session_id in self.__sessions.keys():
            Username = self.__sessions[session_id]
            if Username in self.__password_hashes.keys():
                P_Hash = self.__password_hashes[Username]
                verify_id = hashlib.md5((Username +
                                         P_Hash +
                                         datetime.today().strftime("%Y-%m-%d")
                                         ).encode()).hexdigest()
                return session_id == verify_id
        return False

    def create_new_session(self, username, p_hash):
        if username in self.__password_hashes.keys():
            if p_hash == self.__password_hashes[username]:
                session_id = hashlib.md5((username +
                                          p_hash +
                                          datetime.today().strftime("%Y-%m-%d")
                                          ).encode()).hexdigest()
                data = {"status": "OK", "Message": "Login Successful", "session_id": session_id}
                self.__sessions[session_id] = username
            else:
                data = {"status": "ERROR", "Message": "Password Incorrect"}
        else:
            data = {"status": "ERROR", "Message": "User not found"}
        return data

    def get_terminology(self):
        return self.__terminology

    def register_new_user(self, username, p_hash):
        if username in self.__password_hashes.keys():
            data = {"status": "ERROR", "Message": "User already exists"}
        else:
            self.__password_hashes[username] = p_hash
            p_file = open(self.__usersfile, "a")
            p_file.write(f'\n{username},{p_hash}')
            data = {"status": "OK", "Message": "User added"}
        return data

#api_data = API_Data_Model("Data - Oil&Gas/users.csv")
#api_data.load_energy_data_set("Oil", "OilDaily.csv", directory="../Data - Oil&Gas")
#api_data.load_energy_data_set("Gas", "GasDaily.csv", directory="../Data - Oil&Gas")

@server.route('/fuelprice', methods=['GET'])
def fuelprice():
    if request.method == 'GET':
        args = request.args
        data_series = None #Declared and easier to decode - declared
        display_columns = ["Date", "Price"]
        if "series" in args:
            json_response = {}
            if args["series"] == "OilPrice":
                data_series = api_data.get_energy_prices_df("Oil")
                model = api_data.get_energy_prices_model("Oil")
                json_response["series"] = "Oil"
            elif args["series"] == "GasPrice":
                data_series = api_data.get_energy_prices_model("Gas")
                model = api_data.get_energy_prices_model("Gas")
                json_response["series"] = "Gas"
            if "from_date" in args:
                data_series = filter_price_series(data_series, from_date = args["from_date"])
            if "to_date" in args:
                data_series = filter_price_series(data_series, to_date=args["to_date"])
            if "show_max" in args:
                if args["show_max"] == "True":
                    json_response["Max"] = data_series["Price"].max()
            if "MA90" in args:
                if args["MA90"] == "True":
                    display_columns.append("MA90")
            if "Forecast" in args:
                days = int(args["Forecast"])
                forecast_df = model.forecast(days)
                json_response["Forecast"] = forecast_df.to_dict("records")
            df_results = data_series[display_columns]
            df_results["Date"] = df_results["Date"].dt.strftime('%Y-%m-%d')
            json_response["Prices"] = df_results.to_dict("records")
            return json_response

@server.route('/jargon', methods=['GET'])
def explain():
    if request.method == 'GET':
        args = request.args
        if 'term' in args:
            data = {"term": args["term"], "definition": api_data.get_terminology()[args["term"]] }
            return jsonify(data)

@server.route('/register_user', methods=['GET']) #not GET becasue it shows on the URL - but not for a POST
def register_user():
    if request.method == 'GET':
        args = request.args
        if 'P_Hash' in args and "Username" in args:
            data = api_data.register_new_user(args["Username"], args["P_Hash"])
            return jsonify(data)
    return{}

@server.route('/login', methods=['GET']) #not GET becasue it shows on the URL - but not for a POST
def user_login():
    if request.method == 'GET':
        args = request.args
        if 'P_Hash' in args and "Username" in args:
            data = api_data.create_new_session(args["Username"], args["P_Hash"])
            return jsonify(data)
    return{}
