#! /bin/bash

rm -rf benchmark

cp -r benchmark-srcs benchmark
echo "Build ${approach} ${base} jerryscript"
cd benchmark/jerryscript && python3 tools/build.py --compile-flag "-fprofile-abs-path -fprofile-arcs -ftest-coverage" 1>/dev/null 2>/dev/null
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
cd ..
echo "Complete ${base} benchmark build"