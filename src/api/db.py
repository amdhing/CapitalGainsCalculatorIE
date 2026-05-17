"""DynamoDB Local client for storing calculation history and results."""

import os
import time
import json
from decimal import Decimal, InvalidOperation
from typing import Optional, Any

import boto3
from botocore.config import Config

# DynamoDB Local endpoint (runs on Raspberry Pi)
DYNAMODB_ENDPOINT = os.environ.get(
    "DYNAMODB_ENDPOINT", "http://raspberrypi.local:8000"
)
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "capital-gains-calculations")
BACKLOG_TABLE_NAME = os.environ.get("DYNAMODB_BACKLOG_TABLE", "ticker-backlog")

config = Config(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=3,
    read_timeout=5,
)

client = boto3.resource(
    "dynamodb",
    endpoint_url=DYNAMODB_ENDPOINT,
    region_name="eu-west-1",
    aws_access_key_id="local",
    aws_secret_access_key="local",
    config=config,
)

# Will be set to the DynamoDB table reference if connection succeeds
table = None
backlog_table = None


def _float_to_decimal(obj: Any) -> Any:
    """Recursively convert all float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        try:
            return Decimal(str(obj))
        except InvalidOperation:
            return Decimal("0")
    elif isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_float_to_decimal(v) for v in obj]
    return obj


def ensure_table_exists():
    """Create the DynamoDB table if it doesn't exist."""
    global table
    try:
        table = client.Table(TABLE_NAME)
        table.load()
        return table
    except Exception:
        print("Warning: Could not connect to DynamoDB: table '{}' not available".format(TABLE_NAME))
        print("Calculations will not be persisted until DynamoDB is available.")
        table = None
        return None


def ensure_backlog_table_exists():
    """Ensure the ticker backlog DynamoDB table exists."""
    global backlog_table
    try:
        backlog_table = client.Table(BACKLOG_TABLE_NAME)
        backlog_table.load()
        return backlog_table
    except Exception:
        print("Warning: Could not connect to DynamoDB: backlog table '{}' not available".format(BACKLOG_TABLE_NAME))
        print("Ticker backlog will not be stored until DynamoDB is available.")
        backlog_table = None
        return None


# Attempt to connect on module load
ensure_table_exists()
ensure_backlog_table_exists()


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def is_available() -> bool:
    """Check if DynamoDB is available."""
    return table is not None


def save_result(
    calculation_id: str,
    input_data: dict,
    results: dict,
    user_id: Optional[str] = None,
):
    """Save a calculation result to DynamoDB."""
    if table is None:
        print("Warning: DynamoDB not available, result not saved")
        return

    # Convert all float values to Decimal for DynamoDB compatibility
    item = {
        "id": calculation_id,
        "timestamp": int(time.time()),
        "input": _float_to_decimal(input_data),
        "results": _float_to_decimal(results),
    }
    if user_id:
        item["user_id"] = user_id
    table.put_item(Item=item)


def get_result(calculation_id: str) -> Optional[dict]:
    """Retrieve a calculation result by ID."""
    if table is None:
        return None
    try:
        response = table.get_item(Key={"id": calculation_id})
        return response.get("Item")
    except Exception:
        return None


def list_results(
    limit: int = 20, user_id: Optional[str] = None
) -> list[dict]:
    """List recent calculation results."""
    if table is None:
        return []
    try:
        if user_id:
            response = table.scan(
                FilterExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id},
                Limit=limit,
            )
        else:
            response = table.scan(Limit=limit)
        return response.get("Items", [])
    except Exception:
        return []


# --- Ticker backlog ---

