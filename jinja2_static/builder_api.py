import secrets
import os
import markdown
import re

from flask import Flask, render_template, render_template_string
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
                    md_kwargs = {}
                    md_path = paths.replace("\\", "/")
                    mark, mark_args = self.import_markdown(f"{md_path}/{file}")

                    for key, value in mark_args.items():
                        if key.lower() in ["layout", "markdown"]:
                            continue
                        md_kwargs[key] = value

                    for key, value in kwargs.items():
                        md_kwargs[key] = value

                    has_layout = mark_args.get("layout", None)

                    if has_layout:
                        to_render = f"layouts/{mark_args['layout']}", md_kwargs, render_template

                    md_kwargs["markdown"] = self.jinja_env.from_string(markdown.markdown(mark)).render(**md_kwargs)

                    if not has_layout:
                        to_render = md_kwargs["markdown"], md_kwargs, render_template_string
                        print(f"[-] No layout specified for '{self}', using default")

                    self.add_url_rule(
                        url_path, f"{filename}_{secrets.token_hex(16)}",
                        view_func=lambda x=to_render: x[2](x[0], **x[1]),
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
