#!/usr/bin/env sh
set -eu

IMAGE="${IMAGE:-planesnitch:local}"
CONTAINER_NAME="${CONTAINER_NAME:-planesnitch}"
ROOT_DIR="$(pwd)"
CONFIG_PATH="$ROOT_DIR/config.yaml"
CSV_PATH="$ROOT_DIR/csv"

# grab the example config only if you don't already have one
if [ ! -f "$CONFIG_PATH" ]; then
  curl -sL \
    https://raw.githubusercontent.com/psyb0t/docker-planesnitch/main/config.yaml.example \
    -o "$CONFIG_PATH"
fi

# optional: download CSV watchlists for
# military/gov/police tracking
# (see Plane-Alert-DB section below)
mkdir -p csv
BASE=https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main
curl -sLo "$CSV_PATH/plane-alert-mil.csv" $BASE/plane-alert-mil.csv
curl -sLo "$CSV_PATH/plane-alert-gov.csv" $BASE/plane-alert-gov.csv
curl -sLo "$CSV_PATH/plane-alert-pol.csv" $BASE/plane-alert-pol.csv
curl -sLo "$CSV_PATH/plane-alert-civ.csv" $BASE/plane-alert-civ.csv
curl -sLo "$CSV_PATH/plane-alert-pia.csv" $BASE/plane-alert-pia.csv
curl -sLo "$CSV_PATH/plane-alert-db.csv"  $BASE/plane-alert-db.csv

if grep -Eq 'bot_token:\s*""|chat_id:\s*""' "$CONFIG_PATH"; then
  printf '%s\n' "warning: config.yaml still has blank Telegram credentials."
  printf '%s\n' "edit $CONFIG_PATH before expecting Telegram alerts."
fi

printf '%s\n' "starting $IMAGE as $CONTAINER_NAME"
printf '%s\n' "ui: http://localhost:8080/"

docker build -t "$IMAGE" "$ROOT_DIR"

# let it rip — mount config and csv watchlists
docker run \
  --rm \
  --name "$CONTAINER_NAME" \
  -p 8080:8080 \
  -v "$CONFIG_PATH:/app/config.yaml:ro" \
  -v "$CSV_PATH:/csv:ro" \
  "$IMAGE"
