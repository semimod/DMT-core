from datetime import datetime
import numpy as np
from pathlib import Path
from DMT.core import read_data, DataFrame, specifiers


def test_data_processor_and_deem():
    # load test measurements
    df = read_data(Path(__file__).parent / "test_data" / "Spar_vb.mdm")
    df_open = read_data(Path(__file__).parent / "test_data" / "dummy_open_freq.mdm")
    df_short = read_data(Path(__file__).parent / "test_data" / "dummy_short_freq.mdm")

    # correct data format of measurements
    nodes = ["B", "C", "E", "S"]
    df = df.clean_data(
        nodes,
        "E",
        fallback={
            "S_deemb(1,1)": None,
            "S_deemb(2,1)": None,
            "S_deemb(1,2)": None,
            "S_deemb(2,2)": None,
        },
        ac_ports=["B", "C"],
    )
    df_short = df_short.clean_data(nodes, "E", fallback={"1": "B", "2": "C"}, ac_ports=["B", "C"])
    df_open = df_open.clean_data(nodes, "E", fallback={"1": "B", "2": "C"}, ac_ports=["B", "C"])

    # deembed
    df = df.deembed_open(df_open, nodes)
    df_short = df_short.deembed_open(df_open, nodes)
    df = df.deembed_short(df_short, nodes)

    # calculate cbe
    df = df.calc_cbe()
    return df


def test_cap_extraction_common_base():
    # create a test dataframe
    df = DataFrame()
    freq = np.logspace(3, 10, 101)
    cbe = 15e-15
    cbc = 10e-15
    cce = 0
    # common base config PI network
    g1 = 1j * 2 * np.pi * freq * cbe
    g2 = 1j * 2 * np.pi * freq * cce
    g3 = 1j * 2 * np.pi * freq * cbc
    y_common_e = np.zeros((len(freq), 2, 2), dtype=np.complex128)
    y_common_e[:, 0, 0] = g1 + g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 0, 1] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 0] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 1] = g2 + g3  # pylint: disable=unsupported-assignment-operation
    df[specifiers.FREQUENCY] = freq
    df[specifiers.SS_PARA_Y + "E" + "E"] = y_common_e[:, 0, 0]
    df[specifiers.SS_PARA_Y + "C" + "C"] = y_common_e[:, 1, 1]
    df[specifiers.SS_PARA_Y + "C" + "E"] = y_common_e[:, 0, 1]
    df[specifiers.SS_PARA_Y + "E" + "C"] = y_common_e[:, 1, 0]
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "E", ports=["E", "C"])  # slow
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "C", ports=["E", "C"])  # slow

    # extract cbe
    cbe_extract = df[specifiers.CAPACITANCE + "B" + "E"].to_numpy()
    cbe_extract = np.unique(cbe)
    assert np.isclose(cbe, cbe_extract)
    # extract cbc
    cbc_extract = df[specifiers.CAPACITANCE + "B" + "C"].to_numpy()
    cbc_extract = np.unique(cbc)
    assert np.isclose(cbc, cbc_extract)


def test_cap_extraction_common_base_reversed():
    # create a test dataframe
    df = DataFrame()
    freq = np.logspace(3, 10, 101)
    cbe = 15e-15
    cbc = 10e-15
    cce = 0
    # common base config PI network
    g3 = 1j * 2 * np.pi * freq * cbe
    g2 = 1j * 2 * np.pi * freq * cce
    g1 = 1j * 2 * np.pi * freq * cbc
    y_common_e = np.zeros((len(freq), 2, 2), dtype=np.complex128)
    y_common_e[:, 0, 0] = g1 + g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 0, 1] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 0] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 1] = g2 + g3  # pylint: disable=unsupported-assignment-operation
    df[specifiers.FREQUENCY] = freq
    df[specifiers.SS_PARA_Y + "E" + "E"] = y_common_e[:, 0, 0]
    df[specifiers.SS_PARA_Y + "C" + "C"] = y_common_e[:, 1, 1]
    df[specifiers.SS_PARA_Y + "C" + "E"] = y_common_e[:, 0, 1]
    df[specifiers.SS_PARA_Y + "E" + "C"] = y_common_e[:, 1, 0]
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "E", ports=["C", "E"])  # slow
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "C", ports=["C", "E"])  # slow

    # extract cbe
    cbe_extract = df[specifiers.CAPACITANCE + "B" + "E"].to_numpy()
    cbe_extract = np.unique(cbe)
    assert np.isclose(cbe, cbe_extract)
    # extract cbc
    cbc_extract = df[specifiers.CAPACITANCE + "B" + "C"].to_numpy()
    cbc_extract = np.unique(cbc)
    assert np.isclose(cbc, cbc_extract)


