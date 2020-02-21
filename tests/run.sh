#!/bin/bash

SCRIPT_FULL_PATH=$(readlink -f "$0")
TEST_DIR=$(dirname "${SCRIPT_FULL_PATH}")
PYTEST_ARGS="$@"



source "${TEST_DIR}/.env"

# Build dependencies
docker build -t artifacts:latest "${TEST_DIR}/.."
docker build -t artifacts-end2end:latest "${TEST_DIR}"

# Start cloudserver and artifacts
docker run -d --rm -p 8000:8000 --name cloudserver --env REMOTE_MANAGEMENT_DISABLE=1 --env LOG_LEVEL=debug --env ENDPOINT="cloudserver-front" zenko/cloudserver:8.1.2 yarn start
docker run -d --name artifacts --link=cloudserver:cloudserver-front  -p 5000:80 --rm --env-file=.env artifacts

# Run tests
docker run -it -v ${TEST_DIR}:/home/workspace --rm --env-file=.env --link=cloudserver:cloudserver-front --link=artifacts:artifacts artifacts-end2end pytest ${PYTEST_ARGS}

EXIT=$?

docker logs artifacts >> ${TEST_DIR}/.artifacts.log 2>&1
docker logs cloudserver >> ${TEST_DIR}/.cloudserver.log 2>&1

docker kill cloudserver artifacts

exit ${EXIT}
