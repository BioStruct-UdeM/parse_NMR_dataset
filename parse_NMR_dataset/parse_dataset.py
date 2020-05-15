#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
parse_NMR_dataset - parse experimental information from a Bruker NMR dataset
author: Norm1 <norm@normandcyr.com>
"""

import re
import argparse
import numpy as np
import pandas as pd
import nmrglue as ng
from pathlib import Path
from datetime import date

# from pprint import pprint
import matplotlib.pyplot as plt
from parse_NMR_dataset import _version
from parse_NMR_dataset import make_dataset_html


def load_experiment_data(experiment_number):

    # read in the bruker formatted data
    dic, data = ng.bruker.read(str(experiment_number))

    # remove the digital filter
    data = ng.bruker.remove_digital_filter(dic, data)

    pdic, pdata = ng.bruker.read_pdata(str(experiment_number) + "/pdata/1")

    return dic, data, pdata


def determine_nb_dimensions(dic):

    acqu_list = []
    for key in dic:
        if re.match(r"acqu.+", key):
            acqu_list.append(key)

    nb_dimensions = len(acqu_list)

    return (acqu_list, nb_dimensions)


def parse_dimension_parameters(all_dimension_parameters):

    nucleus = all_dimension_parameters["NUC1"]
    spectral_width = round(all_dimension_parameters["SW"], 2)
    nb_increments = all_dimension_parameters["TD"]
    offset = round(all_dimension_parameters["O1"] / all_dimension_parameters["SFO1"], 2)

    dimension_acquisition_parameters = {}
    dimension_acquisition_parameters["nucleus"] = nucleus
    dimension_acquisition_parameters["spectral width"] = spectral_width
    dimension_acquisition_parameters["carrier offset"] = offset
    dimension_acquisition_parameters["number of increments"] = nb_increments

    return dimension_acquisition_parameters


def parse_general_acquisition_parameters(all_dimension_parameters, nb_dimensions):

    acquisition_date = str(date.fromtimestamp(all_dimension_parameters["DATE"]))
    pulse_program = all_dimension_parameters["PULPROG"]

    nb_scans = all_dimension_parameters["NS"]
    temperature = round(all_dimension_parameters["TE"] - 273.15, 1)

    general_acquisition_parameters = {}
    general_acquisition_parameters["acquisition date"] = acquisition_date
    general_acquisition_parameters["pulse program"] = pulse_program
    general_acquisition_parameters["number of dimensions"] = nb_dimensions
    general_acquisition_parameters["number of scans"] = nb_scans
    general_acquisition_parameters["temperature"] = temperature

    return general_acquisition_parameters


def plot_data(df_1D_data, experiment_number, dataset_name):

    png_plot_filename = "plot_1d_exp{}.png".format(experiment_number.parts[-1])

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(
        df_1D_data.chemical_shift,
        df_1D_data.intensity,
        color="blue",
        linestyle="solid",
        linewidth=2,
    )

    # decorate axes
    ax.set_yticklabels([])
    ax.set_title(dataset_name + "-" + experiment_number.parts[-1])
    ax.set_xlabel("1H, ppm")
    ax.set_xlim(
        df_1D_data.chemical_shift.max() + 0.1, df_1D_data.chemical_shift.min() - 0.1
    )
    ax.set_ylabel("intensity")

    # save the figure
    fig.savefig(png_plot_filename)

    return png_plot_filename


def build_experiment_information(
    dataset_info, experiment_number, dataset_name, x_min, x_max
):

    dic, data, pdata = load_experiment_data(experiment_number)
    acqu_list, nb_dimensions = determine_nb_dimensions(dic)

    acquisition_parameters = {}
    acquisition_parameters["png_plot_filename"] = None
    for dimension in acqu_list:

        all_dimension_parameters = dic[dimension]

        if dimension == "acqus":
            acquisition_parameters[
                "general parameters"
            ] = parse_general_acquisition_parameters(
                all_dimension_parameters, nb_dimensions
            )
            acquisition_parameters[
                "direct dimension parameters"
            ] = parse_dimension_parameters(all_dimension_parameters)

        elif dimension == "acqu2s":
            acquisition_parameters[
                "indirect dimension parameters"
            ] = parse_dimension_parameters(all_dimension_parameters)

    if nb_dimensions == 1:
        x_ppm = (
            np.arange(len(pdata), 0, -1) * (dic["acqus"]["SW"] / len(pdata))
        ) + dic["procs"]["ABSF2"]
        df_1D_data_full = pd.DataFrame({"chemical_shift": x_ppm, "intensity": pdata})
        df_1D_data = df_1D_data_full[
            (df_1D_data_full["chemical_shift"] >= x_min)
            & (df_1D_data_full["chemical_shift"] <= x_max)
        ]

        acquisition_parameters["png_plot_filename"] = plot_data(
            df_1D_data, experiment_number, dataset_name
        )

    return acquisition_parameters


def build_dataset_dict(dataset_info, experiment_number, acquisition_parameters):

    dataset_info["experiments"].append(
        {
            "experiment number": int(experiment_number.parts[-1]),
            "acquisition parameters": acquisition_parameters,
        }
    )

    return dataset_info


def parse_arguments():

    parser = argparse.ArgumentParser(
        prog="parse NMR dataset", usage="parse_dataset [options]"
    )
    parser.add_argument(
        "dataset_path",
        help="indicate the path to dataset you want to be parsed",
        type=Path,
    )
    parser.add_argument(
        "--xmax", default=24, help="specify the maximum ppm to report", type=float,
    )
    parser.add_argument(
        "--xmin", default=-5, help="specify the minimum ppm to report", type=float,
    )
    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + _version.__version__,
    )
    args = parser.parse_args()

    return args


def main():

    args = parse_arguments()

    dataset_path = args.dataset_path
    x_max = args.xmax
    x_min = args.xmin
    dataset_name = dataset_path.parts[-1]
    dataset_info = {"dataset name": dataset_name, "experiments": []}

    for experiment_number in dataset_path.iterdir():
        if experiment_number.is_dir():
            try:
                acquisition_parameters = build_experiment_information(
                    dataset_info, experiment_number, dataset_name, x_min, x_max
                )
                dataset_info = build_dataset_dict(
                    dataset_info, experiment_number, acquisition_parameters
                )
            except IOError:
                print(
                    "'{}' has no readable NMR data so ignoring the folder.".format(
                        experiment_number
                    )
                )
                pass

    make_dataset_html.build_html(dataset_path, dataset_info)


if __name__ == "__main__":
    main()
