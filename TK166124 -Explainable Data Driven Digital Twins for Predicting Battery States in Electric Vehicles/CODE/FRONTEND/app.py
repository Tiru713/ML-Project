from flask import Flask,render_template,url_for,redirect,request,jsonify,render_template_string
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import numpy as np
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.losses import MeanSquaredError
app = Flask(__name__)
import pandas as pd


import mysql.connector
mydb = mysql.connector.connect(
    host='localhost',
    port=3306,          
    user='root',        
    passwd='',          
    database='electric_vehicle'  
)

mycur = mydb.cursor()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/registration', methods=['POST', 'GET'])
def registration():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirmpassword = request.form['confirmpassword']
        address = request.form['Address']
        
        if password == confirmpassword:
            # Check if user already exists
            sql = 'SELECT * FROM users WHERE email = %s'
            val = (email,)
            mycur.execute(sql, val)
            data = mycur.fetchone()
            
            if data is not None:
                msg = 'User already registered!'
                return render_template('registration.html', msg=msg)
            else:
                # Insert new user without hashing password
                sql = 'INSERT INTO users (name, email, password, Address) VALUES (%s, %s, %s, %s)'
                val = (name, email, password, address)
                mycur.execute(sql, val)
                mydb.commit()
                
                msg = 'User registered successfully!'
                return render_template('registration.html', msg=msg)
        else:
            msg = 'Passwords do not match!'
            return render_template('registration.html', msg=msg)
    return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        sql = 'SELECT * FROM users WHERE email=%s'
        val = (email,)
        mycur.execute(sql, val)
        data = mycur.fetchone()

        if data:
            stored_password = data[2]  # Assuming the password is in the 4th column

            # Check if the password matches the stored password
            if password == stored_password:
                return render_template('viewdata.html')
            else:
                msg = 'Password does not match!'
                return render_template('login.html', msg=msg)
        else:
            msg = 'User with this email does not exist. Please register.'
            return render_template('login.html', msg=msg)
    return render_template('login.html')



@app.route('/viewdata', methods=['GET', 'POST'])
def viewdata():
    df1 = pd.read_excel('Arranged_TripA01.xlsx')
    df2 = pd.read_csv('bat_charge(4).csv')
    
    table1 = df1.to_html(classes='table table-striped', index=False)
    table2 = df2.to_html(classes='table table-striped', index=False)
    
    selected_table = None
    selected_dataset = None

    if request.method == 'POST':
        selected_dataset = request.form['dataset']
        if selected_dataset == 'dataset1':
            selected_table = table1
        elif selected_dataset == 'dataset2':
            selected_table = table2

    return render_template('viewdata.html', selected_table=selected_table, selected_dataset=selected_dataset)




algorithms_results = {
    'CNN': {'r2_score': 0.83497},
    'SVR': {'r2_score': 0.99599},
    'FNN': {'r2_score': 0.33411},
    'RBF_SVR': {'r2_score': 0.99599},
    'Random Forest': {'r2_score': 0.99734},
    'XGBoost': {'r2_score': 0.99736},
    'LSTM': {'r2_score': 0.99976},
    'DNN': {'r2_score': 0.81}
}

@app.route('/algo',methods=['GET','POST'])
def algo():
    selected_algorithm = None
    r2_score_value = None

    if request.method == 'POST':
        selected_algorithm = request.form.get('algorithm')
        r2_score_value = algorithms_results[selected_algorithm]['r2_score']
    return render_template('algo.html', algorithms=algorithms_results.keys(), selected_algorithm=selected_algorithm, r2_score_value=r2_score_value)





