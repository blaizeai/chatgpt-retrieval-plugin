#!/usr/bin/env python3
"""
Quick test script for the /list endpoint.
Run this after starting the server to verify the list functionality works.
"""

import requests
import json
import os

# Configuration
BASE_URL = "http://localhost:8000"
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "dev-secret")

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}


def test_list_documents():
    """Test the /list endpoint"""

    print("=" * 80)
    print("Testing POST /list endpoint")
    print("=" * 80)

    # Test 1: List all documents (no filter)
    print("\n1. List all documents (limit=10)")
    response = requests.post(
        f"{BASE_URL}/list",
        headers=headers,
        json={"limit": 10, "offset": 0}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success! Found {data['total']} total documents")
        print(f"   📄 Showing {len(data['documents'])} documents:")
        for doc in data['documents']:
            print(f"      - ID: {doc['document_id'][:8]}... ({doc['chunk_count']} chunks)")
            if doc.get('metadata', {}).get('author'):
                print(f"        Author: {doc['metadata']['author']}")
            if doc.get('sample_text'):
                preview = doc['sample_text'][:80] + "..." if len(doc['sample_text']) > 80 else doc['sample_text']
                print(f"        Preview: {preview}")
    else:
        print(f"   ❌ Failed with status {response.status_code}")
        print(f"   Error: {response.text}")
        return False

    # Test 2: List with filter
    print("\n2. List documents with filter (source='file')")
    response = requests.post(
        f"{BASE_URL}/list",
        headers=headers,
        json={
            "limit": 5,
            "offset": 0,
            "filter": {"source": "file"}
        }
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success! Found {data['total']} documents with source='file'")
        print(f"   📄 Showing {len(data['documents'])} documents")
    else:
        print(f"   ❌ Failed with status {response.status_code}")
        print(f"   Error: {response.text}")
        return False

    # Test 3: Pagination
    if data['total'] > 2:
        print("\n3. Test pagination (offset=1, limit=1)")
        response = requests.post(
            f"{BASE_URL}/list",
            headers=headers,
            json={"limit": 1, "offset": 1}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Got document at offset 1")
            if data['documents']:
                print(f"   Document ID: {data['documents'][0]['document_id'][:8]}...")
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            return False

    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        test_list_documents()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server at", BASE_URL)
        print("   Make sure the server is running: poetry run dev")
    except Exception as e:
        print(f"❌ Error: {e}")
