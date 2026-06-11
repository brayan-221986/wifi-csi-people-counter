from flask import Flask, request, jsonify, render_template
from datetime import datetime
import json, os

app = Flask(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), 'predictions.json')

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

predictions = load_data()

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(predictions[-500:], f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predict', methods=['POST'])
def api_predict():
    body = request.get_json(force=True)
    predictions.append({
        'prediction': body.get('prediction', 0),
        'timestamp': body.get('timestamp', '--:--:--'),
    })
    save_data()
    return jsonify({'ok': True})

@app.route('/api/data')
def api_data():
    return jsonify(predictions[-200:])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
