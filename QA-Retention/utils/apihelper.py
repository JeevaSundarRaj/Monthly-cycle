from http.client import responses

from playwright.sync_api import Page
import requests


class ApiHelpers:
    def __init__(self, page: Page):
        self.payload = None
        self.page = page

    def wait_for_login(self, selector, timeout=10000):
        self.page.wait_for_selector(selector, timeout=timeout).is_visible()

    def get_callId(self, url, headers, key_path):
        """
        Fetches a value from a nested JSON API response using a dot-separated key path.
        Handles indexing into arrays like '0.entry_point_call_id'.
        """
        try:
            response = requests.get(url, headers=headers, timeout=(5, 15))
            response.raise_for_status()
            data = response.json()

            # Traverse using key path
            for key in key_path.split('.'):
                if key.isdigit():
                    data = data[int(key)]  # List index
                else:
                    data = data[key]  # Dict key
            return data

        except (KeyError, TypeError, ValueError, IndexError, requests.exceptions.RequestException) as e:
            print("Error accessing key path:", e)
            return None

    def set_duty_status(self, url, headers, duty_state):
        duty_status = {"is_on_duty": duty_state}
        response = requests.patch(url, json=duty_status, headers=headers, timeout=(5, 15))
        return response

    def setOndutystatus(self, url, bearer_token, user_id):
        duty_state = True
        response = requests.patch(url=url, json={"is_on_duty": duty_state},
                                  headers=self.get_headers(method_type='patch', bearer_token=bearer_token,
                                                           user_id=user_id))
        print(response)
        print("Set to On duty successfully")

    def get_bearer_token(self, client_id, client_secret) -> str:
        body = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        url = "https://dialpadbeta.com/oauth2/token"

        response = requests.post(url, json=body, headers={"Content-Type": "application/json"})
        print("Status:", response.status_code)
        print("Raw Response:", response.text)

        response.raise_for_status()

        data = response.json()
        if "access_token" not in data:
            raise ValueError("Token response missing 'access_token'. Got: " + str(data))

        return data["access_token"]

    def get_headers(self, method_type, bearer_token, user_id):
        """
    Generates HTTP headers for API requests, including the authorization and additional headers
    for POST, PUT and PATCH requests.

    Args:
      method_type (str): The method type of the request.
      bearer_token (str): The bearer token.
      Returns:
        dict: A dictionary containing the HTTP headers.
    """
        headers = {'Authorization': f'Bearer {bearer_token}', 'dp-user-id': f'{user_id}',
                   "Cookie": "DP-ROUTING-BUCKET=100"}
        if method_type.lower() in ['post', 'put', 'patch', 'get']:
            headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Switch-Type': 'harness'
            })
        return headers

    def getUser(self):
        response = requests.get(f"https://dialpadbeta.com/api/v2/users/6094561825914880",
                                headers={
                                    'Authorization': f'Bearer {self.get_bearer_token('qWNGktKHPLK8KxaK5LSTrNFVe', 'F2uH79Qc7FbnFdHwpjvTrFbsPSbbQy5QntwjwzMGUzvyeEusTe')}',
                                    'dp-user-id': '6094561825914880',
                                    "Cookie": "DP-ROUTING-BUCKET=100"})
        response.raise_for_status()
        print(response.json())
        return response.json()