def test_cap_extraction_common_emitter():
    # create a test dataframe
    df = DataFrame()
    freq = np.logspace(3, 10, 101)
    cbe = 15e-15
    cbc = 10e-15
    cce = 0
    # common emitter config PI network
    g1 = 1j * 2 * np.pi * freq * cbe
    g2 = 1j * 2 * np.pi * freq * cbc
    g3 = 0
    y_common_e = np.zeros((len(freq), 2, 2), dtype=np.complex128)
    y_common_e[:, 0, 0] = g1 + g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 0, 1] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 0] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 1] = g2 + g3  # pylint: disable=unsupported-assignment-operation
    df[specifiers.FREQUENCY] = freq
    df[specifiers.SS_PARA_Y + "B" + "B"] = y_common_e[:, 0, 0]
    df[specifiers.SS_PARA_Y + "C" + "C"] = y_common_e[:, 1, 1]
    df[specifiers.SS_PARA_Y + "B" + "C"] = y_common_e[:, 0, 1]
    df[specifiers.SS_PARA_Y + "C" + "B"] = y_common_e[:, 1, 0]
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "E", ports=["B", "C"])  # slow
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "C", ports=["B", "C"])  # slow

    # extract cbe
    cbe_extract = df[specifiers.CAPACITANCE + "B" + "E"].to_numpy()
    cbe_extract = np.unique(cbe)
    assert np.isclose(cbe, cbe_extract)
    # extract cbc
    cbc_extract = df[specifiers.CAPACITANCE + "B" + "C"].to_numpy()
    cbc_extract = np.unique(cbc)
    assert np.isclose(cbc, cbc_extract)


def test_cap_extraction_common_emitter_reverse():
    # create a test dataframe
    df = DataFrame()
    freq = np.logspace(3, 10, 101)
    cbe = 15e-15
    cbc = 10e-15
    cce = 0
    # common emitter config PI network
    g3 = 1j * 2 * np.pi * freq * cbe
    g2 = 1j * 2 * np.pi * freq * cbc
    g1 = 0
    y_common_e = np.zeros((len(freq), 2, 2), dtype=np.complex128)
    y_common_e[:, 0, 0] = g1 + g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 0, 1] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 0] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 1] = g2 + g3  # pylint: disable=unsupported-assignment-operation
    df[specifiers.FREQUENCY] = freq
    df[specifiers.SS_PARA_Y + "B" + "B"] = y_common_e[:, 0, 0]
    df[specifiers.SS_PARA_Y + "C" + "C"] = y_common_e[:, 1, 1]
    df[specifiers.SS_PARA_Y + "B" + "C"] = y_common_e[:, 0, 1]
    df[specifiers.SS_PARA_Y + "C" + "B"] = y_common_e[:, 1, 0]
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "E", ports=["C", "B"])  # slow
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "C", ports=["C", "B"])  # slow

    # extract cbe
    cbe_extract = df[specifiers.CAPACITANCE + "B" + "E"].to_numpy()
    cbe_extract = np.unique(cbe)
    assert np.isclose(cbe, cbe_extract)
    # extract cbc
    cbc_extract = df[specifiers.CAPACITANCE + "B" + "C"].to_numpy()
    cbc_extract = np.unique(cbc)
    assert np.isclose(cbc, cbc_extract)


