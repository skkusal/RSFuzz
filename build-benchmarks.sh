#! /bin/bash

rm -rf benchmark
mkdir benchmark
bases="RSFuzz Baseline Naive"
for base in $bases
do
    cp -r benchmark-srcs benchmark/${base}
    echo "Build ${base} jerryscript"
    cd benchmark/${base}/jerryscript && python3 tools/build.py --compile-flag "-fprofile-abs-path -fprofile-arcs -ftest-coverage" 1>/dev/null 2>/dev/null
    echo "Build ${base} jsish"
    cd ../jsish && make 1>/dev/null 2>/dev/null
    echo "Build ${base} quickjs"
    cd ../quickjs && make 1>/dev/null 2>/dev/null
    cd ..

    javabenchs="Rhino Argo Genson Gson JsonToJava"

    for pgm in $javabenchs
    do
        cp coverage-analyser.jar ${pgm}-analyser.jar
    done
    rm coverage-analyser.jar
    cd ../..
    echo "Complete ${base} benchmark build"
done