# environment for JURECA:

```
module load GCC Python makeinfo/.6.8 Bison/.3.8.2 ccache HDF5 protobuf{,-python}/.3.19.4 libpng/.1.6.37
pip install --user scons
pip install --user pre-commit
export PATH=$HOME/.local/bin:$PATH
```
