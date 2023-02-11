import secrets
import os
import markdown
import re
import sass
import htmlmin


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
        self._extra_dirs = []
        self.config.update(
            FREEZER_DESTINATION=self._dist,
            FREEZER_DEFAULT_MIMETYPE="text/html",
        )

    @property
    def _extra_file_watcher(self):
        extra_files = []
        for extra_dir in self._extra_dirs:
            for dirname, dirs, files in os.walk(extra_dir):
                for filename in files:
                    filename = os.path.join(dirname, filename)
                    if os.path.isfile(filename):
                        extra_files.append(filename)
        return extra_files

    def import_markdown(self, filename: str) -> list[str, dict]:
        """ Used to read Markdown files and convert to HTML while also providing arguments to the template """
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

    def sass_compiler(self, **kwargs) -> None:
        """ Compile SASS files to CSS """
        if not os.path.isdir(f"{self._static}/sass"):
            return None

        self._extra_dirs.append(f"{self._static}/sass")

        try:
            sass.compile(
                dirname=[f"{self._static}/sass", f"{self._static}/css"],
                output_style="compressed"
            )
        except Exception as e:
            print(f"[-] SASS compile error | {type(e).__name__}: {e}")
        else:
            print(f"[+] SASS compiled to {self._static}/css")

    def _render_html(self, func: any, minify_html: bool = True):
        if minify_html:
            return htmlmin.minify(func, remove_empty_space=True)
        return func

    def generate(self, debug: bool = False, minify_html: bool = True, **kwargs) -> None:
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
                        view_func=lambda x=to_render: self._render_html(
                            x[2](x[0], **x[1]), minify_html
                        )
                    )
                else:
                    self.add_url_rule(
                        url_path, f"{filename}_{secrets.token_hex(16)}",
                        view_func=lambda x=filename_render: self._render_html(
                            render_template(x, **kwargs), minify_html
                        )
                    )

        self.sass_compiler()

        if not debug:
            self.freezer.freeze()
            try:
                pass
            except Exception as e:
                print(f"[-] Compile error | {type(e).__name__}:\n{e}")
            print(f"[+] Done, compiled to {self.config['FREEZER_DESTINATION']}")
        else:
            self.config["TEMPLATES_AUTO_RELOAD"] = True
            self.run(
                port=self._port, debug=True,
                extra_files=self._extra_file_watcher
            )
