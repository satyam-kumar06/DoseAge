"""Central configuration. Everything reads env vars so the same code runs
locally with no AWS credentials and unchanged inside Lambda."""
import os


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


# "aws" when running on Lambda, "local" for the offline dev server.
BACKEND = os.environ.get("DOSEWISE_BACKEND", "local").lower()
IS_AWS = BACKEND == "aws"

TABLE_NAME = os.environ.get("TABLE_NAME", "DoseWise")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "dosewise-local")
REGION = os.environ.get("AWS_REGION", "ap-south-1")
# boto3 can still sign a presigned URL against the legacy GLOBAL S3 host
# (bucket.s3.amazonaws.com) even when the credential scope is regional. For a
# bucket outside us-east-1 that host answers with a 307 redirect, and a
# redirect carries no CORS headers, so a browser PUT dies on the preflight.
# Pinning the regional endpoint is what keeps the upload working from a page.
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", f"https://s3.{REGION}.amazonaws.com")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", REGION)
BEDROCK_MODEL_ID = os.environ.get(
    # Read through the Converse API, so any Bedrock vision model works and this
    # is a deploy-time parameter. Which models an account can reach varies:
    # `aws bedrock list-inference-profiles` is the only reliable answer.
    "BEDROCK_MODEL_ID", "apac.amazon.nova-pro-v1:0"
)

SNS_ENABLED = _flag("SNS_ENABLED", "1" if IS_AWS else "0")
POLLY_ENABLED = _flag("POLLY_ENABLED", "1" if IS_AWS else "0")
TEXTRACT_ENABLED = _flag("TEXTRACT_ENABLED", "1" if IS_AWS else "0")
BEDROCK_ENABLED = _flag("BEDROCK_ENABLED", "1" if IS_AWS else "0")

# Demo mode collapses the 30 minute escalation waits to 30 seconds.
DEMO_MODE = _flag("DEMO_MODE", "0")
WAIT_FIRST_SECONDS = 30 if DEMO_MODE else 30 * 60
WAIT_SECOND_SECONDS = 30 if DEMO_MODE else 30 * 60

LOCAL_DB_PATH = os.environ.get(
    "LOCAL_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), ".local", "db.json")
)
LOCAL_FILES_PATH = os.environ.get(
    "LOCAL_FILES_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), ".local", "files")
)
DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data"),
)

# Confidence under this gets a "please check" tag in the review screen.
LOW_CONFIDENCE = float(os.environ.get("LOW_CONFIDENCE", "0.7"))

DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", "Asia/Kolkata")

# Slot clock times, used for scheduling and for the EventBridge cron rules.
SLOT_TIMES = {
    "MORNING": os.environ.get("SLOT_MORNING", "08:00"),
    "AFTERNOON": os.environ.get("SLOT_AFTERNOON", "14:00"),
    "NIGHT": os.environ.get("SLOT_NIGHT", "21:00"),
}
SLOT_ORDER = ["MORNING", "AFTERNOON", "NIGHT"]
