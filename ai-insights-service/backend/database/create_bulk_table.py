import boto3
from app.utils.config.config_util import AWS
from app.utils.logger.logger_util import get_logger

logger = get_logger()


dynamodb = boto3.resource('dynamodb', region_name=AWS.get('region', 'us-east-1'))
BULK_UPLOAD_TABLE_NAME = 'bulk_upload_records'


def create_bulk_upload_table_if_not_exists():
    """
    Create the bulk_upload_records table in DynamoDB if it doesn't exist.
    """
    try:
        # Check if table exists
        existing_tables = [table.name for table in dynamodb.tables.all()]
        
        if BULK_UPLOAD_TABLE_NAME in existing_tables:
            logger.info(f"Table {BULK_UPLOAD_TABLE_NAME} already exists")
            return
        
        # Create table
        table = dynamodb.create_table(
            TableName=BULK_UPLOAD_TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'fileName',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'fileName',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        logger.info(f"✅ Table {BULK_UPLOAD_TABLE_NAME} created successfully")
        
    except Exception as e:
        logger.error(f"Error creating table {BULK_UPLOAD_TABLE_NAME}: {str(e)}")
        raise