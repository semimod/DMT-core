import os
import pandas as pd
from DMT.core import Plot, specifiers
import numpy as np

if __name__ == "__main__":
    # open file and read
    path = os.path.join("test/test_interface_ngspice/output_tran")
    with open(path, "r") as f:
        txt = f.read()

    txt = txt.splitlines()
    headers = txt[0].split()
    data = {}
    for head in headers:
        data[head] = np.zeros(len(txt) - 1)

    for i, line in enumerate(txt[1:]):
        line = line.split()
        for head, ele in zip(headers, line):
            data[head][i] = float(ele)

    data = pd.DataFrame.from_dict(data)

    data_ads = pd.read_csv("test/test_interface_ngspice/transient_data_ads.csv")

    plt_cc = Plot(
        "V_C(t)",
        style="xtraction_color",
        x_label="t(ps)",
        y_specifier=specifiers.VOLTAGE + "C",
        x_scale=1e12,
    )
    plt_cc.add_data_set(data["time"], data["c"], label="ngs")
    plt_cc.add_data_set(data_ads["t"], data_ads["V_C"], label="ads")
    plt_cc.plot_py(show=True)