def add_to_backlog(ticker: str, app_source: str = "unknown"):
    """Add or update a ticker in the backlog.

    If the ticker already exists, increments the encounter_count
    and updates last_seen. Otherwise creates a new entry.
    """
    if backlog_table is None:
        print("Warning: Backlog not available, ticker '{}' not stored".format(ticker))
        return False
    now = int(time.time())
    try:
        backlog_table.update_item(
            Key={"ticker": ticker.upper()},
            UpdateExpression="""
                SET #status = :status,
                    app_source = :app_source,
                    last_seen = :now,
                    encounter_count = if_not_exists(encounter_count, :one)
                """,
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "unresolvable",
                ":app_source": app_source,
                ":now": now,
                ":one": 1,
            },
        )
        # For first creation, also set the original timestamp
        backlog_table.update_item(
            Key={"ticker": ticker.upper()},
            UpdateExpression="SET #ts = if_not_exists(#ts, :now)",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={":now": now},
        )
        return True
    except Exception as e:
        print("Warning: Failed to update backlog for ticker '{}': {}".format(ticker, e))
        return False


def add_to_backlog_atomic(ticker: str, app_source: str = "unknown"):
    """Atomically add or update a ticker in the backlog.

    Uses a single update_item call with ADD on the counter and
    SET for the other fields, ensuring this is thread-safe.
    Increments encounter_count by 1 each time a customer run hits it.
    Sets last_seen to current time.
    Sets timestamp on first creation (if_not_exists).
    """
    if backlog_table is None:
        print("Warning: Backlog not available, ticker '{}' not stored".format(ticker))
        return False
    now = int(time.time())
    try:
        backlog_table.update_item(
            Key={"ticker": ticker.upper()},
            UpdateExpression="""
                SET #status = :status,
                    app_source = :app_source,
                    last_seen = :now,
                    #timestamp = if_not_exists(#timestamp, :now)
                ADD encounter_count :one
            """,
            ExpressionAttributeNames={
                "#status": "status",
                "#timestamp": "timestamp",
            },
            ExpressionAttributeValues={
                ":status": "unresolvable",
                ":app_source": app_source,
                ":now": now,
                ":one": 1,
            },
        )
        return True
    except Exception as e:
        print("Warning: Failed to update backlog for ticker '{}': {}".format(ticker, e))
        return False


def is_backlogged(ticker: str) -> bool:
    """Check if a ticker is already in the unresolvable backlog."""
    if backlog_table is None:
        return False
    try:
        response = backlog_table.get_item(Key={"ticker": ticker.upper()})
        return "Item" in response
    except Exception:
        return False


PARSE_ERRORS_TABLE_NAME = os.environ.get(
    "DYNAMODB_PARSE_ERRORS_TABLE", "parse-errors"
)

parse_errors_table = None


def ensure_parse_errors_table_exists():
    """Ensure the parse errors DynamoDB table exists."""
    global parse_errors_table
    try:
        parse_errors_table = client.Table(PARSE_ERRORS_TABLE_NAME)
        parse_errors_table.load()
        return parse_errors_table
    except Exception:
        print("Warning: Could not connect to DynamoDB: parse errors table '{}' not available".format(PARSE_ERRORS_TABLE_NAME))
        print("Parse errors will not be persisted until DynamoDB is available.")
        parse_errors_table = None
        return None


ensure_parse_errors_table_exists()


def add_parse_error(calculation_id: str, row: dict):
    """Persist a skipped/unparseable row for later inspection.

    The row dict is stored with a timestamp, the calculation_id it came from,
    and the skip reason so operators can inspect and fix the source data.
    """
    if parse_errors_table is None:
        return False
    now = int(time.time())
    error_id = f"{calculation_id}_{now}_{hash(str(row)) % (10**8)}"
    try:
        parse_errors_table.put_item(Item={
            "id": error_id,
            "calculation_id": calculation_id,
            "timestamp": now,
            "row": _float_to_decimal(row),
        })
        return True
    except Exception as e:
        print("Warning: Failed to store parse error: {}".format(e))
        return False


def list_parse_errors(limit: int = 50) -> list[dict]:
    """List recent parse errors for inspection."""
    if parse_errors_table is None:
        return []
    try:
        response = parse_errors_table.scan(Limit=limit)
        return response.get("Items", [])
    except Exception:
        return []


def list_backlog() -> list[dict]:

    """List all unresolved tickers in the backlog."""
    if backlog_table is None:
        return []
    try:
        response = backlog_table.scan()
        return response.get("Items", [])
    except Exception:
        return []
