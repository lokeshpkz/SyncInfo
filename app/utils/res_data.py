from app.proto import output_pb2, personalInfo_pb2
import httpx
import json
import time
from google.protobuf import json_format, message
from Crypto.Cipher import AES
import base64
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Constants
MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASE_VERSION = "OB55"

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.bot_xpert
tokens_collection = db.info_tokens

async def json_to_proto(json_data: str, proto_message: message.Message) -> bytes:
    """Convert JSON data to protobuf bytes"""
    json_format.ParseDict(json.loads(json_data), proto_message)
    return proto_message.SerializeToString()

def pad(text: bytes) -> bytes:
    """Add PKCS7 padding to text"""
    padding_length = AES.block_size - (len(text) % AES.block_size)
    padding = bytes([padding_length] * padding_length)
    return text + padding

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    """Encrypt data using AES-CBC"""
    aes = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = pad(plaintext)
    return aes.encrypt(padded_plaintext)

def decode_protobuf(encoded_data: bytes, message_type: message.Message) -> message.Message:
    """Decode protobuf data"""
    message_instance = message_type()
    message_instance.ParseFromString(encoded_data)
    return message_instance

def get_jwt_tokens():
    """Get JWT tokens from database for allowed regions"""
    allowed_regions = {"bd", "pk", "ind", "us"}
    tokens_cursor = tokens_collection.find({"region": {"$in": list(allowed_regions)}})
    
    tokens = {}
    for doc in tokens_cursor:
        region = doc.get("region")
        token = doc.get("token")
        if region and token:
            tokens[region] = token
    return tokens

def get_url(region):
    if region == "ind":
        return "https://client.ind.freefiremobile.com"
    elif region in {"br", "us", "sac", "na"}:
        return "https://client.us.freefiremobile.com"
    else:
        return "https://clientbp.ppmainecoonghj.com"

def build_headers(token):
    return {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 13; A063 Build/TKQ1.221220.001)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'Authorization': f"Bearer {token}",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASE_VERSION
    }

async def GetAccountInformation(ID, UNKNOWN_ID, endpoint):
    """Get account information from Free Fire API"""
    try:
        # Create JSON payload
        json_data = json.dumps({
            "a": ID,
            "b": UNKNOWN_ID
        })
        
        # Get tokens from database
        tokens = get_jwt_tokens()
        if not tokens:
            return {
                "error": "No tokens found in database",
                "message": "Service temporarily unavailable"
            }

        # Try regions in priority order
        region_priority = ["bd", "pk", "ind", "na"]
        
        for region in region_priority:
            token = tokens.get(region)
            if not token:
                continue
                
            try:
                # Prepare request data
                server_url = get_url(region)
                headers = build_headers(token)
                encoded_result = await json_to_proto(json_data, output_pb2.PlayerInfoByLokesh())
                payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded_result)
                
                # Make API request
                async with httpx.AsyncClient() as client:
                    response = await client.post(server_url + endpoint, data=payload, headers=headers)
                    response.raise_for_status()
                    
                    # Decode response
                    message = decode_protobuf(response.content, personalInfo_pb2.PersonalInfoByLokesh)
                    
                    if hasattr(message, 'developer_info'):
                        # Create developer info object
                        dev_info = personalInfo_pb2.DeveloperInfo()
                        dev_info.developer_name = "@lokeshpkz"  
                        dev_info.portfolio = "https://nexxlokesh.in"
                        dev_info.github = "https://github.com/lokeshpkz"
                        dev_info.youtube = "@aimguardexe"
                        dev_info.signature = "Aimguard — I don't write code. I write legacy."
                        dev_info.do_not_remove_credits = True
                        
                        # Assign to message
                        message.developer_info.CopyFrom(dev_info)
                    
                    return json.loads(json_format.MessageToJson(message))
                    
            except Exception as e:
                # Continue to next region if current one fails
                continue
        
        # If all regions failed
        return {
            "error": "All regions failed",
            "message": "Unable to fetch account information"
        }

    except Exception as e:
        return {
            "error": "Failed to get account info",
            "reason": str(e)
        }
