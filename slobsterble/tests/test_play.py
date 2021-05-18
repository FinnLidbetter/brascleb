"""Test the play turn API."""


def test_game_does_not_exist(client, alice_headers):
    """Test submitting a play to a game that does not exist."""
    resp = client.post('/game/1', json=[], headers=alice_headers)
    assert resp.status_code == 400
    assert resp.get_data(as_text=True) == 'Game does not exist.'
