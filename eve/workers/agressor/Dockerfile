FROM python:3.6

RUN pip install buildbot-worker

RUN apt-get update && apt-get install -y netcat

CMD ["/bin/sh", "-c", "buildbot-worker create-worker . ${BUILDMASTER}:${BUILDMASTER_PORT} ${WORKERNAME} ${WORKERPASS} && buildbot-worker start --nodaemon"]

