import requests


def test_read_main(flowchem_test_instance):
    response = requests.get(r"http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert "Flowchem" in response.text

    response = requests.get(r"http://127.0.0.1:8000/test-device/test-component/test")
    assert response.status_code == 200
    assert response.text == "true"

    response = requests.get(r"http://127.0.0.1:8000/test-device2")
    assert response.status_code == 404
