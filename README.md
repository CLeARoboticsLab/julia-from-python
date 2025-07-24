# julia-from-python

This project is meant as an introduction and guide to using Julia from Python.
We will use the python library [JuliaCall](https://juliapy.github.io/PythonCall.jl/stable/juliacall/) but not focus on the reverse (Python from Julia).

This project came out of an older project in which we used the [Waymax](https://github.com/waymo-research/waymax) Python library as a simulator to use a [planner made in Julia](https://github.com/cadearmstrxng/InverseGameDiscountFactor.jl), and thus includes a guide to using Waymax from the Python side.
However, changing what we are doing on the Python side shouldn't affect things on the Julia side of things, with a few caveats :).

You can run this project by using:
```
uv run run_sim.py
```
while in the same directory as this readme.
The `uv run` part is simply handling Python package management and not core to the process of calling Julia from Python.

We have a few CLI options which can be turned on or off to experiment!
`-m` will import a Julia module rather than the script, which is used by default.
`-v` will turn the `verbose` flag, which can be helpful in debugging.

## How does this work?
There are a pair of packages [PythonCall and JuliaCall](https://juliapy.github.io/PythonCall.jl/stable/juliacall/) which implement the ability to call Python from Julia and Julia from Python.
In particular, JuliaCall has a function `seval` which is the core of how we will use Julia.
It runs the input string as Julia code.

In our case, we have a Python script create a Julia instance when
```
from juliacall import Main as jl
```
is run.
Then, we activate the current Julia project with:
```
jl.seval("using Pkg")
jl.seval(f'Pkg.activate("./")')
```
We could activate any project by finding the relative path from the process running the Python script to the Julia project directory.

Finally, we can run Julia code from our project with 
```
jl.seval("...")
``` 


## Some Issues and Warnings
### Conda
#### Conda on Windows
Although you could use any Python environment manager that you want, as of 2025, in our experience, package managers like `conda` on Windows make things difficult by changing environment variables.
On the Julia side of things, these changed environment variables mean that there is a lot of debugging to even get Julia to run properly.
The solution we used was to simply ssh into a Linux machine, where all problems disappeared.

#### Conda & Shared Libraries
Another error to watch out for is that even on Linux, `conda` will still set some environment variables in order to protect certain shared libraries.
As a Python package manager, `conda` focuses on providing versions of these libraries that Python packages expect.
However, Julia libraries may expect a different version, which can lead to errors.

We encountered these errors primarily for graphics libraries such as Makie-based plotting librairies, or even Plots.jl.
A temporary workaround is to simply use a version of Julia libraries that do not depend on any graphics; this includes making sure that any libraries that your Julia project uses also do not depend on graphics.
Changing these dependencies, if possible, can be done by downloading a dev version of a necessary package.
For example, for TrajectoryGamesExamples,
```
pkg> dev TrajectoryGamesExamples
```
will download an editable version of `TrajectoryGamesExamples`.
Then, in the `juliapkg.json` file, we must edit the entry corresponding to `TrajectoryGamesExamples` to indicate where to find the edited version.
This can be done by replacing the `"version": "x.x.x"` entry to `"path": "..."`, where the `"..."` is the correct path to the directory containing the downloaded version.
Typically this is `"./.julia/dev/TrajectoryGamesExamples"` in the home directory for Linux machines.

## Waymax
In order to use the [Waymax](https://github.com/waymo-research/waymax) library, you must first follow the steps outlined in their repository.

## Project Files
Here is a list of what package manager is keeping track of what:

[uv](https://docs.astral.sh/uv/) (Python)
- pyproject.toml
- uv.lock
- .python-version
- ./venv

[Pkg.jl](https://pkgdocs.julialang.org/v1/) (Julia)
- Manifest.toml
- Project.toml

[JuliaCall](https://juliapy.github.io/PythonCall.jl/stable/juliacall/)
- juliapkg.json

### Package Management
If we are importing a Julia script into Python, we must provide JuliaCall with a list of dependencies, which are located in `juliapkg.json`.
The `uuid` and `version` information for each entry can be found in the `Manifest.toml` file by `Ctrl+f`ing for the appropriate dependency.

Note that JuliaCall will automatically figure out dependencies if we are importing a module-thus this can be an easy way to avoid having a large, manually crafted `juliapkg.json`.
When using edited Julia dependencies, however, each edited dependency must have an entry in `juliapkg.json` for the Julia instance to use the edited dependency.