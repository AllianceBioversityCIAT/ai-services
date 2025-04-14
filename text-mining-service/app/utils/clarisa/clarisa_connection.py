import os
import time
import jwt
import requests
import logging
from typing import Dict, Any, TypeVar, Generic, Optional, cast
from app.utils.logger.logger_util import logger

T = TypeVar('T')
X = TypeVar('X')


class Clarisa:
    def __init__(self):
        """Initialize Clarisa connection with configuration from environment variables"""
        clarisa_host = os.getenv('CLARISA_HOST', '')
        if not clarisa_host.endswith('/'):
            clarisa_host += '/'
        self.clarisa_host = clarisa_host + 'api/'

        self.auth_body = {
            "login": os.getenv('CLARISA_LOGIN'),
            "password": os.getenv('CLARISA_PASSWORD')
        }
        self.token = None

    async def get_token(self) -> str:
        """Get a valid token or request a new one if needed"""
        if not self.token or not self._valid_token(self.token):
            try:
                auth_url = os.getenv('CLARISA_HOST', '')
                if not auth_url.endswith('/'):
                    auth_url += '/'
                auth_url += 'auth/login'

                logger.debug(
                    f"Requesting token from {auth_url} with login: {self.auth_body['login']}")
                response = requests.post(auth_url, json=self.auth_body)
                response.raise_for_status()

                token_response = response.json()
                if 'access_token' not in token_response:
                    logger.error(
                        f"Token response does not contain access_token: {token_response}")
                    raise Exception("Invalid token response format")

                self.token = token_response.get('access_token')
                logger.debug(f"Token obtained: {self.token[:20]}...")
            except Exception as e:
                logger.error(f"Error obtaining token: {str(e)}")
                raise
        return self.token

    def _valid_token(self, token: str) -> bool:
        """Check if token is still valid"""
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            now = int(time.time())
            expiration = decoded.get('exp')
            logger.debug(
                f"Token expiration time: {expiration}, current time: {now}")
            if decoded and 'exp' in decoded:
                return decoded['exp'] > now
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
        return False

    async def post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send authenticated POST request to Clarisa API"""
        try:
            token = await self.get_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            safe_data = {**data}
            if 'secret' in safe_data:
                safe_data['secret'] = '********'
            logger.debug(
                f"Sending POST request to {self.clarisa_host}{path} with data: {safe_data}")

            url = f"{self.clarisa_host}{path}"
            response = requests.post(
                url,
                json=data,
                headers=headers
            )

            status_code = response.status_code
            try:
                response_data = response.json()
                logger.debug(
                    f"Response status: {status_code}, data: {response_data}")
            except:
                response_text = response.text
                logger.debug(
                    f"Response status: {status_code}, text: {response_text[:100]}")
                response_data = {
                    "error": "Invalid JSON response", "text": response_text[:100]}

            return {
                "status": status_code,
                "response": response_data
            }
        except Exception as e:
            logger.error(f"Error in POST request: {str(e)}")
            return {
                "status": 500,
                "response": {"error": str(e)}
            }
