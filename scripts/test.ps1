# Run the pytest suite inside the api container.
$ErrorActionPreference = 'Stop'

docker compose run --rm api pytest @args
