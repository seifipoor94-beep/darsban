from supabase import create_client

# اطلاعات اتصال به Supabase
url = "https://mpeotfhtlhouyzkvnubw.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1wZW90Zmh0bGhvdXl6a3ZudWJ3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAwMjA4NDcsImV4cCI6MjA3NTU5Njg0N30.ylwI1wsUVteSj-VrrXcoHD4o4sfGGNPz1m4zjy7S1mc"

# ساخت کلاینت Supabase
supabase = create_client(url, key)

# تابع تست اتصال (اختیاری)
def test_supabase_connection():
    try:
        response = supabase.table("users").select("*").limit(1).execute()
        return True, response.data
    except Exception as e:
        return False, str(e)
