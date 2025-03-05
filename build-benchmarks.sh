#! /bin/bash

rm -rf benchmark
cp -r benchmark-srcs benchmark
echo "Build jerryscript"
cd benchmark/jerryscript && python3 tools/build.py --compile-flag "-fprofile-abs-path -fprofile-arcs -ftest-coverage" 1>/dev/null 2>/dev/null
echo "Build jsish"
cd ../jsish && make 1>/dev/null 2>/dev/null
echo "Build quickjs"
cd ../quickjs && make 1>/dev/null 2>/dev/null
cd ..

benchmarks="Rhino Argo Genson Gson JsonToJava"

for pgm in $benchmarks
do
    cp coverage-analyser.jar ${pgm}-analyser.jar
done
rm coverage-analyser.jar
echo "Complete benchmark build"