"""Writes suggestions and run counters in the ElectroDB-compatible format.

One transaction per job: put the suggestion only if its key does not exist, and ADD 1 to the run
counter. A duplicate delivery fails the condition, so nothing is written and nothing is counted
twice: the counters stay exact under SQS at-least-once delivery.

A stored ``unavailable/failed`` item is the only one that can be replaced: re-enqueuing the job
overwrites it (condition: still failed) and moves its count from ``failed`` to the new counter in
the same transaction.
"""

from typing import Any, Literal, Protocol

from boto3.dynamodb.types import TypeSerializer

from app.contract.items import (
    ELECTRODB_ENTITY_RUN,
    ELECTRODB_VERSION,
    RUN_SK,
    AiSuggestionItem,
    run_pk,
)

Counter = Literal["produced", "unavailable", "failed"]
Existing = Literal["absent", "done", "failed"]

_ser = TypeSerializer()


class SuggestionStore(Protocol):
    def lookup(self, pk: str, sk: str) -> Existing: ...

    def write(self, item: AiSuggestionItem, counter: Counter, replaces_failed: bool = False) -> bool:
        """False when the condition fails (duplicate delivery or a concurrent writer): nothing written."""
        ...


def _av(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: _ser.serialize(v) for k, v in doc.items()}


class DynamoSuggestionStore:
    def __init__(self, table: str, client: Any):
        self._table = table
        self._client = client

    def lookup(self, pk: str, sk: str) -> Existing:
        resp = self._client.get_item(
            TableName=self._table,
            Key={"pk": {"S": pk}, "sk": {"S": sk}},
            ProjectionExpression="pk, unavailableReason",
            ConsistentRead=True,
        )
        item = resp.get("Item")
        if not item:
            return "absent"
        return "failed" if item.get("unavailableReason", {}).get("S") == "failed" else "done"

    def write(self, item: AiSuggestionItem, counter: Counter, replaces_failed: bool = False) -> bool:
        doc = item.model_dump(by_alias=True, exclude_none=True)
        put: dict[str, Any] = {"TableName": self._table, "Item": _av(doc)}
        update = "ADD #c :one SET #e = if_not_exists(#e, :e), #v = if_not_exists(#v, :v), #r = if_not_exists(#r, :r)"
        names = {"#c": counter, "#e": "__edb_e__", "#v": "__edb_v__", "#r": "runId"}
        values = {":one": 1, ":e": ELECTRODB_ENTITY_RUN, ":v": ELECTRODB_VERSION, ":r": item.runId}
        if replaces_failed:
            put["ConditionExpression"] = "unavailableReason = :failed"
            put["ExpressionAttributeValues"] = _av({":failed": "failed"})
            if counter != "failed":
                update = update.replace("ADD #c :one", "ADD #c :one, #f :minus")
                names["#f"] = "failed"
                values[":minus"] = -1
        else:
            put["ConditionExpression"] = "attribute_not_exists(pk)"
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {"Put": put},
                    {
                        "Update": {
                            "TableName": self._table,
                            "Key": _av({"pk": run_pk(item.runId), "sk": RUN_SK}),
                            "UpdateExpression": update,
                            "ExpressionAttributeNames": names,
                            "ExpressionAttributeValues": _av(values),
                        }
                    },
                ]
            )
        except self._client.exceptions.TransactionCanceledException as err:
            reasons = err.response.get("CancellationReasons") or []
            if reasons and reasons[0].get("Code") == "ConditionalCheckFailed":
                return False
            raise
        return True
