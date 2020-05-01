#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from jinja2 import Environment, FileSystemLoader


def build_html(dataset_path, dataset_info):

    file_loader = FileSystemLoader("parse_NMR_dataset/templates")
    env = Environment(loader=file_loader)
    template = env.get_template("data.html")

    dataset_name = dataset_path.parts[-1]
    filename = dataset_name + ".html"
    with open(filename, "w") as f:
        f.write(template.render(dataset_info=dataset_info, dataset_name=dataset_name))
