import argparse
import os
import subprocess

benchmark_dir = os.path.abspath("./benchmark/Baseline")
print(benchmark_dir)

def run_baseline_test(opt):
    if not os.path.isdir(opt.result_dir):
        os.makedirs(opt.result_dir)
    if os.path.isdir(os.path.join(opt.result_dir, "capture_data")): 
        os.system("rm -rf " + os.path.join(opt.result_dir, "capture_data"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "coverage"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "captured_clusters"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "error"))
    if os.path.isdir(os.path.join(opt.result_dir, "test_data")):
        os.system("rm -rf " + os.path.join(opt.result_dir, "test_data"))
    os.mkdir(os.path.join(opt.result_dir, "test_data"))

    if opt.benchmark in ["JerryScript", "Jsish", "QuickJS"] and (opt.test_dir is None or opt.test_pgm is None):
        print("Please input test directory and program")
        exit(1)

    if opt.benchmark in ["JerryScript", "Jsish", "QuickJS"]:
        file_extension = "js"
        test_pgm = opt.test_pgm
    else:
        file_extension = "json"
        test_pgm = "java"

    if opt.benchmark == "Rhino":
        file_extension = "js"

    subprocess.call(
        f"timeout {str(opt.test_time)} python3 scripts/testing.py --benchmark {opt.benchmark} --fileExtension {file_extension} --base_fuzzer {opt.base_fuzzer} --list_dir {os.path.join(opt.result_dir, 'capture_data')} --result_dir {os.path.join(opt.result_dir, 'test_data')} --n_num {str(opt.n_num)} --test_dir {opt.test_dir} --test_pgm {test_pgm}",
        shell=True,
        stderr=subprocess.STDOUT,
    )  
    print("Baseline test finished")
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Options for Baseline fuzzers", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--benchmark",
        dest="benchmark",
        help="Available benchmark: JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava",
    )
    parser.add_argument(
        "--base_fuzzer",
        dest="base_fuzzer",
        help="random or prob",
    )
    parser.add_argument(
        "--test_time",
        dest="test_time",
        type=int,
        default=86400,
        help="Test time(sec) (Default: 43200 = 12h)",
    )
    parser.add_argument(
        "--result_dir",
        dest="result_dir",
        default="baseline_results",
        help="Result directory (Default: baseline_results)",
    )
    parser.add_argument(
        "--n_num",
        dest="n_num",
        type=int,
        default=3000,
        help="Hyperparameter to hanlde # of input generation in a iteration (Default: 2000)",
    )

    options = parser.parse_args()

    if options.benchmark is None or options.benchmark not in "JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava":
        print("Please input available benchmark name\nAvailable benchmarks : JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava")
        exit(1)
        
    options.result_dir = os.path.abspath(options.result_dir)

    if options.benchmark == "QuickJS":
        options.test_pgm = f"{benchmark_dir}/quickjs/qjs"
        options.test_dir = f"{benchmark_dir}/quickjs"
    elif options.benchmark == "JerryScript":
        options.test_pgm = f"{benchmark_dir}/jerryscript/build/bin/jerry"
        options.test_dir = f"{benchmark_dir}/jerryscript/build"
    elif options.benchmark == "Jsish":
        options.test_pgm = f"{benchmark_dir}/jsish/jsish"
        options.test_dir = f"{benchmark_dir}/jsish"
    else:
        options.test_pgm = "java"
        options.test_dir = f"{benchmark_dir}/{options.benchmark}-analyser.jar"
    
    print("target program :", options.test_pgm)
    print("Dir of target program :", options.test_dir)

    run_baseline_test(options)
