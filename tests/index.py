from jinja2_static import Builder

build = Builder(
    templates="./templates",
    dist="./public",
)

build.generate(debug=True)
