"""Test the play turn API."""


def test_game_does_not_exist(alice_client):
    """Test submitting a play to a game that does not exist."""
    resp = alice_client.post('/api/game/1/play', json=[])
    assert resp.status_code == 400
    assert resp.get_data(as_text=True) == 'Game does not exist.'
