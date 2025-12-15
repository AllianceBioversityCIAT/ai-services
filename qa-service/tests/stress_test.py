import json
import asyncio
import httpx
import time

URL = "https://dj3rjcpfvsiytr7ydjhmlc7ho40wglws.lambda-url.us-east-1.on.aws/api/prms-qa"
CONCURRENCY = 100


async def send_request(client, data):
    try:
        res = await client.post(URL, json=data)
        return {
            "ok": res.status_code < 400,
            "status": res.status_code,
        }
    except httpx.HTTPStatusError as err:
        return {
            "ok": False,
            "status": err.response.status_code,
            "message": str(err),
        }
    except (httpx.ReadTimeout, httpx.ConnectError, httpx.HTTPError) as err:
        return {
            "ok": False,
            "status": None,
            "message": f"{type(err).__name__}: {str(err)}",
        }
    except Exception as err:
        return {
            "ok": False,
            "status": None,
            "message": f"Unexpected error: {type(err).__name__}: {str(err)}",
        }


async def main():
    with open("./data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    async with httpx.AsyncClient(timeout=7200) as client:
        tasks = [send_request(client, data) for _ in range(CONCURRENCY)]

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        end = time.perf_counter()

    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count
    
    status_counts = {}
    for r in results:
        status = r.get("status")
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"\n{'='*50}")
    print(f"STRESS TEST RESULTS")
    print(f"{'='*50}")
    print(f"Total requests: {len(results)}")
    print(f"Success (2xx): {ok_count}")
    print(f"Failed: {fail_count}")
    print(f"Time elapsed: {end - start:.2f}s")
    print(f"\nStatus code breakdown:")
    for status in sorted(status_counts.keys(), key=lambda x: (x is None, x)):
        count = status_counts[status]
        pct = (count / len(results)) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")
    print(f"{'='*50}\n")
    
    errors = [r for r in results if not r["ok"]]
    if errors:
        print(f"Sample errors (first 5):")
        for i, err in enumerate(errors[:5], 1):
            print(f"  {i}. Status {err['status']}: {err.get('message', 'No message')}")


if __name__ == "__main__":
    asyncio.run(main())