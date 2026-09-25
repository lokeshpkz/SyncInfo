from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import app.utils.res_data as res_data
import json
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/info')
def get_account_info():
    uid = request.args.get('uid')
    api_key = request.args.get('key')
    
    # 1. Check if key is provided
    if not api_key:
        return jsonify({
            "error": "Unauthorized",
            "message": "Missing 'key' parameter."
        }), 401, {'Content-Type': 'application/json; charset=utf-8'}
        
    expected_key = os.getenv("API_KEY")
    key_expiry_str = os.getenv("API_KEY_EXPIRY")
    
    # 2. Check if key is valid
    if api_key != expected_key:
        return jsonify({
            "error": "Unauthorized",
            "message": "Invalid API key."
        }), 401, {'Content-Type': 'application/json; charset=utf-8'}
        
    # 3. Check if key is expired
    if key_expiry_str:
        try:
            expiry_date = datetime.strptime(key_expiry_str, "%Y-%m-%d").date()
            if datetime.now().date() > expiry_date:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "API key has expired."
                }), 401, {'Content-Type': 'application/json; charset=utf-8'}
        except ValueError:
            pass # fallback if date format is invalid in .env

    # 4. Check uid
    if not uid:
        response = {
            "error": "Invalid request",
            "message": "Empty 'uid' parameter. Please provide a valid 'uid'."
        }
        return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}


    return_data = asyncio.run(res_data.GetAccountInformation(uid, "7","/GetPlayerPersonalShow"))
    formatted_json = json.dumps(return_data, indent=2, ensure_ascii=False)
    return formatted_json, 200, {'Content-Type': 'application/json; charset=utf-8'}


if __name__ == '__main__':
    app.run(port=3000, host='0.0.0.0', debug=True)
