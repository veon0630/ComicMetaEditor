import requests
import json
import time

def check_related(subject_id, connect_timeout=10, read_timeout=30, max_retries=3):
    """
    Check related subjects with timeout and retry mechanism.
    
    Args:
        subject_id: Bangumi subject ID
        connect_timeout: Connection timeout in seconds
        read_timeout: Read timeout in seconds
        max_retries: Maximum number of retry attempts
    """
    url = f"https://api.bgm.tv/v0/subjects/{subject_id}/subjects"
    headers = {"User-Agent": "DAZAO/ComicMetaEditor"}
    timeout = (connect_timeout, read_timeout)
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}...")
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            print(json.dumps(data[0] if data else {}, indent=2, ensure_ascii=False))
            return data
        except requests.exceptions.Timeout:
            print(f"Request timed out (connect: {connect_timeout}s, read: {read_timeout}s)")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Please check your network connection.")
        except requests.exceptions.ConnectionError:
            print("Connection failed. Please check your internet connection.")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error {e.response.status_code}: {e}")
            break  # Don't retry on HTTP errors
        except Exception as e:
            print(f"Unexpected error: {e}")
            break
    
    return None

# Test with a known series ID (e.g., One Piece: 824)
if __name__ == "__main__":
    check_related(269207)
