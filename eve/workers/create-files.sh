#!/bin/bash
dd if=/dev/urandom of=file bs=1M count=100



for ((i=0;i<100;i++));
do
    cat file >> file
done
