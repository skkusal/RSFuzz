# RSFuzz

RSFuzz is a tool designed to minimize coverage-equivalent input generation in grammar-based fuzzing. It automatically identifies main causes of redundancy and guides the base fuzzer to avoid them, improving efficiency and effectiveness.

## Installation

We recommend using a Docker image for quick and easy installation. For more details about the installation process, please check `Dockerfile`.

```bash
$ docker pull anonymrsfuzz/rsfuzz:v1.1
$ docker run --rm -it anonymrsfuzz/rsfuzz:v1.1
```

## Benchmarks

In the docker image, all 12 benchmarks we used are installed in 'root/rsfuzz/benchmark'. Details of benchmarks are as follows:
![benchmark_table](./Benchmarks.png)

## How to run RSFuzz

You can run RSFuzz and baseline fuzzers with the following commands in the 'root/rsfuzz/main' directory. There are two required arguments:`benchmark` (target program) and `base_fuzzer` (`random`, `prob`, or `tribble`).

```bash
# At rsfuzz/main
# Run RSFuzz
$ python3 runRSFuzz.py --benchmark Gson --basefuzzer random
# Run baselines
$ python3 runRSFuzz.py --baseline-only --benchmark Gson --basefuzzer random
# Run fuzzer with recurrent sequences
$ python3 runRSFuzz.py --benchmark Gson --basefuzzer random --prepared-RS {path/to/recurrent-sequence}
```

The results will be saved in the `{result_dir}/{benchmark}/captured_data` dicrectory. RSFuzz generates 4 main outputs:
1. Recurrent sequences : `recurrent_sequence.pickle` file
2. Test logs : `logs.txt` file
3. Error cases and their derivation trees : `error/*` files
4. Coverage results : `total_coverage.pickle` file

## Additional Experiments

We also provied some additional approaches: naive versions of RSFuzz
- **naive**: RSFuzz without `Select` and `Capture`
- **select**: RSFuzz without `Capture`
- **capture**: RSFuzz without `Select`

You can execute these experiments with the following commands in the 'root/rsfuzz/main' directory:
```bash
# At rsfuzz/main
# run naive: RSFuzz - (Select, Capture) approaches
$ python3 runNaive.py --benchmark Gson --basefuzzer random --naive_version naive
# run select: RSFuzz - (Capture) approaches
$ python3 runNaive.py --benchmark Gson --basefuzzer random --naive_version select
# run capture: RSFuzz - (Select) approaches
$ python3 runNaive.py --benchmark Gson --basefuzzer random --naive_version capture
```

To check the coverage-equivalent input ratio, you can run the following command. If you omit the `recurrent_sequence` argument, the experiment will run for baseline fuzzers.

```bash
# Check the coverage-equivalent input ratio (Default: 100,000 inputs)
$ python3 runRatio.py --benchmark Gson --basefuzzer random --recurrent_sequence {path/to/recurrent_sequence.pickle}
```

## Details

For more details about arguments, you can use `--help` commands:

```bash
$python3 main_rsfuzz.py --help
usage: main_rsfuzz.py [options]

Options:
  -h, --help            show this help message and exit
  --benchmark=BENCHMARK
                        Available benchmark: JerryScript, Jsish, QuickJS,
                        Rhino, Argo, Genson, Gson, JsonToJava, jackson-
                        dataformat-csv, super-csv, commonmark, txtmark
  --basefuzzer=BASEFUZZER
                        Base Fuzzer : [random, pcfg, tribble]
  --baseline-only       Run baseline fuzzer without RSFuzz
  --prepared-RS=PREPARED_RS
                        Run fuzzer with prepared recurrent sequence
  --capture_time=CAPTURE_TIME
                        Recurrent sequence generation time(sec) (Default:
                        43200 = 12h)
  --test_time=TEST_TIME
                        Base fuzzer testing time(sec) (Default: 43200 = 12h)
  --result_dir=RESULT_DIR
                        Result directory (Default:
                        results/{basefuzzer}-{benchmark})
  --n_num=N_NUM         Hyperparameter to hanlde n of input generation in a
                        iteration (Default: 2000)
  --test_dir=TEST_DIR   Directory to capture coverage data (Required to test
                        JerryScript, Jsish, or QuickJS)
  --test_pgm=TEST_PGM   Program to run (Required to test JerryScript, Jsish,
                        or QuickJS)
```

## Bug-finding results

Since coverage results are stored in output files, we only provide a Python file, `errorCheck.py`, to check bug-finding results. There are two required arguments: `benchmark` (target program) and `inputs_dir` (e.g., `*/capture_data/error`).
```bash
# At rsfuzz/main
$ python3 errorCheck.py --benchmark Gson --inputs_dir results/argo/captured_data/error
Exception Type                                    N uniques
java.lang.ClassCastException                      3
java.lang.IllegalArgumentException                10
Detail reports : rsfuzz_results/random/argo/captured_data/error/bug-result.txt
```
You can check more details (stack traces) in the `{inputs_dir}/bug-result.txt` file.