@app.route('/prediction1', methods=['GET', 'POST'])
def prediction1():
    if request.method == 'POST':
        # Load and prepare data
        df1 = pd.read_excel('Arranged_TripA01.xlsx')

        # Select columns related to battery performance
        battery_performance_columns = [
            'Battery Voltage [V]',
            'Battery Current [A]',
            'Battery Temperature [°C]',
            'max. Battery Temperature [°C]',
            'SoC [%]',
            'displayed SoC [%]',
            'min. SoC [%]',
            'max. SoC [%)'
        ]
        
        # Separate input features and target variable
        X = df1[battery_performance_columns].drop(columns=['SoC [%]'])
        y = df1['SoC [%]']
        
        # Split data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Standardize features
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Get user input values
        Battery_Voltage = float(request.form['Battery Voltage [V]'])
        Battery_Current = float(request.form['Battery Current [A]'])
        Battery_Temperature = float(request.form['Battery Temperature [°C]'])
        max_Battery_Temperature = float(request.form['max. Battery Temperature [°C]'])
        displayed_SoC = float(request.form['displayed SoC [%]'])
        min_SoC = float(request.form['min. SoC [%]'])
        max_SoC = float(request.form['max. SoC [%)'])
        
        # Create feature list
        input_data = [Battery_Voltage, Battery_Current, Battery_Temperature, max_Battery_Temperature, displayed_SoC, min_SoC, max_SoC]
        
        # Train RandomForestRegressor
        rf = RandomForestRegressor()
        rf.fit(X_train_scaled, y_train)
        
        # Scale the input data before prediction
        input_data_scaled = scaler.transform([input_data])
        
        # Predict the battery performance
        predicted_performance = rf.predict(input_data_scaled)[0]
        
        # Prepare the message based on the predicted performance
        issue = ""
        precautions = ""
        
        if predicted_performance >= 84:
            msg = f"Performance of the battery is {predicted_performance:.2f}. The battery is operating optimally. Keep maintaining appropriate voltage and temperature levels for sustained performance."
        elif 81.1 <= predicted_performance <= 83.9:
            if Battery_Temperature > -40:
                issue += "Temperature is too high. "
                precautions += "Ensure proper cooling and avoid overcharging. "
            if Battery_Voltage < 280:
                issue += "Voltage is below the required threshold. "
                precautions += "Check the battery connections and charge appropriately. "
            if Battery_Current < 20:
                issue += "Current is too high. "
                precautions += "Reduce the load on the battery or check for short circuits. "
            if not issue:
                issue = "Battery performance is slightly reduced. "
            msg = f"Performance of the battery is {predicted_performance:.2f}. {issue}{precautions}"
        else:
            msg = f"Performance of the battery is {predicted_performance:.2f}. Consider performing a detailed inspection for potential issues."
        
        # Render the template with the message
        return render_template('prediction1.html', msg=msg)

    return render_template('prediction1.html')



@app.route('/prediction2',methods=['GET','POST'])
def prediction2():
    # Load the saved model
    model = load_model('lstm_vdc_model.h5', compile=False)
    model.compile(optimizer='adam', loss=MeanSquaredError())

    # Load and preprocess the dataset
    file_path = 'bat_charge(4).csv'
    data = pd.read_csv(file_path)
    data['Time'] = pd.to_datetime(data['Time'], format='%d-%m-%Y %H:%M')
    data.set_index('Time', inplace=True)
    data = data.resample('T').mean().interpolate()
    scaler = MinMaxScaler(feature_range=(0, 1))
    data['VDC_normalized'] = scaler.fit_transform(data['VDC'].values.reshape(-1, 1))

    # Prepare the last sequence of data
    n_steps = 30
    last_sequence = data['VDC_normalized'].values[-n_steps:]
    def predict_future_vdc(minutes):
        predictions = []
        sequence = last_sequence.copy()
        
        for _ in range(minutes):
            next_pred = model.predict(sequence.reshape(1, n_steps, 1))
            predictions.append(next_pred[0, 0])
            sequence = np.append(sequence[1:], next_pred)
        
        predictions_actual = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        
        return predictions_actual
    if request.method == 'POST':
        try:
            minutes = int(request.form['minutes'])
            predicted_values = predict_future_vdc(minutes)
            # Convert numpy array to list for JSON serialization
            predicted_values_list = predicted_values.flatten().tolist()
            return jsonify(predicted_values=predicted_values_list)
        except ValueError:
            return jsonify(error="Invalid input. Please enter a valid number.")
     
    # return render_template_string(open('prediction2.html').read())
    return render_template('prediction2.html')

 










if __name__ == '__main__':
    app.run(debug=True)