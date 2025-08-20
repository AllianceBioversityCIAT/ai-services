import os
import json
from app.utils.logger.logger_util import get_logger
from app.utils.s3.upload_file_to_s3 import s3_file_exists, upload_file_to_s3

logger = get_logger()

def split_jsonl_to_individual_files(jsonl_file_path, output_dir):
    """Divide a JSONL file into individual JSON files"""
    
    with open(jsonl_file_path, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)

                data = {k: v for k, v in data.items() if v not in ("", None, [], {})}
                
                file_name = f"{output_dir}_record_{line_number}.json"
                local_path = os.path.join("/tmp", file_name)
                
                with open(local_path, 'w', encoding='utf-8') as out_f:
                    json.dump(data, out_f, ensure_ascii=False, indent=2)

                file_key = f"aiccra/generator/knowledge_base/{output_dir}/{file_name}"
                # if not s3_file_exists(file_key):
                upload_file_to_s3(file_key, local_path)
                os.remove(local_path)
                    
            except Exception as e:
                logger.error(f"Error processing line {line_number}: {e}")
                continue