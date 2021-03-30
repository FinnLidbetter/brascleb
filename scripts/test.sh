#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SLOBSTERBLE_ROOT="$(dirname "$DIR")"

POSITIONAL_ARGS=()
RECREATE_DB=false

while [[ $# -gt 0 ]]
do
  key="$1"
  case $key in
    -b|--recreate-db)
    RECREATE_DB=true
    shift
    ;;
    *)
    POSITIONAL_ARGS+=("$1")
    shift
    ;;
  esac
done
set -- "${POSITIONAL_ARGS[@]}"

if [[ "$RECREATE_DB" = true ]] ; then
  echo "Recreating the test database."
  cd "$SLOBSTERBLE_ROOT"
  echo "Deleting the test database"
  rm instance/slobsterble_test.sqlite
  echo "Upgrading to head..."
  env TESTING=True flask db upgrade
fi
echo "Running:"
echo "  pytest $@"
pytest "$@"