#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import requests
import pytest
from hcloud import HcloudClient, HcloudAPIException


class TestHetznerClient(object):

    @pytest.fixture()
    def client(self):
        HcloudClient.version = '0.0.0'
        return HcloudClient(token="project_token")

    @pytest.fixture()
    def response(self):
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"result": "data"}).encode('utf-8')
        return response

    @pytest.fixture()
    def fail_response(self, response):
        response.status_code = 422
        error = {
            "code": "invalid_input",
            "message": "invalid input in field 'broken_field': is too long",
            "details": {
                "fields": [
                    {
                        "name": "broken_field",
                        "messages": ["is too long"]
                    }
                ]
            }
        }
        response._content = json.dumps({"error": error}).encode('utf-8')
        return response

    def test__get_user_agent(self, client):
        user_agent = client._get_user_agent()
        assert user_agent == "hcloud-python/0.0.0"

    def test__get_headers(self, client):
        headers = client._get_headers()
        assert headers == {
            "User-Agent": "hcloud-python/0.0.0",
            "Authorization": "Bearer project_token"
        }

    def test_request_library_mocked(self, client):
        response = client.request("POST", "url", params={"1": 2})
        assert response.__class__.__name__ == 'MagicMock'

    def test_request_ok(self, mocked_requests, client, response):
        mocked_requests.request.return_value = response
        response = client.request("POST", "/servers", params={"argument": "value"}, timeout=2)
        mocked_requests.request.assert_called_once()
        assert mocked_requests.request.call_args[0] == ('POST', 'https://api.hetzner.cloud/v1/servers')
        assert mocked_requests.request.call_args[1]['params'] == {'argument': 'value'}
        assert mocked_requests.request.call_args[1]['timeout'] == 2
        assert response == {"result": "data"}

    def test_request_fails(self, mocked_requests, client, fail_response):
        mocked_requests.request.return_value = fail_response
        with pytest.raises(HcloudAPIException) as exception_info:
            client.request("POST", "http://url.com", params={"argument": "value"}, timeout=2)
        error = exception_info.value
        assert error.code == "invalid_input"
        assert error.message == "invalid input in field 'broken_field': is too long"
        assert error.details['fields'][0]['name'] == "broken_field"

    def test_request_500(self, mocked_requests, client, fail_response):
        fail_response.status_code = 500
        fail_response.reason = "Internal Server Error"
        fail_response._content = "Internal Server Error"
        mocked_requests.request.return_value = fail_response
        with pytest.raises(HcloudAPIException) as exception_info:
            client.request("POST", "http://url.com", params={"argument": "value"}, timeout=2)
        error = exception_info.value
        assert error.code == 500
        assert error.message == "Internal Server Error"
        assert error.details['content'] == "Internal Server Error"

    def test_request_broken_json_200(self, mocked_requests, client, response):
        content = "{'key': 'value'".encode('utf-8')
        response.reason = "OK"
        response._content = content
        mocked_requests.request.return_value = response
        with pytest.raises(HcloudAPIException) as exception_info:
            client.request("POST", "http://url.com", params={"argument": "value"}, timeout=2)
        error = exception_info.value
        assert error.code == 200
        assert error.message == "OK"
        assert error.details['content'] == content