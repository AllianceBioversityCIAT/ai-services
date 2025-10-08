import os
import csv
import json
from app.utils.logger.logger_util import get_logger
from app.utils.s3.upload_file_to_s3 import upload_file_to_s3

logger = get_logger()


def split_jsonl_to_individual_csv_files(jsonl_file_path):
    """Divide a JSONL file into individual CSV files"""
    
    with open(jsonl_file_path, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)

                indicator = data.get("indicator_acronym", "")
                year = data.get("year", "")
                table_type = data.get("table_type", "")
                phase_name = data.get("phase_name", "")

                content_str = ",".join([f'"{k}":"{v}"' for k, v in data.items() if v not in ("", None, [], {}, "Not Provided", "Not provided", "Not linked", "Not defined", "NA", "Not Applicable", "N/A")])

                file_name = f"{table_type}_record_{line_number}.csv"
                local_path = os.path.join(os.getcwd(), "csv_files", file_name)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                fieldnames = ["content", "year", "table_type"]
                row_data = {
                    "content": content_str,
                    "year": year,
                    "table_type": table_type
                }
                if indicator:
                    fieldnames.append("indicator_acronym")
                    row_data["indicator_acronym"] = indicator
                if phase_name:
                    fieldnames.append("phase_name")
                    row_data["phase_name"] = phase_name
                
                with open(local_path, 'w', encoding='utf-8', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerow(row_data)

                # Create metadata file
                metadata_file_name = f"{file_name}.metadata.json"
                metadata_local_path = os.path.join(os.getcwd(), "csv_files", metadata_file_name)
                os.makedirs(os.path.dirname(metadata_local_path), exist_ok=True)

                attributes = {
                    "year": year,
                    "table_type": table_type
                }
                if indicator:
                    attributes["indicator_acronym"] = indicator
                if phase_name:
                    attributes["phase_name"] = phase_name

                fields_to_include = [
                    {"fieldName": "year"},
                    {"fieldName": "table_type"}
                ]
                if indicator:
                    fields_to_include.append({"fieldName": "indicator_acronym"})
                if phase_name:
                    fields_to_include.append({"fieldName": "phase_name"})

                metadata = {
                    "metadataAttributes": attributes,
                    "documentStructureConfiguration": {
                        "type": "RECORD_BASED_STRUCTURE_METADATA",
                        "recordBasedStructureMetadata": {
                            "contentFields": [
                                {"fieldName": "content"}
                            ],
                            "metadataFieldsSpecification": {
                                "fieldsToInclude": fields_to_include,
                                "fieldsToExclude": []
                            }
                        }
                    }
                }

                with open(metadata_local_path, 'w', encoding='utf-8') as metafile:
                    json.dump(metadata, metafile, indent=2)

                file_key = f"aiccra/chatbot/knowledge_base/{table_type}/{file_name}"
                upload_file_to_s3(file_key, local_path)
                upload_file_to_s3(file_key + ".metadata.json", metadata_local_path)
                os.remove(local_path)
                os.remove(metadata_local_path)
                    
            except Exception as e:
                logger.error(f"Error processing line {line_number}: {e}")
                continue