def test_cap_extraction_common_collector():
    # create a test dataframe
    df = DataFrame()
    freq = np.logspace(3, 10, 101)
    cbe = 15e-15
    cbc = 10e-15
    cce = 0
    # common collector config PI network
    g1 = 1j * 2 * np.pi * freq * cbc
    g2 = 1j * 2 * np.pi * freq * cbe
    g3 = 1j * 2 * np.pi * freq * cce
    y_common_e = np.zeros((len(freq), 2, 2), dtype=np.complex128)
    y_common_e[:, 0, 0] = g1 + g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 0, 1] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 0] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 1] = g2 + g3  # pylint: disable=unsupported-assignment-operation
    df[specifiers.FREQUENCY] = freq
    df[specifiers.SS_PARA_Y + "B" + "B"] = y_common_e[:, 0, 0]
    df[specifiers.SS_PARA_Y + "E" + "E"] = y_common_e[:, 1, 1]
    df[specifiers.SS_PARA_Y + "B" + "E"] = y_common_e[:, 0, 1]
    df[specifiers.SS_PARA_Y + "E" + "B"] = y_common_e[:, 1, 0]
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "E", ports=["B", "E"])  # slow
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "C", ports=["B", "E"])  # slow

    # extract cbe
    cbe_extract = df[specifiers.CAPACITANCE + "B" + "E"].to_numpy()
    cbe_extract = np.unique(cbe)
    assert np.isclose(cbe, cbe_extract)
    # extract cbc
    cbc_extract = df[specifiers.CAPACITANCE + "B" + "C"].to_numpy()
    cbc_extract = np.unique(cbc)
    assert np.isclose(cbc, cbc_extract)


def test_cap_extraction_common_collector_reversed():
    # create a test dataframe
    df = DataFrame()
    freq = np.logspace(3, 10, 101)
    cbe = 15e-15
    cbc = 10e-15
    cce = 0
    # common collector config PI network
    g3 = 1j * 2 * np.pi * freq * cbc
    g2 = 1j * 2 * np.pi * freq * cbe
    g1 = 1j * 2 * np.pi * freq * cce
    y_common_e = np.zeros((len(freq), 2, 2), dtype=np.complex128)
    y_common_e[:, 0, 0] = g1 + g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 0, 1] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 0] = -g2  # pylint: disable=unsupported-assignment-operation
    y_common_e[:, 1, 1] = g2 + g3  # pylint: disable=unsupported-assignment-operation
    df[specifiers.FREQUENCY] = freq
    df[specifiers.SS_PARA_Y + "B" + "B"] = y_common_e[:, 0, 0]
    df[specifiers.SS_PARA_Y + "E" + "E"] = y_common_e[:, 1, 1]
    df[specifiers.SS_PARA_Y + "B" + "E"] = y_common_e[:, 0, 1]
    df[specifiers.SS_PARA_Y + "E" + "B"] = y_common_e[:, 1, 0]
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "E", ports=["E", "B"])
    df.ensure_specifier_column(specifiers.CAPACITANCE + "B" + "C", ports=["E", "B"])

    # extract cbe
    cbe_extract = df[specifiers.CAPACITANCE + "B" + "E"].to_numpy()
    cbe_extract = np.unique(cbe)
    assert np.isclose(cbe, cbe_extract)
    # extract cbc
    cbc_extract = df[specifiers.CAPACITANCE + "B" + "C"].to_numpy()
    cbc_extract = np.unique(cbc)
    assert np.isclose(cbc, cbc_extract)


if __name__ == "__main__":
    from DMT.core import Plot

    import cProfile, pstats, io

    profiler = cProfile.Profile()
    time_start = datetime.now()
    profiler.enable()
    test_cap_extraction_common_emitter()
    test_cap_extraction_common_emitter_reverse()
    test_cap_extraction_common_base()
    test_cap_extraction_common_base_reversed()
    test_cap_extraction_common_collector()
    test_cap_extraction_common_collector_reversed()
    df_deemb = test_data_processor_and_deem()
    profiler.disable()
    print("Runtime: " + str(datetime.now() - time_start))

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")

    ps.print_stats(50)  # print the 50 methods with the longest cumulative time

    print(s.getvalue())
    # plot the result
    plt_cbe = Plot("C_BE(V_BE)", style="bw")
    for freq_a in [1e9, 5e9, 10e9]:
        df_tmp = df_deemb[df_deemb["FREQ"] == freq_a]
        plt_cbe.add_data_set(df_tmp["V_B"].to_numpy(), df_tmp["C_BE"].to_numpy(), label="meas")

    plt_cbe.plot_pyqtgraph(show=True)
