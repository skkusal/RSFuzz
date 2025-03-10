#! /bin/bash

rm -rf naive-benchmark
mkdir naive-benchmark
approaches="naive select capture"
bases="random prob"

for approach in $approaches
do
    mkdir naive-benchmark/${approach}
    for base in $bases
    do  
        cp -r benchmark-srcs naive-benchmark/${approach}/${base}
        echo "Build ${approach} ${base} jerryscript"
        cd naive-benchmark/${approach}/${base}/jerryscript && python3 tools/build.py --compile-flag "-fprofile-abs-path -fprofile-arcs -ftest-coverage" 1>/dev/null 2>/dev/null
        echo "Build ${approach} ${base} jsish"
        cd ../jsish && make 1>/dev/null 2>/dev/null
        echo "Build ${approach} ${base} quickjs"
        cd ../quickjs && make 1>/dev/null 2>/dev/null
        cd ..

        javabenchs="Rhino Argo Genson Gson JsonToJava"

        for pgm in $javabenchs
        do
            cp coverage-analyser.jar ${pgm}-analyser.jar
        done
        rm coverage-analyser.jar
        cd ../../..
        echo "Complete ${base} benchmark build"
    done
done