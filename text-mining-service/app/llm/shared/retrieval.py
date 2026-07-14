from app.utils.logger.logger_util import get_logger
from langchain_text_splitters import RecursiveCharacterTextSplitter


logger = get_logger()


def split_text(text):
    logger.info("✂️  Dividing the text into fragments...")
    
    if isinstance(text, dict) and text.get("type") == "excel":
        logger.info(f"📊 Using Excel rows as chunks: {len(text['chunks'])} rows")
        return text["chunks"]
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=8000, chunk_overlap=1500)
    return text_splitter.split_text(text)