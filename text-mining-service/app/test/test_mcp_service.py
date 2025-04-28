import requests
import json
import time
import argparse
import os
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()


def process_document(bucket_name, file_key, token=None, request_id=None):
    """
    Process a single document through the text mining endpoint

    Args:
        bucket_name: The S3 bucket containing the document
        file_key: The path/key to the document in the S3 bucket
        token: Authentication token (will use env vars if not provided)
        request_id: Identifier for this request in concurrent processing

    Returns:
        Dictionary with results and performance metrics
    """
    # Use provided token or get from environment
    # auth_token = token or os.getenv("AUTH_TOKEN")

    # if not auth_token:
    #     raise ValueError(
    #         "Missing authentication token. Provide it as an argument or set AUTH_TOKEN env var")

    payload = {
        "bucketName": bucket_name,
        "key": file_key,
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MTMsImZpcnN0X25hbWUiOiJMdWxpdG8iLCJsYXN0X25hbWUiOiIxODkiLCJpYXQiOjE3NDU4NTk4MDMsImV4cCI6MTc0NTg2NzAwM30.8TRzSZqdEKpk1r7xR5Ezr9MU5RMRWd1wiWhq4RmRD-U"
    }

    base_url = os.getenv("MINING_SERVICE_URL", "http://0.0.0.0:8000")
    url = f"{base_url}/process"

    req_id = request_id if request_id is not None else 1
    print(f"🔍 [Request {req_id}] Testing endpoint: {url}")
    print(f"📄 [Request {req_id}] Document: {bucket_name}/{file_key}")

    start_time = time.time()

    try:
        print(f"📤 [Request {req_id}] Sending request...")
        response = requests.post(
            url, json=payload, timeout=300)  # 5-minute timeout

        time_taken = time.time() - start_time

        result = {
            "request_id": req_id,
            "bucket": bucket_name,
            "key": file_key,
            "status_code": response.status_code,
            "time_taken": time_taken,
            "success": response.status_code == 200,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"🔢 [Request {req_id}] Status code: {response.status_code}")

        if response.status_code == 200:
            print(
                f"✅ [Request {req_id}] Success! Time taken: {time_taken:.2f}s")

            try:
                response_data = response.json()

                timestamp = time.strftime("%Y%m%d_%H%M%S")
                doc_name = os.path.splitext(os.path.basename(file_key))[0]
                filename = f"mining_result_{doc_name}_{req_id}_{timestamp}.json"
                with open(filename, "w") as f:
                    json.dump(response_data, f, indent=2)
                print(f"💾 [Request {req_id}] Response saved to {filename}")

                result["data"] = response_data

            except json.JSONDecodeError:
                print(f"⚠️ [Request {req_id}] Response is not valid JSON")
                result["error"] = "Invalid JSON response"
                result["response_text"] = response.text[:500]

        else:
            print(f"❌ [Request {req_id}] Error! Time taken: {time_taken:.2f}s")
            result["error"] = "Request failed with non-200 status code"
            result["response_text"] = response.text[:500]

        return result

    except requests.exceptions.RequestException as e:
        time_taken = time.time() - start_time
        print(f"❌ [Request {req_id}] Request failed: {str(e)}")
        return {
            "request_id": req_id,
            "bucket": bucket_name,
            "key": file_key,
            "success": False,
            "time_taken": time_taken,
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


def run_multi_document_tests(documents, token=None):
    """
    Run requests for multiple documents simultaneously

    Args:
        documents: List of tuples (bucket_name, file_key) for each document
        token: Authentication token (will use env vars if not provided)
    """
    num_documents = len(documents)
    print(f"🚀 Starting tests for {num_documents} different documents...")
    start_time = time.time()

    args = [(bucket, key, token, i+1)
            for i, (bucket, key) in enumerate(documents)]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_documents) as executor:
        future_to_id = {
            executor.submit(process_document, *arg): arg[3] for arg in args
        }

        for future in concurrent.futures.as_completed(future_to_id):
            req_id = future_to_id[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"❌ [Request {req_id}] Error: {str(e)}")
                doc_info = next((d for i, d in enumerate(
                    documents) if i == req_id-1), None)
                results.append({
                    "request_id": req_id,
                    "bucket": doc_info[0] if doc_info else "unknown",
                    "key": doc_info[1] if doc_info else "unknown",
                    "success": False,
                    "error": str(e),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })

    total_time = time.time() - start_time

    success_count = sum(1 for r in results if r.get("success", False))
    failure_count = len(results) - success_count

    if results:
        avg_time = sum(r.get("time_taken", 0) for r in results) / len(results)
        min_time = min((r.get("time_taken", float('inf'))
                        for r in results), default=0)
        max_time = max((r.get("time_taken", 0) for r in results), default=0)
    else:
        avg_time = min_time = max_time = 0

    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    print(f"Total documents: {num_documents}")
    print(f"Successful requests: {success_count}")
    print(f"Failed requests: {failure_count}")
    print(f"Total time taken: {total_time:.2f}s")
    print(f"Average response time: {avg_time:.2f}s")
    print(f"Fastest response: {min_time:.2f}s")
    print(f"Slowest response: {max_time:.2f}s")
    print("="*50)

    for result in sorted(results, key=lambda r: r.get("time_taken", 0), reverse=True):
        status = "✅" if result.get("success", False) else "❌"
        time_taken = result.get("time_taken", 0)
        doc_key = result.get("key", "unknown")
        print(f"{status} {doc_key}: {time_taken:.2f}s")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    summary_file = f"multi_document_test_summary_{timestamp}.json"
    with open(summary_file, "w") as f:
        json.dump({
            "test_info": {
                "documents": [{"bucket": b, "key": k} for b, k in documents],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "summary": {
                "total_time": total_time,
                "success_count": success_count,
                "failure_count": failure_count,
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time
            },
            "results": results
        }, f, indent=2)

    print(f"💾 Test summary saved to {summary_file}")


def parse_document_list(doc_list):
    """
    Parse the document list from command line arguments
    Format: bucket1:key1,bucket2:key2,...
    """
    documents = []
    for doc_spec in doc_list.split(','):
        parts = doc_spec.strip().split(':')
        if len(parts) != 2:
            raise ValueError(
                f"Invalid document specification: {doc_spec}. Format should be bucket:key")
        bucket, key = parts
        documents.append((bucket, key))
    return documents


def run_predefined_tests():
    """
    Run predefined test cases with multiple documents
    """
    # Define your documents here
    test_documents = [
        ("microservice-mining", "Guatemala_Policy_Brief_2024-46-1745849681481.pdf")
    ]

    print("🧪 Running predefined test with test documents")
    print("📚 Documents to process:")
    for i, (bucket, key) in enumerate(test_documents, 1):
        print(f"  {i}. {bucket}/{key}")

    # Get token from environment variable
    token = os.getenv("AUTH_TOKEN")

    run_multi_document_tests(test_documents, token)


def run_same_document_concurrently(num_requests=5):
    """
    Run multiple concurrent requests for the same document
    """
    bucket_name = "microservice-mining"
    file_key = "Guatemala_Policy_Brief_2024-13-1745849915180"

    test_documents = [(bucket_name, file_key) for _ in range(num_requests)]

    print(
        f"🧪 Running concurrency test with {num_requests} simultaneous requests")
    print(f"📚 Document to process: {bucket_name}/{file_key}")

    # Get token from environment variable
    token = os.getenv("AUTH_TOKEN")

    run_multi_document_tests(test_documents, token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test the text mining microservice with multiple documents")

    mode_group = parser.add_mutually_exclusive_group(required=True)

    doc_group = parser.add_argument_group('document specification')

    doc_group.add_argument("--documents", "-d",
                           help="List of documents to process in format: bucket1:key1,bucket2:key2,...")

    doc_group.add_argument("--bucket", "-b",
                           help="S3 bucket name containing the documents")
    doc_group.add_argument("--keys", "-k",
                           help="Comma-separated list of document keys/paths in the S3 bucket")

    mode_group.add_argument("--predefined", "-p", action="store_true",
                            help="Run predefined test with example documents")

    mode_group.add_argument("--concurrency", "-n", type=int, metavar="NUM_REQUESTS",
                            help="Run concurrency test with multiple requests to same document")

    parser.add_argument("--token", "-t",
                        help="Authentication token (optional, can use env var AUTH_TOKEN)")

    args = parser.parse_args()

    # Get token from args or environment
    token = args.token or os.getenv("AUTH_TOKEN")

    if args.predefined:
        run_predefined_tests()
    elif args.concurrency:
        run_same_document_concurrently(args.concurrency)
    else:
        if args.documents:
            documents = parse_document_list(args.documents)
        elif args.bucket and args.keys:
            documents = [(args.bucket, key.strip())
                         for key in args.keys.split(',')]
        else:
            parser.error(
                "Either --documents or both --bucket and --keys are required when not using --predefined or --concurrency")

        run_multi_document_tests(
            documents=documents,
            token=token
        )
