import os
import json
import httpx
from typing import Optional, List
from google.cloud import storage

REPLIT_SIDECAR_ENDPOINT = "http://127.0.0.1:1106"

def get_storage_client() -> storage.Client:
    credentials_config = {
        "audience": "replit",
        "subject_token_type": "access_token",
        "token_url": f"{REPLIT_SIDECAR_ENDPOINT}/token",
        "type": "external_account",
        "credential_source": {
            "url": f"{REPLIT_SIDECAR_ENDPOINT}/credential",
            "format": {
                "type": "json",
                "subject_token_field_name": "access_token"
            }
        },
        "universe_domain": "googleapis.com"
    }
    
    from google.oauth2 import credentials as oauth2_credentials
    from google.auth import external_account
    
    creds = external_account.Credentials.from_info(credentials_config)
    return storage.Client(credentials=creds, project="")

def get_public_object_search_paths() -> List[str]:
    paths_str = os.environ.get("PUBLIC_OBJECT_SEARCH_PATHS", "")
    paths = [p.strip() for p in paths_str.split(",") if p.strip()]
    if not paths:
        raise ValueError("PUBLIC_OBJECT_SEARCH_PATHS not set")
    return paths

def get_private_object_dir() -> str:
    dir_path = os.environ.get("PRIVATE_OBJECT_DIR", "")
    if not dir_path:
        raise ValueError("PRIVATE_OBJECT_DIR not set")
    return dir_path

def get_bucket_id() -> str:
    bucket_id = os.environ.get("DEFAULT_OBJECT_STORAGE_BUCKET_ID", "")
    if not bucket_id:
        raise ValueError("DEFAULT_OBJECT_STORAGE_BUCKET_ID not set")
    return bucket_id

def parse_object_path(path: str) -> tuple:
    if not path.startswith("/"):
        path = f"/{path}"
    parts = path.split("/")
    if len(parts) < 3:
        raise ValueError("Invalid path: must contain at least a bucket name")
    bucket_name = parts[1]
    object_name = "/".join(parts[2:])
    return bucket_name, object_name

def save_file(content: bytes, object_path: str, content_type: str = "image/jpeg") -> str:
    client = get_storage_client()
    
    public_paths = get_public_object_search_paths()
    if not public_paths:
        raise ValueError("No public object search paths configured")
    
    base_path = public_paths[0]
    full_path = f"{base_path}/{object_path}"
    
    bucket_name, object_name = parse_object_path(full_path)
    
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    
    blob.upload_from_string(content, content_type=content_type)
    
    return full_path

def list_files(prefix: str) -> List[dict]:
    client = get_storage_client()
    
    public_paths = get_public_object_search_paths()
    if not public_paths:
        return []
    
    base_path = public_paths[0]
    full_prefix = f"{base_path}/{prefix}"
    
    bucket_name, object_prefix = parse_object_path(full_prefix)
    
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=object_prefix)
    
    files = []
    for blob in blobs:
        files.append({
            "name": blob.name,
            "path": f"/{bucket_name}/{blob.name}",
            "size": blob.size,
            "updated": blob.updated.isoformat() if blob.updated else None,
            "content_type": blob.content_type
        })
    
    return sorted(files, key=lambda x: x["updated"] or "", reverse=True)

def get_signed_url(object_path: str, ttl_sec: int = 3600) -> str:
    bucket_name, object_name = parse_object_path(object_path)
    
    request_body = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "method": "GET",
        "expires_at": None
    }
    
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(seconds=ttl_sec)
    request_body["expires_at"] = expires_at.isoformat() + "Z"
    
    response = httpx.post(
        f"{REPLIT_SIDECAR_ENDPOINT}/object-storage/signed-object-url",
        json=request_body,
        timeout=15
    )
    
    if not response.is_success:
        raise Exception(f"Failed to sign URL: {response.status_code}")
    
    return response.json().get("signed_url")

def get_public_url(object_path: str) -> str:
    bucket_name, object_name = parse_object_path(object_path)
    return f"https://storage.googleapis.com/{bucket_name}/{object_name}"
