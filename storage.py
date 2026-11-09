"""Private Supabase REST persistence; service key stays in Streamlit Secrets."""
import requests

class Store:
    def __init__(self, url, key):
        self.url = (url or '').rstrip('/')
        self.key = key or ''
        self.enabled = bool(self.url and self.key)

    def request(self, method, params=None, payload=None, preference=None):
        if not self.enabled:
            raise RuntimeError('Supabase 연결이 설정되지 않았습니다.')
        headers = {'apikey': self.key, 'Authorization':f'Bearer {self.key}', 'Content-Type':'application/json'}
        if preference:
            headers['Prefer'] = preference
        response = requests.request(method, f'{self.url}/rest/v1/emotiongap_runs', headers=headers,
                                    params=params, json=payload, timeout=20)
        response.raise_for_status()
        return response.json() if response.content else None

    def get_runs(self, participant_id):
        data = self.request('GET', params={'participant_id': f'eq.{participant_id}', 'select':'run_id,run_number,level,mode,model,created_at,answers', 'order':'run_number.asc', 'limit':'500'})
        return data or []

    def save(self, run):
        # Idempotent: on network retry, the same run_id is updated, not duplicated.
        return self.request('POST', payload=run, preference='resolution=merge-duplicates,return=minimal')
