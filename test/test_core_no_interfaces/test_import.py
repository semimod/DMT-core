import time
from pathlib import Path


def test_import():
    time_cur = time.time()
    from DMT.core import specifiers
    from DMT.core.hasher import create_md5_hash

    print("Import took: " + str(time.time() - time_cur))


if __name__ == "__main__":
    import cProfile, pstats, io

    pr = cProfile.Profile()
    pr.enable()
    test_import()
    pr.disable()

    s = io.StringIO()
    # ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps = pstats.Stats(pr, stream=s).sort_stats(pstats.SortKey.NFL)
    ps.print_stats()

    log_file = Path(__file__).parent / "import.log"
    log_file.write_text(s.getvalue())
