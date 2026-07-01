from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_docs_available():
    response = client.get('/docs')
    assert response.status_code == 200
    assert 'Swagger UI' in response.text


def test_openapi_available():
    response = client.get('/openapi.json')
    assert response.status_code == 200
    data = response.json()
    assert data['info']['title'] == 'Clausio API'
    assert '/api/stories' in data['paths']
    assert '/api/corpus/puzzle/generate' in data['paths']


def test_stories_available():
    response = client.get('/api/stories')
    assert response.status_code == 200
    data = response.json()
    assert 'stories' in data
    assert isinstance(data['stories'], list)


def test_corpus_sources_available():
    response = client.get('/api/corpus/sources')
    assert response.status_code == 200
    data = response.json()
    assert 'sources' in data
    assert isinstance(data['sources'], list)
    ids = {item['id'] for item in data['sources']}
    assert 'aozora' in ids
    assert 'nhk_easy' in ids


def test_corpus_topics_aozora_n4():
    response = client.get('/api/corpus/topics', params={'source': 'aozora', 'level': 'N4'})
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    assert 'topics' in data
    assert isinstance(data['topics'], list)


def test_story_puzzle_validation_error_on_empty_body():
    response = client.post('/api/puzzle/generate', json={})
    assert response.status_code == 422
    body = response.json()
    assert 'detail' in body


def test_corpus_puzzle_not_found_for_bad_topic():
    response = client.post(
        '/api/corpus/puzzle/generate',
        json={'source': 'aozora', 'topic_id': 'does-not-exist', 'level': 'N4'},
    )
    assert response.status_code == 404
    assert response.json()['detail'] == 'Topic not found: does-not-exist'


def test_story_puzzle_generate_success():
    response = client.post(
        '/api/puzzle/generate',
        json={'file_path': 'modern.txt', 'level': 'N5'},
    )
    assert response.status_code == 200
    data = response.json()
    assert data['target_level_requested'] == 'N5'
    assert 'grid_matrix' in data
    assert len(data['grid_matrix']) == 25


def test_corpus_puzzle_generate_success():
    response = client.post(
        '/api/corpus/puzzle/generate',
        json={'source': 'aozora', 'topic_id': 'modern', 'level': 'N5'},
    )
    assert response.status_code == 200
    data = response.json()
    assert data['target_level_requested'] == 'N5'
    assert 'grid_matrix' in data
    assert len(data['grid_matrix']) == 25
