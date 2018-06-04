# Start the artifacts download failure

##  Build

```shell
# build and push your image into the registry
$ docker build . -t gcr.io/eve-dev-174712/artifacts-test:1.0 && docker push gcr.io/eve-dev-174712/artifacts-test:1.0
```

This image has already been pushed into the registry as it follow, so you can execute the next command,
it will work. In case you need to change the code you'll need to execute it.

## Deploy

```shell
# deploy the kube deployment.yml

$ kubectl apply -f deploy.yaml
```

## Watch

Go into stackdriver logging UI on google and start streaming all the logs related to your deployment with a filter on errors/ curl error 56.
You'll see they should appear.

Click on this [link](https://console.cloud.google.com/logs/viewer?project=eve-dev-174712&organizationId=384653579524&minLogLevel=0&expandAll=false&timestamp=2018-06-01T06:16:06.087000000Z&customFacets=&limitCustomFacetWidth=true&interval=PT1H&resource=container%2Fcluster_name%2Feve-dev%2Fnamespace_id%2Fgithub-scality-zenko-releng-julien&scrollTimestamp=2018-06-01T06:17:44.000000000Z&logName=projects%2Feve-dev-174712%2Flogs%2Fdownload&filters=text:peer&dateRangeStart=2018-06-01T05:18:54.492Z&dateRangeEnd=2018-06-01T06:18:54.492Z)

and press play


## Not working?

If you have 404 http erros the artifacts might be deleted, find a new one change the link in `run.sh` and try again.
