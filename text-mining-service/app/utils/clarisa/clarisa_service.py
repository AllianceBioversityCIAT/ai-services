import os
from typing import Dict, Any, Optional
from app.utils.clarisa.clarisa_connection import Clarisa
from app.utils.logger.logger_util import logger


class ResponseValidateClarisa:
    def __init__(self, data, valid):
        self.data = data
        self.valid = valid


class ClarisaService:
    def __init__(self):
        """Initialize ClarisaService with configuration"""
        self.mis_settings = {
            "acronym": os.getenv('CLARISA_MIS', ''),
            "environment": os.getenv('CLARISA_MIS_ENV', '')
        }
        self.connection = Clarisa()

    async def authorization(self, client_id: str, client_secret: str) -> ResponseValidateClarisa:
        """Validate client credentials with CLARISA"""
        try:
            if not client_id or not client_secret:
                logger.error("Missing client credentials")
                return ResponseValidateClarisa(data=None, valid=False)

            data = {
                "client_id": client_id,
                "secret": client_secret
            }

            result = await self.connection.post('app-secrets/validate', data)
            logger.debug(f"Authorization result: {result}")

            return self.format_valid(result)
        except Exception as e:
            logger.error(f"Authorization error: {str(e)}")
            return ResponseValidateClarisa(data=None, valid=False)

    async def create_connection(self, mis: Dict[str, str]) -> Dict[str, Any]:
        """Create connection with another MIS"""
        try:
            data = {
                "receiver_mis": self.mis_settings,
                "sender_mis": mis
            }
            cla_conn = await self.connection.post('app-secrets/create', data)
            result = self.format_valid(cla_conn)
            if result.valid and result.data:
                return result.data
            logger.error(f"Failed to create connection: {cla_conn}")
            raise Exception("Failed to create connection")
        except Exception as e:
            logger.error(f"Create connection error: {str(e)}")
            raise

    def format_valid(self, data: Dict[str, Any]) -> ResponseValidateClarisa:
        """Format API response to consistent structure"""
        status = data.get("status", 0)
        if 200 <= status < 300:
            return ResponseValidateClarisa(data=data.get("response"), valid=True)

        return ResponseValidateClarisa(data=None, valid=False)
