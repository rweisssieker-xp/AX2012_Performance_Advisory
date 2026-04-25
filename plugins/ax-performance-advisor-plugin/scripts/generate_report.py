from axpa_core import main


if __name__ == "__main__":
    raise SystemExit(main(["report", *(__import__("sys").argv[1:])]))
