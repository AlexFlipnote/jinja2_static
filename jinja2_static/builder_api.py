import secrets
import os
import markdown
import re

from flask import Flask, render_template
from flask_frozen import Freezer


class Builder(Flask):
    def __init__(self, templates: str = None, dist: str = None, static: str = None, port: int = 8080):
        self._templates = templates or "./templates"
        self._dist = dist or "./public"
        self._static = static or "./static"
        self._port = port

        super().__init__(
            __name__, root_path="./",
            template_folder=self._templates, static_folder=self._static
        )

        self.freezer = Freezer(self)
        self.config.update(
            FREEZER_DESTINATION=self._dist,
            FREEZER_DEFAULT_MIMETYPE="text/html",
        )

    def import_markdown(self, filename: str) -> list[str, dict]:
        try:
            with open(filename, "r") as f:
                data = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"[-] File not found: {filename}")

        re_args = re.compile(r"^\-\-\-(.*)\-\-\-", flags=re.DOTALL)
        get_arg = re.compile(r"([a-zA-Z0-9\_]{1,})(?:\: |\:)(.*)")
        temp_args = {}

        has_arguments = re_args.search(data)
        if has_arguments:
            for arg in has_arguments.group(1).split("\n"):
                valid_arg = get_arg.search(arg)
                if valid_arg:
                    temp_args[valid_arg.group(1)] = valid_arg.group(2)

        data = re_args.sub("", data)
        return markdown.markdown(data), temp_args

    def generate(self, debug: bool = False, **kwargs) -> None:
        """ Generate the sites, kwargs are the arguments to pass to the template """
        for paths, dirs, files in os.walk(self._templates):
            for file in files:
                if file.startswith("_"):
                    continue

                path = paths.replace(self._templates, "").replace("\\", "/")
                filename = file.replace(".jinja", "").replace(".md", "").replace(".html", "")

                if filename == "index":
                    url_path = f"{path}/" if path else "/"
                elif filename.isdigit():
                    # For GitHub Pages, it's useful for 404.html and stuff
                    url_path = f"/{filename}.html"
                else:
                    url_path = f"{path}/{filename}/" if path else f"/{filename}/"

                filename_render = f"{path}/{file}" if path else f"{file}"

                if file.endswith(".md"):
                    md_path = paths.replace("\\", "/")
                    mark, mark_args = self.import_markdown(f"{md_path}/{file}")
                    if "layout" in mark_args:
                        filename_render = f"layouts/{mark_args['layout']}"
                        kwargs["markdown"] = mark
                    else:
                        print(f"[-] No layout specified for {filename}, using default")

                    for key, value in kwargs.items():
                        if key.lower() in ["layout", "markdown"]:
                            continue
                        kwargs[key] = value

                    self.add_url_rule(
                        url_path, f"{filename}_{secrets.token_hex(16)}",
                        view_func=lambda x=filename_render: render_template(x, **kwargs),
                    )
                else:
                    self.add_url_rule(
                        url_path, f"{filename}_{secrets.token_hex(16)}",
                        view_func=lambda x=filename_render: render_template(x, **kwargs),
                    )

        if not debug:
            self.freezer.freeze()
            try:
                pass
            except Exception as e:
                print(f"[-] Compile error | {type(e).__name__}:\n{e}")
            print(f"[+] Done, compiled to {self.config['FREEZER_DESTINATION']}")
        else:
            self.run(port=self._port, debug=True)
