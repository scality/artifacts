# Artifacts Tests

## Execute

Assuming you have docker installed on your machine. To run the tests locally just do:

```shell
$ ./run.sh
```

If you want to debug your tests or add parameters to pytest, all arguments sent to
the `run.sh` script are transfered to pytest. Example:

```shell
# to debug your test
$ ./run.sh --pdb
# to run a single test
$ ./run.sh -k test_name
```
