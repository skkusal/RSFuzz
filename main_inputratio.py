import argparse
import os
import subprocess

benchmark_dir = os.path.abspath("./benchmark")
print(benchmark_dir)

def run_rsfuzz(opt):
    if not os.path.isdir(opt.result_dir):
        os.makedirs(opt.result_dir)
    if os.path.isdir(os.path.join(opt.result_dir, "capture_data")):
        os.system("rm -rf " + os.path.join(opt.result_dir, "capture_data"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "coverage"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "unique_covs"))
    if os.path.isdir(os.path.join(opt.result_dir, "test_data")):
        os.system("rm -rf " + os.path.join(opt.result_dir, "test_data"))
    os.mkdir(os.path.join(opt.result_dir, "test_data"))

    if opt.benchmark in ["JerryScript", "Jsish", "QuickJS"] and (
        opt.test_dir is None or opt.test_pgm is None
    ):
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
        f"python3 scripts/input_ratio.py --benchmark {opt.benchmark} --fileExtension {file_extension} --base_fuzzer {opt.base_fuzzer} --list_dir {os.path.join(opt.result_dir, 'capture_data')} --result_dir {os.path.join(opt.result_dir, 'test_data')} --n_test_inputs {opt.n_test_inputs} --test_dir {opt.test_dir} --test_pgm {test_pgm} --redundant_sequence {opt.redundant_sequence}",
        shell=True,
        stderr=subprocess.STDOUT,
    )  
    print("RSFuzz test finished")
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Options for RSFuzz", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--benchmark",
        dest="benchmark",
        help="Available benchmarks: JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava",
    )
    parser.add_argument(
        "--base_fuzzer",
        dest="base_fuzzer",
        help="random or prob",
    )
    parser.add_argument(
        "--redundant_sequence",
        dest="redundant_sequence",
        default="None",
        help="file path of redundant sequence",
    )
    parser.add_argument(
        "--n_test_inputs",
        dest="n_test_inputs",
        type=int,
        default=100000,
        help="# of inputs to measure covered line set (Default: 100000)",
    )
    parser.add_argument(
        "--result_dir",
        dest="result_dir",
        default="results_inputratio",
        help="Result directory (Default: results_inputratio)",
    )
    parser.add_argument(
        "--n_num",
        dest="n_num",
        type=int,
        default=2000,
        help="Hyperparameter to hanlde # of inputs generation in a iteration (Default: 2000)",
    )

    options = parser.parse_args()

    if options.benchmark is None or options.benchmark not in "JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava":
        print("Please input available benchmark name\nAvailable benchmarks : JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava")
        exit(1)

    if options.base_fuzzer is None or options.base_fuzzer not in "random prob":
        print("Please input available base fuzzer name : random or prob")
        exit(1)

    options.result_dir = os.path.abspath(f"{options.result_dir}/{options.base_fuzzer}/{options.benchmark}")
    
    if options.benchmark == "QuickJS":
        options.test_pgm = f"{benchmark_dir}/{options.base_fuzzer}/quickjs/qjs"
        options.test_dir = f"{benchmark_dir}/{options.base_fuzzer}/quickjs"
    elif options.benchmark == "JerryScript":
        options.test_pgm = f"{benchmark_dir}/{options.base_fuzzer}/jerryscript/build/bin/jerry"
        options.test_dir = f"{benchmark_dir}/{options.base_fuzzer}/jerryscript/build"
    elif options.benchmark == "Jsish":
        options.test_pgm = f"{benchmark_dir}/{options.base_fuzzer}/jsish/jsish"
        options.test_dir = f"{benchmark_dir}/{options.base_fuzzer}/jsish"
    else:
        options.test_pgm = "java"
        options.test_dir = f"{benchmark_dir}/{options.benchmark}-analyser.jar"
    
    print("target program :", options.test_pgm)
    print("Dir of target program :", options.test_dir)

    run_rsfuzz(options)
