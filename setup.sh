THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

POTENTIAL_VENV="$THIS_DIR/venv"
if [ -z "$VIRTUAL_ENV" ] && [ -d "$POTENTIAL_VENV" ]; then
    . "$POTENTIAL_VENV/bin/activate"
fi
unset POTENTIAL_VENV
