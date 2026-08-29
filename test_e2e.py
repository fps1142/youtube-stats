from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print('Testing health check...')
h_resp = client.get('/api/health')
print('Health status:', h_resp.status_code, h_resp.json())

print('\nTesting /api/analyze with real YouTube community post URL...')
payload = {
    'url': 'https://www.youtube.com/post/UgkxjHhnb7b_31Ry7mGWXCmVnOL--bN4czrL',
    'max_comments': 2000,
    'correct_price': 3800
}
a_resp = client.post('/api/analyze', json=payload)
print('Analyze status:', a_resp.status_code)
if a_resp.status_code == 200:
    res = a_resp.json()
    print('Author:', res['metadata']['author'])
    print('Title:', res['metadata']['title'])
    print('Image URL exists:', bool(res['metadata']['image_url']))
    print('Total comments fetched:', res['stats']['summary']['total_comments'])
    print('Valid price guesses:', res['stats']['summary']['valid_answers_count'])
    print('Mean price:', res['stats']['summary']['mean_price'])
    print('Median price:', res['stats']['summary']['median_price'])
    print('Mode price:', res['stats']['summary']['mode_price'])
    print('Histogram bins count:', len(res['stats']['histogram']))
    for h in res['stats']['histogram'][:4]:
        pct = h['percentage']
        print('  Bin:', h['label'], '->', h['count'], f'({pct}%)')
    
    quiz = res['stats']['quiz_result']
    if quiz:
        print('\nQuiz simulation (Correct: 3800):')
        print('  Exact matches:', quiz['exact_matches_count'])
        print('  Near matches:', quiz['near_matches_count'])
        print('  Talk gap:', quiz['talk_gap'])
        print('  Script text preview:\n', quiz['script_text'])
    
    print('\nTesting static frontend serving...')
    f_resp = client.get('/')
    print('Frontend index.html status:', f_resp.status_code, 'Content length:', len(f_resp.text))
else:
    print('Error:', a_resp.text)
