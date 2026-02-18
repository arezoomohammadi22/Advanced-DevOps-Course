import os
import json
import requests
from flask import Flask, request, jsonify
from hashlib import sha256

# Initialize Flask application
app = Flask(__name__)

# Vault Server URL
VAULT_ADDR = "http://127.0.0.1:8200"  # Replace with your Vault server's address
VAULT_TOKEN = os.getenv("VAULT_TOKEN")  # Vault token should be set in environment variables

# Function to interact with Vault and generate a Secret ID
def generate_secret_id(role):
    # Vault AppRole Secret ID generation endpoint
    url = f"{VAULT_ADDR}/v1/auth/approle/role/{role}/secret-id"
    
    headers = {
        "X-Vault-Token": VAULT_TOKEN
    }
    
    # Metadata must be in string format
    metadata = {
        "issued_to": "ci-cd-pipeline",
        "job_id": sha256(role.encode()).hexdigest()  # Just an example, you can use a job ID or other details
    }

    # Convert metadata to JSON string
    metadata_str = json.dumps(metadata)
    
    # Send the request to Vault to generate the Secret ID
    response = requests.post(url, headers=headers, json={"metadata": metadata_str})
    
    if response.status_code == 200:
        # Extract secret_id from response data
        secret_data = response.json()
        return secret_data["data"]["secret_id"]
    else:
        raise Exception(f"Failed to generate Secret ID: {response.text}")

# Endpoint to handle the generation of Secret ID
@app.route('/secret-id', methods=['POST'])
def handle_secret_id():
    # Parse the JSON request body
    request_data = request.get_json()
    if not request_data or 'role' not in request_data:
        return "Bad Request: 'role' is required", 400
    
    role = request_data['role']
    
    try:
        # Generate Secret ID for the given role
        secret_id = generate_secret_id(role)
        
        # Return the Secret ID in JSON format
        return jsonify({"secret_id": secret_id}), 200
    except Exception as e:
        return f"Internal Server Error: {str(e)}", 500

if __name__ == '__main__':
    # Run the Flask application
    app.run(host="0.0.0.0", port=8080)
